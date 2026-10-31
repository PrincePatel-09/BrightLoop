import secrets
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.deps import DbSession, RequireStaff
from app.core.dates import add_billing_interval
from app.core.exceptions import AppError
from app.models.catalog import Discount, Plan, ProductVariant
from app.models.customer import Customer
from app.models.subscription import Quotation, Subscription
from app.schemas.subscription import (
    QuotationCreate,
    QuotationPublic,
    QuotationStatusUpdate,
    SubscriptionPublic,
    SubscriptionStatusUpdate,
)
from app.services.audit_service import record_audit

router = APIRouter()


def quote_public(row: Quotation) -> QuotationPublic:
    return QuotationPublic(
        **{key: getattr(row, key) for key in (
            "id", "number", "customer_id", "plan_id", "product_name", "plan_name", "billing_interval",
            "interval_count", "quantity", "unit_price", "status", "valid_until", "notes", "discount_code", "discount_amount", "created_at",
        )},
        line_items=row.line_items or [],
        customer_name=row.customer.user.name,
        customer_email=row.customer.user.email,
    )


def subscription_public(row: Subscription) -> SubscriptionPublic:
    return SubscriptionPublic(
        **{key: getattr(row, key) for key in (
            "id", "number", "customer_id", "plan_id", "quotation_id", "product_name", "plan_name",
            "billing_interval", "interval_count", "quantity", "unit_price", "discount_code", "discount_amount", "status", "start_date",
            "next_billing_date", "features", "created_at",
        )},
        line_items=row.line_items or [],
        customer_name=row.customer.user.name,
        customer_email=row.customer.user.email,
    )


@router.get("/quotations", response_model=list[QuotationPublic])
def list_quotations(
    _staff: RequireStaff,
    db: DbSession,
    status: str | None = Query(default=None),
    customer_id: int | None = Query(default=None, gt=0),
):
    query = select(Quotation).options(joinedload(Quotation.customer).joinedload(Customer.user)).order_by(Quotation.created_at.desc())
    if status:
        query = query.where(Quotation.status == status)
    if customer_id:
        query = query.where(Quotation.customer_id == customer_id)
    return [quote_public(row) for row in db.scalars(query).unique().all()]


@router.post("/quotations", response_model=QuotationPublic, status_code=201)
def create_quotation(payload: QuotationCreate, staff: RequireStaff, db: DbSession):
    if payload.valid_until < date.today():
        raise AppError("Quotation expiry must be today or later", status_code=422, code="invalid_expiry")
    customer = db.get(Customer, payload.customer_id)
    plan = db.scalar(select(Plan).options(joinedload(Plan.product)).where(Plan.id == payload.plan_id))
    if not customer or not customer.user.is_active:
        raise AppError("Active customer not found", status_code=404, code="customer_not_found")
    if not plan or not plan.is_active or not plan.product.is_active:
        raise AppError("Active plan not found", status_code=404, code="plan_not_found")
    if customer.company_id != plan.product.company_id:
        raise AppError("Customer and product must belong to the same company workspace", status_code=422, code="company_mismatch")
    variant = None
    if payload.variant_id is not None:
        variant = db.get(ProductVariant, payload.variant_id)
        if not variant or not variant.is_active or variant.product_id != plan.product_id:
            raise AppError("Active variant for the selected product not found", status_code=422, code="invalid_variant")
    unit_price = (plan.price + (variant.price_extra if variant else Decimal("0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    plan_display_name = f"{plan.name} ({variant.attribute}: {variant.name})" if variant else plan.name
    subtotal = (unit_price * payload.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discount = None
    discount_amount = Decimal("0.00")
    discount_code = payload.discount_code.strip().upper() if payload.discount_code else None
    if discount_code:
        discount = db.scalar(select(Discount).where(Discount.code == discount_code, Discount.company_id == customer.company_id))
        today = date.today()
        if not discount or not discount.is_active or (discount.starts_at and discount.starts_at > today) or (discount.ends_at and discount.ends_at < today):
            raise AppError("Discount code is invalid or inactive", status_code=422, code="invalid_discount_code")
        if discount.usage_limit is not None and discount.times_used >= discount.usage_limit:
            raise AppError("Discount usage limit has been reached", status_code=409, code="discount_limit_reached")
        if subtotal < discount.minimum_amount:
            raise AppError("Quotation does not meet the discount minimum amount", status_code=422, code="discount_minimum_not_met")
        discount_amount = (subtotal * discount.value / Decimal("100") if discount.discount_type == "percentage" else discount.value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        discount_amount = min(subtotal, discount_amount)
    quote = Quotation(
        company_id=customer.company_id,
        number=f"QT-{date.today():%y%m%d}-{secrets.token_hex(3).upper()}",
        customer_id=customer.id,
        plan_id=plan.id,
        product_name=plan.product.name,
        plan_name=plan_display_name,
        billing_interval=plan.billing_interval,
        interval_count=plan.interval_count,
        quantity=payload.quantity,
        unit_price=unit_price,
        valid_until=payload.valid_until,
        notes=payload.notes,
        discount_id=discount.id if discount else None,
        discount_code=discount.code if discount else None,
        discount_type=discount.discount_type if discount else None,
        discount_value=discount.value if discount else None,
        discount_amount=discount_amount,
        line_items=[{"plan_id": plan.id, "description": f"{plan.product.name} - {plan_display_name}",
            "product_name": plan.product.name, "plan_name": plan_display_name,
            "quantity": payload.quantity, "unit_price": str(unit_price)}],
        status="draft",
    )
    db.add(quote)
    db.flush()
    record_audit(db, staff.id, "quotation.created", "quotation", quote.id, {"customer_id": customer.id, "plan_id": plan.id})
    db.commit()
    row = db.scalar(select(Quotation).options(joinedload(Quotation.customer).joinedload(Customer.user)).where(Quotation.id == quote.id))
    return quote_public(row)


@router.patch("/quotations/{quotation_id}", response_model=QuotationPublic)
def update_quotation_status(quotation_id: int, payload: QuotationStatusUpdate, staff: RequireStaff, db: DbSession):
    quote = db.scalar(select(Quotation).options(joinedload(Quotation.customer).joinedload(Customer.user)).where(Quotation.id == quotation_id))
    if not quote:
        raise AppError("Quotation not found", status_code=404, code="not_found")
    allowed = {"draft": {"sent", "cancelled"}, "sent": {"accepted", "cancelled"}, "accepted": {"cancelled"}}
    if payload.status not in allowed.get(quote.status, set()):
        raise AppError(f"Cannot change quotation from {quote.status} to {payload.status}", status_code=409, code="invalid_transition")
    if payload.status == "accepted" and quote.valid_until < date.today():
        raise AppError("Expired quotations cannot be accepted", status_code=409, code="quotation_expired")
    quote.status = payload.status
    record_audit(db, staff.id, "quotation.status_changed", "quotation", quote.id, {"status": payload.status})
    db.commit()
    return quote_public(quote)


@router.post("/quotations/{quotation_id}/convert", response_model=SubscriptionPublic, status_code=201)
def convert_quotation(quotation_id: int, staff: RequireStaff, db: DbSession):
    quote = db.scalar(select(Quotation).options(joinedload(Quotation.customer).joinedload(Customer.user)).where(Quotation.id == quotation_id))
    if not quote:
        raise AppError("Quotation not found", status_code=404, code="not_found")
    if quote.status != "accepted" or quote.valid_until < date.today():
        raise AppError("Only accepted, unexpired quotations can be converted", status_code=409, code="not_convertible")
    existing = db.scalar(select(Subscription.id).where(Subscription.quotation_id == quote.id))
    if existing:
        raise AppError("Quotation has already been converted", status_code=409, code="already_converted")
    start = date.today()
    subscription = Subscription(
        company_id=quote.company_id,
        number=f"SN-{start:%y%m%d}-{secrets.token_hex(3).upper()}",
        customer_id=quote.customer_id,
        plan_id=quote.plan_id,
        quotation_id=quote.id,
        discount_id=quote.discount_id,
        product_name=quote.product_name,
        plan_name=quote.plan_name,
        billing_interval=quote.billing_interval,
        interval_count=quote.interval_count,
        quantity=quote.quantity,
        unit_price=quote.unit_price,
        discount_code=quote.discount_code,
        discount_type=quote.discount_type,
        discount_value=quote.discount_value,
        discount_amount=quote.discount_amount,
        features=list(quote.plan.features or []),
        line_items=quote.line_items,
        start_date=start,
        next_billing_date=start,
        status="active",
    )
    db.add(subscription)
    if quote.discount_id is not None:
        discount = db.scalar(select(Discount).where(Discount.id == quote.discount_id,
            Discount.company_id == quote.company_id).with_for_update())
        today = date.today()
        if not discount or not discount.is_active or (discount.starts_at and discount.starts_at > today) or (discount.ends_at and discount.ends_at < today):
            raise AppError("Discount is no longer active", status_code=409, code="discount_inactive")
        if discount.usage_limit is not None and discount.times_used >= discount.usage_limit:
            raise AppError("Discount usage limit has been reached", status_code=409, code="discount_limit_reached")
        discount.times_used += 1
    db.flush()
    quote.status = "converted"
    record_audit(db, staff.id, "quotation.converted", "quotation", quote.id, {"subscription_id": subscription.id})
    record_audit(db, staff.id, "subscription.created", "subscription", subscription.id, {"quotation_id": quote.id})
    db.commit()
    row = db.scalar(select(Subscription).options(joinedload(Subscription.customer).joinedload(Customer.user)).where(Subscription.id == subscription.id))
    return subscription_public(row)


@router.get("/subscriptions", response_model=list[SubscriptionPublic])
def list_subscriptions(_staff: RequireStaff, db: DbSession, status: str | None = None, customer_id: int | None = None):
    query = select(Subscription).options(joinedload(Subscription.customer).joinedload(Customer.user)).order_by(Subscription.created_at.desc())
    if status:
        query = query.where(Subscription.status == status)
    if customer_id:
        query = query.where(Subscription.customer_id == customer_id)
    return [subscription_public(row) for row in db.scalars(query).unique().all()]


@router.patch("/subscriptions/{subscription_id}", response_model=SubscriptionPublic)
def update_subscription_status(subscription_id: int, payload: SubscriptionStatusUpdate, staff: RequireStaff, db: DbSession):
    sub = db.scalar(select(Subscription).options(joinedload(Subscription.customer).joinedload(Customer.user)).where(Subscription.id == subscription_id))
    if not sub:
        raise AppError("Subscription not found", status_code=404, code="not_found")
    if sub.status == "cancelled" or sub.status == "expired":
        raise AppError("Cancelled or expired subscriptions cannot be changed", status_code=409, code="invalid_transition")
    if payload.status == "cancelled":
        sub.cancelled_at = date.today()
    elif payload.status == "active":
        sub.cancelled_at = None
    sub.status = payload.status
    record_audit(db, staff.id, "subscription.status_changed", "subscription", sub.id, {"status": payload.status})
    db.commit()
    return subscription_public(sub)
