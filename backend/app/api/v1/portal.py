import hashlib
import hmac
import secrets
from datetime import date, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from io import BytesIO

from app.api.v1.billing import invoice_public
from app.api.v1.sales import subscription_public
from app.core.deps import DbSession, RequireCustomer
from app.core.config import settings
from app.core.exceptions import AppError
from app.models.customer import Customer
from app.models.catalog import Discount, Plan, Product
from app.models.company import Company
from app.models.subscription import Invoice, Payment, PaymentAttempt, Quotation, Subscription, SubscriptionChangeRequest
from app.schemas.billing import InvoicePublic, PaymentRecord, PaymentPublic
from app.schemas.portal import (CustomerCatalog, CustomerChangeRequestCreate, CustomerProfilePublic, CustomerProfileUpdate,
    CustomerDirectSubscriptionCreate, CustomerRequestPublic, CustomerSubscriptionRequestCreate, CustomerSummary, PaymentOrderPublic,
    PaymentVerificationRequest)
from app.schemas.subscription import QuotationPublic, QuotationStatusUpdate
from app.services.audit_service import record_audit
from app.services.invoice_service import invoice_balance_due, refresh_invoice_status
from app.schemas.subscription import SubscriptionPublic
from app.services.invoice_pdf import render_invoice

router = APIRouter()


def normalized_monthly_price(amount, interval: str, interval_count: int) -> Decimal:
    count = max(interval_count, 1)
    if interval == "year": return amount / (12 * count)
    if interval == "week": return amount * Decimal(52) / (12 * count)
    if interval == "day": return amount * Decimal(365) / (12 * count)
    return amount / count


def customer_id_for(user: RequireCustomer, db: DbSession) -> int:
    customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
    if not customer:
        raise AppError("Customer profile not found", status_code=404, code="customer_not_found")
    return customer.id


def customer_for(user: RequireCustomer, db: DbSession) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
    if not customer:
        raise AppError("Customer profile not found", status_code=404, code="customer_not_found")
    return customer


@router.get("/catalog", response_model=CustomerCatalog)
def browse_catalog(user: RequireCustomer, db: DbSession):
    customer = customer_for(user, db)
    company = db.get(Company, customer.company_id)
    products = db.scalars(select(Product).options(selectinload(Product.plans)).where(
        Product.company_id == customer.company_id, Product.is_active.is_(True)).order_by(Product.name)).all()
    return CustomerCatalog(company_name=company.name, company_slug=company.slug, company_email=company.email, products=[
        {"id": product.id, "name": product.name, "sku": product.sku, "product_type": product.product_type,
         "description": product.notes, "plans": [{"id": plan.id, "name": plan.name, "price": plan.price,
         "billing_interval": plan.billing_interval, "interval_count": plan.interval_count,
         "features": plan.features or []} for plan in product.plans if plan.is_active]}
        for product in products if any(plan.is_active for plan in product.plans)
    ])


@router.post("/subscription-requests", status_code=201)
def request_subscription(payload: CustomerSubscriptionRequestCreate, user: RequireCustomer, db: DbSession):
    customer = customer_for(user, db)
    plan = db.scalar(select(Plan).options(joinedload(Plan.product)).where(Plan.id == payload.plan_id))
    if not plan or not plan.is_active or not plan.product.is_active or plan.product.company_id != customer.company_id:
        raise AppError("Plan not found in your company workspace", status_code=404, code="plan_not_found")
    discount = None
    discount_amount = Decimal("0.00")
    discount_code = payload.discount_code.strip().upper() if payload.discount_code else None
    subtotal = (plan.price * payload.quantity).quantize(Decimal("0.01"))
    if discount_code:
        discount = db.scalar(select(Discount).where(Discount.company_id == customer.company_id, Discount.code == discount_code))
        today = date.today()
        if not discount or not discount.is_active or (discount.starts_at and discount.starts_at > today) or (discount.ends_at and discount.ends_at < today):
            raise AppError("Discount code is invalid or inactive for this company", status_code=422, code="invalid_discount_code")
        if discount.usage_limit is not None and discount.times_used >= discount.usage_limit:
            raise AppError("Discount usage limit has been reached", status_code=409, code="discount_limit_reached")
        if subtotal < discount.minimum_amount:
            raise AppError("Subscription request does not meet the discount minimum", status_code=422, code="discount_minimum_not_met")
        discount_amount = (subtotal * discount.value / Decimal("100") if discount.discount_type == "percentage" else discount.value).quantize(Decimal("0.01"))
        discount_amount = min(subtotal, discount_amount)
    quote = Quotation(company_id=customer.company_id, number=f"QT-{date.today():%y%m%d}-{secrets.token_hex(3).upper()}",
        customer_id=customer.id, plan_id=plan.id, product_name=plan.product.name, plan_name=plan.name,
        billing_interval=plan.billing_interval, interval_count=plan.interval_count, quantity=payload.quantity,
        unit_price=plan.price, valid_until=date.today() + timedelta(days=14), notes=payload.notes,
        discount_id=discount.id if discount else None, discount_code=discount.code if discount else None,
        discount_type=discount.discount_type if discount else None, discount_value=discount.value if discount else None,
        discount_amount=discount_amount, line_items=[{"plan_id": plan.id,
            "description": f"{plan.product.name} - {plan.name}", "product_name": plan.product.name,
            "plan_name": plan.name, "quantity": payload.quantity, "unit_price": str(plan.price)}], status="draft")
    db.add(quote); db.flush()
    record_audit(db, user.id, "customer.subscription_requested", "quotation", quote.id, {"company_id": customer.company_id, "plan_id": plan.id})
    db.commit()
    return {"id": quote.id, "number": quote.number, "status": quote.status}


@router.post("/subscriptions", response_model=SubscriptionPublic, status_code=201)
def buy_subscription(payload: CustomerDirectSubscriptionCreate, user: RequireCustomer, db: DbSession):
    customer = customer_for(user, db)
    plan = db.scalar(select(Plan).options(joinedload(Plan.product)).where(Plan.id == payload.plan_id))
    if not plan or not plan.is_active or not plan.product.is_active or plan.product.company_id != customer.company_id:
        raise AppError("Plan not found in your company workspace", status_code=404, code="plan_not_found")

    discount = None
    discount_amount = Decimal("0.00")
    discount_code = payload.discount_code.strip().upper() if payload.discount_code else None
    subtotal = (plan.price * payload.quantity).quantize(Decimal("0.01"))
    if discount_code:
        discount = db.scalar(select(Discount).where(
            Discount.company_id == customer.company_id, Discount.code == discount_code
        ).with_for_update())
        today = date.today()
        if not discount or not discount.is_active or (discount.starts_at and discount.starts_at > today) or (discount.ends_at and discount.ends_at < today):
            raise AppError("Discount code is invalid or inactive for this company", status_code=422, code="invalid_discount_code")
        if discount.usage_limit is not None and discount.times_used >= discount.usage_limit:
            raise AppError("Discount usage limit has been reached", status_code=409, code="discount_limit_reached")
        if subtotal < discount.minimum_amount:
            raise AppError("Subscription does not meet the discount minimum", status_code=422, code="discount_minimum_not_met")
        discount_amount = (
            subtotal * discount.value / Decimal("100")
            if discount.discount_type == "percentage" else discount.value
        ).quantize(Decimal("0.01"))
        discount_amount = min(subtotal, discount_amount)

    start = date.today()
    subscription = Subscription(
        company_id=customer.company_id,
        number=f"SN-{start:%y%m%d}-{secrets.token_hex(3).upper()}",
        customer_id=customer.id,
        plan_id=plan.id,
        quotation_id=None,
        discount_id=discount.id if discount else None,
        product_name=plan.product.name,
        plan_name=plan.name,
        billing_interval=plan.billing_interval,
        interval_count=plan.interval_count,
        quantity=payload.quantity,
        unit_price=plan.price,
        discount_code=discount.code if discount else None,
        discount_type=discount.discount_type if discount else None,
        discount_value=discount.value if discount else None,
        discount_amount=discount_amount,
        features=list(plan.features or []),
        line_items=[{"plan_id": plan.id, "description": f"{plan.product.name} - {plan.name}",
            "product_name": plan.product.name, "plan_name": plan.name,
            "quantity": payload.quantity, "unit_price": str(plan.price)}],
        start_date=start,
        next_billing_date=start,
        status="active",
    )
    db.add(subscription)
    if discount:
        discount.times_used += 1
    db.flush()
    record_audit(db, user.id, "customer.subscription_purchased", "subscription", subscription.id,
        {"company_id": customer.company_id, "plan_id": plan.id, "quantity": payload.quantity})
    db.commit()
    row = db.scalar(select(Subscription).options(
        joinedload(Subscription.customer).joinedload(Customer.user)
    ).where(Subscription.id == subscription.id))
    return subscription_public(row)


@router.get("/quotations", response_model=list[QuotationPublic])
def my_quotations(user: RequireCustomer, db: DbSession):
    customer = customer_for(user, db)
    rows = db.scalars(select(Quotation).options(joinedload(Quotation.customer).joinedload(Customer.user)).where(
        Quotation.customer_id == customer.id).order_by(Quotation.created_at.desc())).unique().all()
    return [QuotationPublic(**{key: getattr(row, key) for key in (
        "id", "number", "customer_id", "plan_id", "product_name", "plan_name", "billing_interval", "interval_count",
        "quantity", "unit_price", "status", "valid_until", "notes", "discount_code", "discount_amount", "created_at")},
        line_items=row.line_items or [],
        customer_name=row.customer.user.name, customer_email=row.customer.user.email) for row in rows]


@router.patch("/quotations/{quotation_id}", response_model=QuotationPublic)
def update_my_quotation(quotation_id: int, payload: QuotationStatusUpdate, user: RequireCustomer, db: DbSession):
    customer = customer_for(user, db)
    quote = db.scalar(select(Quotation).options(joinedload(Quotation.customer).joinedload(Customer.user)).where(
        Quotation.id == quotation_id, Quotation.customer_id == customer.id))
    if not quote:
        raise AppError("Quotation not found", status_code=404, code="not_found")
    if payload.status != "accepted" or quote.status != "sent":
        raise AppError("Only sent quotations can be accepted", status_code=409, code="invalid_transition")
    if quote.valid_until < date.today():
        raise AppError("Expired quotations cannot be accepted", status_code=409, code="quotation_expired")
    quote.status = "accepted"
    record_audit(db, user.id, "customer.quotation_accepted", "quotation", quote.id)
    db.commit()
    return QuotationPublic(**{key: getattr(quote, key) for key in (
        "id", "number", "customer_id", "plan_id", "product_name", "plan_name", "billing_interval", "interval_count",
        "quantity", "unit_price", "status", "valid_until", "notes", "discount_code", "discount_amount", "created_at")},
        line_items=quote.line_items or [],
        customer_name=quote.customer.user.name, customer_email=quote.customer.user.email)


@router.post("/subscriptions/{subscription_id}/requests", status_code=201)
def request_subscription_change(subscription_id: int, payload: CustomerChangeRequestCreate, user: RequireCustomer, db: DbSession):
    customer = customer_for(user, db)
    subscription = db.scalar(select(Subscription).where(Subscription.id == subscription_id,
        Subscription.customer_id == customer.id, Subscription.company_id == customer.company_id))
    if not subscription:
        raise AppError("Subscription not found", status_code=404, code="not_found")
    if subscription.status in {"cancelled", "expired"}:
        raise AppError("Closed subscriptions cannot be changed", status_code=409, code="invalid_transition")
    if db.scalar(select(SubscriptionChangeRequest.id).where(
        SubscriptionChangeRequest.subscription_id == subscription.id, SubscriptionChangeRequest.status == "pending")):
        raise AppError("A change request is already pending for this subscription", status_code=409, code="request_pending")
    if payload.request_type == "pause" and subscription.status != "active":
        raise AppError("Only active subscriptions can be paused", status_code=409, code="invalid_transition")
    if payload.request_type == "resume" and subscription.status != "paused":
        raise AppError("Only paused subscriptions can be resumed", status_code=409, code="invalid_transition")
    requested_plan = None
    if payload.request_type in {"upgrade", "downgrade"}:
        if subscription.status != "active":
            raise AppError("Only active subscriptions can change plans", status_code=409, code="invalid_transition")
        if payload.requested_plan_id is None:
            raise AppError("Select a plan for this request", status_code=422, code="plan_required")
        requested_plan = db.scalar(select(Plan).options(joinedload(Plan.product)).where(
            Plan.id == payload.requested_plan_id, Plan.is_active.is_(True)))
        if not requested_plan or requested_plan.product.company_id != customer.company_id or not requested_plan.product.is_active:
            raise AppError("Plan not found in your company workspace", status_code=404, code="plan_not_found")
        if requested_plan.id == subscription.plan_id:
            raise AppError("Select a different plan", status_code=422, code="same_plan")
        is_upgrade = normalized_monthly_price(requested_plan.price, requested_plan.billing_interval, requested_plan.interval_count) > normalized_monthly_price(
            subscription.unit_price, subscription.billing_interval, subscription.interval_count)
        if (payload.request_type == "upgrade") != is_upgrade:
            raise AppError("Choose upgrade or downgrade based on the plan price", status_code=422, code="incorrect_change_type")
    elif payload.requested_plan_id is not None:
        raise AppError("A plan can only be selected for an upgrade or downgrade", status_code=422, code="unexpected_plan")
    request = SubscriptionChangeRequest(company_id=customer.company_id, customer_id=customer.id,
        subscription_id=subscription.id, requested_plan_id=requested_plan.id if requested_plan else None,
        request_type=payload.request_type, notes=payload.notes, status="pending")
    db.add(request); db.flush()
    record_audit(db, user.id, "customer.subscription_change_requested", "subscription_change_request", request.id,
        {"subscription_id": subscription.id, "request_type": request.request_type})
    db.commit()
    return {"id": request.id, "status": request.status, "request_type": request.request_type}


@router.get("/requests", response_model=list[CustomerRequestPublic])
def my_change_requests(user: RequireCustomer, db: DbSession):
    customer = customer_for(user, db)
    rows = db.scalars(select(SubscriptionChangeRequest).options(
        joinedload(SubscriptionChangeRequest.subscription), joinedload(SubscriptionChangeRequest.requested_plan)
    ).where(SubscriptionChangeRequest.customer_id == customer.id).order_by(SubscriptionChangeRequest.created_at.desc())).all()
    return [CustomerRequestPublic(id=row.id, subscription_id=row.subscription_id, subscription_number=row.subscription.number,
        request_type=row.request_type, requested_plan_id=row.requested_plan_id,
        requested_plan_name=row.requested_plan.name if row.requested_plan else None, status=row.status, notes=row.notes,
        created_at=row.created_at, decided_at=row.decided_at) for row in rows]


@router.get("/profile", response_model=CustomerProfilePublic)
def my_profile(user: RequireCustomer, db: DbSession):
    customer_id = customer_id_for(user, db)
    customer = db.get(Customer, customer_id)
    return CustomerProfilePublic(
        name=user.name,
        email=user.email,
        company_name=customer.company_name,
        phone=customer.phone,
        billing_address=customer.billing_address,
        gstin=customer.gstin,
        state_code=customer.state_code,
    )


@router.patch("/profile", response_model=CustomerProfilePublic)
def update_my_profile(payload: CustomerProfileUpdate, user: RequireCustomer, db: DbSession):
    customer_id = customer_id_for(user, db)
    customer = db.get(Customer, customer_id)
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        name = updates.pop("name")
        if name is None or len(name.strip()) < 2:
            raise AppError("Name must contain at least 2 characters", status_code=422, code="invalid_name")
        user.name = name.strip()
    for key, value in updates.items():
        setattr(customer, key, value.strip() if isinstance(value, str) else value)
    db.commit()
    return CustomerProfilePublic(
        name=user.name,
        email=user.email,
        company_name=customer.company_name,
        phone=customer.phone,
        billing_address=customer.billing_address,
        gstin=customer.gstin,
        state_code=customer.state_code,
    )


@router.get("/summary", response_model=CustomerSummary)
def summary(user: RequireCustomer, db: DbSession):
    customer_id = customer_id_for(user, db)
    active = db.scalar(select(func.count()).select_from(Subscription).where(Subscription.customer_id == customer_id, Subscription.status == "active")) or 0
    balance = db.scalar(select(func.coalesce(func.sum(Invoice.total_amount - Invoice.amount_paid - Invoice.credited_amount), 0)).where(Invoice.customer_id == customer_id, Invoice.status != "cancelled")) or 0
    overdue = db.scalar(select(func.count()).select_from(Invoice).where(Invoice.customer_id == customer_id, Invoice.status == "overdue")) or 0
    payments = db.scalar(select(func.count()).select_from(Payment).join(Invoice).where(Invoice.customer_id == customer_id)) or 0
    return CustomerSummary(active_subscriptions=active, outstanding_balance=balance, overdue_invoices=overdue, payments_recorded=payments)


@router.get("/subscriptions", response_model=list[SubscriptionPublic])
def my_subscriptions(user: RequireCustomer, db: DbSession):
    customer_id = customer_id_for(user, db)
    rows = db.scalars(select(Subscription).options(joinedload(Subscription.customer).joinedload(Customer.user)).where(Subscription.customer_id == customer_id).order_by(Subscription.created_at.desc())).unique().all()
    return [subscription_public(row) for row in rows]


@router.get("/invoices", response_model=list[InvoicePublic])
def my_invoices(user: RequireCustomer, db: DbSession):
    customer_id = customer_id_for(user, db)
    rows = db.scalars(select(Invoice).options(joinedload(Invoice.customer).joinedload(Customer.user)).where(Invoice.customer_id == customer_id).order_by(Invoice.created_at.desc())).unique().all()
    return [invoice_public(row) for row in rows]


@router.post("/invoices/{invoice_id}/payment-orders", response_model=PaymentOrderPublic)
def create_payment_order(invoice_id: int, user: RequireCustomer, db: DbSession):
    if not settings.RAZORPAY_KEY_ID.startswith("rzp_test_") or not settings.RAZORPAY_KEY_SECRET:
        raise AppError("Online payments are not configured for test mode", status_code=503, code="payment_gateway_unavailable")
    customer = customer_for(user, db)
    invoice = db.scalar(select(Invoice).options(joinedload(Invoice.customer).joinedload(Customer.user)).where(
        Invoice.id == invoice_id, Invoice.customer_id == customer.id, Invoice.company_id == customer.company_id).with_for_update())
    if not invoice:
        raise AppError("Invoice not found", status_code=404, code="not_found")
    balance = invoice_balance_due(invoice)
    if invoice.status == "cancelled" or balance <= 0:
        raise AppError("This invoice has no payable balance", status_code=409, code="invoice_not_payable")
    if invoice.currency_code not in {"INR", "USD"}:
        raise AppError("Online test payments currently support INR and USD invoices", status_code=422, code="currency_not_supported")
    amount_minor = int((balance * 100).quantize(Decimal("1")))
    existing = db.scalar(select(PaymentAttempt).where(PaymentAttempt.invoice_id == invoice.id,
        PaymentAttempt.customer_id == customer.id, PaymentAttempt.status == "pending",
        PaymentAttempt.amount_minor == amount_minor, PaymentAttempt.currency_code == invoice.currency_code)
        .order_by(PaymentAttempt.created_at.desc()))
    if existing:
        return PaymentOrderPublic(order_id=existing.gateway_order_id, amount=existing.amount_minor,
            currency=existing.currency_code, key_id=settings.RAZORPAY_KEY_ID, company_name=invoice.company_name,
            customer_name=invoice.customer.user.name, customer_email=invoice.customer.user.email)
    try:
        response = httpx.post("https://api.razorpay.com/v1/orders",
            json={"amount": amount_minor, "currency": invoice.currency_code,
                "receipt": f"{invoice.number}-{secrets.token_hex(2)}",
                "notes": {"invoice_id": str(invoice.id), "company_id": str(invoice.company_id)}},
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET), timeout=10)
        response.raise_for_status()
        order = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AppError("Unable to create a payment order with the gateway", status_code=502, code="payment_gateway_error") from exc
    if order.get("amount") != amount_minor or order.get("currency") != invoice.currency_code or not order.get("id"):
        raise AppError("Payment gateway returned an invalid order", status_code=502, code="payment_gateway_error")
    attempt = PaymentAttempt(company_id=invoice.company_id, customer_id=customer.id, invoice_id=invoice.id,
        gateway_order_id=order["id"], amount_minor=amount_minor, currency_code=invoice.currency_code, status="pending")
    db.add(attempt)
    db.commit()
    return PaymentOrderPublic(order_id=attempt.gateway_order_id, amount=attempt.amount_minor,
        currency=attempt.currency_code, key_id=settings.RAZORPAY_KEY_ID, company_name=invoice.company_name,
        customer_name=invoice.customer.user.name, customer_email=invoice.customer.user.email)


@router.post("/invoices/{invoice_id}/verify-payment", response_model=PaymentPublic)
def verify_payment(invoice_id: int, payload: PaymentVerificationRequest, user: RequireCustomer, db: DbSession):
    if not settings.RAZORPAY_KEY_ID.startswith("rzp_test_") or not settings.RAZORPAY_KEY_SECRET:
        raise AppError("Online payments are not configured for test mode", status_code=503, code="payment_gateway_unavailable")
    customer = customer_for(user, db)
    attempt = db.scalar(select(PaymentAttempt).where(PaymentAttempt.gateway_order_id == payload.order_id,
        PaymentAttempt.invoice_id == invoice_id, PaymentAttempt.customer_id == customer.id,
        PaymentAttempt.company_id == customer.company_id).with_for_update())
    if not attempt:
        raise AppError("Payment order not found", status_code=404, code="payment_order_not_found")
    if attempt.status == "paid" and attempt.payment_record_id:
        payment = db.get(Payment, attempt.payment_record_id)
        return PaymentPublic.model_validate(payment)
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(),
        f"{payload.order_id}|{payload.payment_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, payload.signature):
        raise AppError("Payment signature is invalid", status_code=400, code="invalid_payment_signature")
    try:
        response = httpx.get(f"https://api.razorpay.com/v1/payments/{payload.payment_id}",
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET), timeout=10)
        response.raise_for_status()
        gateway_payment = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AppError("Unable to verify payment with the gateway", status_code=502, code="payment_gateway_error") from exc
    if (gateway_payment.get("id") != payload.payment_id or gateway_payment.get("order_id") != attempt.gateway_order_id
        or gateway_payment.get("amount") != attempt.amount_minor or gateway_payment.get("currency") != attempt.currency_code
        or gateway_payment.get("status") != "captured" or gateway_payment.get("captured") is not True):
        raise AppError("Payment is not captured for this invoice", status_code=409, code="payment_not_captured")
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.customer_id == customer.id,
        Invoice.company_id == customer.company_id).with_for_update())
    if not invoice:
        raise AppError("Invoice not found", status_code=404, code="not_found")
    amount = (Decimal(attempt.amount_minor) / Decimal(100)).quantize(Decimal("0.01"))
    if amount > invoice_balance_due(invoice):
        attempt.status = "captured_unapplied"
        attempt.gateway_payment_id = payload.payment_id
        db.commit()
        raise AppError("Payment was captured after the invoice balance changed; contact the company for reconciliation", status_code=409, code="payment_reconciliation_required")
    payment = Payment(number=f"PAY-{date.today():%y%m%d}-{secrets.token_hex(3).upper()}", invoice_id=invoice.id,
        amount=amount, method=(gateway_payment.get("method") or "card")[:24], reference=payload.payment_id, paid_at=date.today())
    db.add(payment)
    invoice.amount_paid += amount
    refresh_invoice_status(invoice)
    db.flush()
    attempt.status = "paid"
    attempt.gateway_payment_id = payload.payment_id
    attempt.payment_record_id = payment.id
    record_audit(db, user.id, "customer.payment_verified", "payment", payment.id,
        {"invoice_id": invoice.id, "gateway": "razorpay", "gateway_payment_id": payload.payment_id})
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/invoices/{invoice_id}/pdf")
def download_my_invoice(invoice_id: int, user: RequireCustomer, db: DbSession):
    customer_id = customer_id_for(user, db)
    invoice = db.scalar(select(Invoice).options(joinedload(Invoice.customer).joinedload(Customer.user)).where(Invoice.id == invoice_id, Invoice.customer_id == customer_id))
    if not invoice:
        raise AppError("Invoice not found", status_code=404, code="not_found")
    return StreamingResponse(BytesIO(render_invoice(invoice)), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{invoice.number}.pdf"'})


@router.get("/payments", response_model=list[PaymentRecord])
def my_payments(user: RequireCustomer, db: DbSession):
    customer_id = customer_id_for(user, db)
    rows = db.scalars(select(Payment).join(Payment.invoice).options(joinedload(Payment.invoice).joinedload(Invoice.customer).joinedload(Customer.user)).where(Invoice.customer_id == customer_id).order_by(Payment.paid_at.desc(), Payment.id.desc())).unique().all()
    return [PaymentRecord(id=row.id, number=row.number, invoice_id=row.invoice_id, amount=row.amount, refunded_amount=row.refunded_amount, method=row.method, reference=row.reference, paid_at=row.paid_at, created_at=row.created_at, invoice_number=row.invoice.number, customer_name=user.name) for row in rows]
