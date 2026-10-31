import secrets
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.core.deps import DbSession, RequireCompanyAdmin, RequireCompanyStaff
from app.core.exceptions import AppError
from app.core.config import settings
from app.core.security import hash_password
from app.models.base import AppSetting
from app.models.catalog import Discount, Plan, Product, ProductVariant
from app.models.company import Company
from app.models.customer import Customer
from app.models.subscription import CreditNote, Invoice, Payment, PaymentRefund, Quotation, QuotationTemplate, Subscription
from app.models.subscription import SubscriptionChangeRequest
from app.models.user import User
from app.schemas.catalog import (PlanCreate, PlanPublic, PlanUpdate, ProductCreate, ProductPublic, ProductUpdate,
    ProductVariantCreate, ProductVariantPublic, ProductVariantUpdate)
from app.schemas.customer import CustomerPublic
from app.schemas.subscription import QuotationPublic, QuotationStatusUpdate, SubscriptionPublic, SubscriptionStatusUpdate
from app.schemas.billing import (BillingRunRequest, BillingRunResult, CreditNoteCreate, CreditNoteDecision,
    CreditNotePublic, PaymentCreate, PaymentPublic, PaymentRefundCreate, PaymentRefundPublic)
from app.schemas.user import StaffUpdateRequest, UserPublic
from app.schemas.pricing import DiscountCreate, DiscountPublic, DiscountUpdate
from app.schemas.workspace import (CompanyStaffCreateRequest, WorkspaceCompanySettings, WorkspaceCompanySettingsUpdate,
    ChangeRequestDecision, WorkspaceOverview, WorkspaceQuotationCreate, WorkspaceQuotationUpdate,
    QuotationTemplateCreate, QuotationTemplatePublic, QuotationLineItemInput)
from app.services.audit_service import record_audit
from app.services.billing_service import process_due_subscriptions
from app.services.invoice_pdf import render_invoice
from app.services.invoice_service import invoice_balance_due, refresh_invoice_status
from app.services.email_service import send_invoice_notice

router = APIRouter()


def company_id_for(user: User) -> int:
    if user.company_id is None:
        raise AppError("Your account is not assigned to a company workspace", status_code=403, code="company_required")
    return user.company_id


def workspace_settings(db: DbSession, company_id: int) -> WorkspaceCompanySettings:
    company = db.get(Company, company_id)
    values = {row.key.split(":", 2)[2]: row.value for row in db.scalars(
        select(AppSetting).where(AppSetting.key.like(f"company:{company_id}:%"))).all()}
    return WorkspaceCompanySettings(
        name=company.name, legal_name=company.legal_name, email=company.email, phone=company.phone,
        address=company.address, tax_id=company.tax_id, currency_code=values.get("currency_code", "INR"),
        invoice_prefix=values.get("invoice_prefix", "INV"), payment_terms_days=int(values.get("payment_terms_days", "14")),
        state_name=values.get("state_name"), state_code=values.get("state_code"),
        gst_rate_percent=Decimal(values.get("gst_rate_percent", "0")),
    )


@router.get("/settings", response_model=WorkspaceCompanySettings)
def get_workspace_settings(user: RequireCompanyStaff, db: DbSession):
    return workspace_settings(db, company_id_for(user))


@router.put("/settings", response_model=WorkspaceCompanySettings)
def update_workspace_settings(payload: WorkspaceCompanySettingsUpdate, user: RequireCompanyAdmin, db: DbSession):
    company_id = company_id_for(user)
    company = db.get(Company, company_id)
    values = payload.model_dump(exclude_unset=True)
    keys = list(values)
    for key in ("name", "legal_name", "email", "phone", "address", "tax_id"):
        if key in values:
            setattr(company, key, values.pop(key))
    for key, value in values.items():
        setting_key = f"company:{company_id}:{key}"
        row = db.get(AppSetting, setting_key)
        if row:
            row.value = str(value)
        else:
            db.add(AppSetting(key=setting_key, value=str(value)))
    current = {row.key.split(":", 2)[2]: row.value for row in db.scalars(
        select(AppSetting).where(AppSetting.key.like(f"company:{company_id}:%"))).all()}
    current.update({key: str(value) for key, value in payload.model_dump(exclude_unset=True).items()
        if key in {"state_code", "gst_rate_percent"}})
    if Decimal(current.get("gst_rate_percent", "0")) > 0 and (not company.tax_id or not current.get("state_code")):
        raise AppError("GST requires a company GSTIN and registered state code", status_code=422, code="gst_configuration_incomplete")
    record_audit(db, user.id, "workspace.settings_updated", "company", company_id, {"keys": keys})
    db.commit()
    return workspace_settings(db, company_id)


@router.get("/discounts", response_model=list[DiscountPublic])
def list_workspace_discounts(user: RequireCompanyStaff, db: DbSession):
    return db.scalars(select(Discount).where(Discount.company_id == company_id_for(user)).order_by(Discount.code)).all()


@router.post("/discounts", response_model=DiscountPublic, status_code=201)
def create_workspace_discount(payload: DiscountCreate, user: RequireCompanyAdmin, db: DbSession):
    company_id = company_id_for(user)
    values = payload.model_dump(exclude={"company_id"})
    if values["discount_type"] == "percentage" and values["value"] > 100:
        raise AppError("Percentage discounts cannot exceed 100", status_code=422, code="invalid_discount")
    if values["starts_at"] and values["ends_at"] and values["ends_at"] < values["starts_at"]:
        raise AppError("Discount end date must be on or after its start date", status_code=422, code="invalid_discount_dates")
    if db.scalar(select(Discount.id).where(Discount.company_id == company_id, Discount.code == values["code"])):
        raise AppError("A discount with this code already exists in this workspace", status_code=409, code="discount_code_taken")
    discount = Discount(company_id=company_id, **values, is_active=True, times_used=0)
    db.add(discount); db.flush()
    record_audit(db, user.id, "workspace.discount_created", "discount", discount.id, {"company_id": company_id})
    db.commit(); db.refresh(discount)
    return discount


@router.patch("/discounts/{discount_id}", response_model=DiscountPublic)
def update_workspace_discount(discount_id: int, payload: DiscountUpdate, user: RequireCompanyAdmin, db: DbSession):
    company_id = company_id_for(user)
    discount = db.scalar(select(Discount).where(Discount.id == discount_id, Discount.company_id == company_id))
    if not discount:
        raise AppError("Discount not found", status_code=404, code="not_found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(discount, key, value)
    if discount.discount_type == "percentage" and discount.value > 100:
        raise AppError("Percentage discounts cannot exceed 100", status_code=422, code="invalid_discount")
    if discount.starts_at and discount.ends_at and discount.ends_at < discount.starts_at:
        raise AppError("Discount end date must be on or after its start date", status_code=422, code="invalid_discount_dates")
    record_audit(db, user.id, "workspace.discount_updated", "discount", discount.id, {"company_id": company_id})
    db.commit(); db.refresh(discount)
    return discount


def scoped_subscription_public(row: Subscription) -> SubscriptionPublic:
    return SubscriptionPublic(
        **{key: getattr(row, key) for key in (
            "id", "number", "customer_id", "plan_id", "quotation_id", "product_name", "plan_name",
            "billing_interval", "interval_count", "quantity", "unit_price", "discount_code", "discount_amount", "status",
            "start_date", "next_billing_date", "features", "created_at",
        )},
        line_items=row.line_items or [],
        customer_name=row.customer.user.name,
        customer_email=row.customer.user.email,
    )


def scoped_quotation_public(row: Quotation) -> QuotationPublic:
    return QuotationPublic(
        **{key: getattr(row, key) for key in (
            "id", "number", "customer_id", "plan_id", "product_name", "plan_name", "billing_interval",
            "interval_count", "quantity", "unit_price", "status", "valid_until", "notes", "discount_code", "discount_amount", "created_at",
        )},
        line_items=row.line_items or [],
        customer_name=row.customer.user.name,
        customer_email=row.customer.user.email,
    )


def quote_line_items(db: DbSession, company_id: int, base_plan: Plan, base_quantity: int,
    extra_lines: list[QuotationLineItemInput]) -> list[dict]:
    plans = {}
    if extra_lines:
        plans = {plan.id: plan for plan in db.scalars(select(Plan).options(joinedload(Plan.product)).join(Product).where(
            Plan.id.in_([line.plan_id for line in extra_lines]), Product.company_id == company_id,
            Plan.is_active.is_(True), Product.is_active.is_(True))).unique().all()}
    if len(plans) != len({line.plan_id for line in extra_lines}):
        raise AppError("Every quotation line must use an active plan in this workspace", status_code=422, code="invalid_quote_line")
    lines = [{"plan_id": base_plan.id, "description": f"{base_plan.product.name} - {base_plan.name}",
        "product_name": base_plan.product.name, "plan_name": base_plan.name,
        "quantity": base_quantity, "unit_price": str(base_plan.price)}]
    for item in extra_lines:
        plan = plans[item.plan_id]
        if plan.billing_interval != base_plan.billing_interval or plan.interval_count != base_plan.interval_count:
            raise AppError("All quotation lines must share the primary plan billing interval", status_code=422, code="quote_interval_mismatch")
        lines.append({"plan_id": plan.id, "description": f"{plan.product.name} - {plan.name}",
            "product_name": plan.product.name, "plan_name": plan.name,
            "quantity": item.quantity, "unit_price": str(plan.price)})
    return lines


def quote_lines_total(lines: list[dict]) -> Decimal:
    return sum((Decimal(str(line["unit_price"])) * int(line["quantity"]) for line in lines), Decimal("0.00")).quantize(Decimal("0.01"))


@router.get("/overview", response_model=WorkspaceOverview)
def overview(user: RequireCompanyStaff, db: DbSession):
    company_id = company_id_for(user)
    active = db.scalars(select(Subscription).where(Subscription.company_id == company_id, Subscription.status == "active")).all()
    mrr = Decimal("0.00")
    for subscription in active:
        amount = quote_lines_total(subscription.line_items) if subscription.line_items else subscription.unit_price * subscription.quantity
        count = max(subscription.interval_count, 1)
        if subscription.billing_interval == "month": mrr += amount / count
        elif subscription.billing_interval == "year": mrr += amount / (12 * count)
        elif subscription.billing_interval == "week": mrr += amount * Decimal(52) / (12 * count)
        elif subscription.billing_interval == "day": mrr += amount * Decimal(365) / (12 * count)
    mrr = mrr.quantize(Decimal("0.01"))
    return WorkspaceOverview(
        customers=db.scalar(select(func.count()).select_from(Customer).where(Customer.company_id == company_id)) or 0,
        products=db.scalar(select(func.count()).select_from(Product).where(Product.company_id == company_id, Product.is_active.is_(True))) or 0,
        active_subscriptions=len(active),
        revenue_received=db.scalar(select(func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)).join(Invoice).where(Invoice.company_id == company_id)) or 0,
        outstanding_balance=db.scalar(select(func.coalesce(func.sum(Invoice.total_amount - Invoice.amount_paid - Invoice.credited_amount), 0)).where(Invoice.company_id == company_id, Invoice.status != "cancelled")) or 0,
        mrr=mrr,
        arr=(mrr * 12).quantize(Decimal("0.01")),
    )


@router.get("/products", response_model=list[ProductPublic])
def list_products(user: RequireCompanyStaff, db: DbSession, include_inactive: bool = False):
    query = select(Product).where(Product.company_id == company_id_for(user)).order_by(Product.name)
    if not include_inactive:
        query = query.where(Product.is_active.is_(True))
    return db.scalars(query).unique().all()


@router.post("/products", response_model=ProductPublic, status_code=201)
def create_product(payload: ProductCreate, user: RequireCompanyAdmin, db: DbSession):
    company_id = company_id_for(user)
    if db.scalar(select(Product.id).where(Product.sku == payload.sku)):
        raise AppError("A product with this SKU already exists", status_code=409, code="sku_taken")
    values = payload.model_dump(exclude={"company_id"})
    product = Product(company_id=company_id, **values)
    db.add(product)
    db.flush()
    record_audit(db, user.id, "workspace.product_created", "product", product.id, {"company_id": company_id})
    db.commit()
    db.refresh(product)
    return product


@router.patch("/products/{product_id}", response_model=ProductPublic)
def update_product(product_id: int, payload: ProductUpdate, user: RequireCompanyAdmin, db: DbSession):
    product = db.scalar(select(Product).where(Product.id == product_id, Product.company_id == company_id_for(user)))
    if not product:
        raise AppError("Product not found", status_code=404, code="not_found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    record_audit(db, user.id, "workspace.product_updated", "product", product.id, {"company_id": product.company_id})
    db.commit()
    db.refresh(product)
    return product


@router.post("/products/{product_id}/plans", response_model=PlanPublic, status_code=201)
def create_plan(product_id: int, payload: PlanCreate, user: RequireCompanyAdmin, db: DbSession):
    product = db.scalar(select(Product).where(Product.id == product_id, Product.company_id == company_id_for(user), Product.is_active.is_(True)))
    if not product:
        raise AppError("Active product not found", status_code=404, code="not_found")
    plan = Plan(product_id=product.id, **payload.model_dump())
    db.add(plan)
    db.flush()
    record_audit(db, user.id, "workspace.plan_created", "plan", plan.id, {"company_id": product.company_id, "product_id": product.id})
    db.commit()
    db.refresh(plan)
    return plan


@router.patch("/plans/{plan_id}", response_model=PlanPublic)
def update_plan(plan_id: int, payload: PlanUpdate, user: RequireCompanyAdmin, db: DbSession):
    plan = db.scalar(select(Plan).join(Product).where(Plan.id == plan_id, Product.company_id == company_id_for(user)))
    if not plan:
        raise AppError("Plan not found", status_code=404, code="not_found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    record_audit(db, user.id, "workspace.plan_updated", "plan", plan.id, {"company_id": user.company_id})
    db.commit(); db.refresh(plan)
    return plan


@router.post("/products/{product_id}/variants", response_model=ProductVariantPublic, status_code=201)
def create_variant(product_id: int, payload: ProductVariantCreate, user: RequireCompanyAdmin, db: DbSession):
    product = db.scalar(select(Product).where(Product.id == product_id, Product.company_id == company_id_for(user), Product.is_active.is_(True)))
    if not product:
        raise AppError("Active product not found", status_code=404, code="not_found")
    variant = ProductVariant(product_id=product.id, **payload.model_dump())
    db.add(variant); db.flush()
    record_audit(db, user.id, "workspace.variant_created", "product_variant", variant.id, {"company_id": product.company_id})
    db.commit(); db.refresh(variant)
    return variant


@router.patch("/variants/{variant_id}", response_model=ProductVariantPublic)
def update_variant(variant_id: int, payload: ProductVariantUpdate, user: RequireCompanyAdmin, db: DbSession):
    variant = db.scalar(select(ProductVariant).join(Product).where(
        ProductVariant.id == variant_id, Product.company_id == company_id_for(user)))
    if not variant:
        raise AppError("Variant not found", status_code=404, code="not_found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(variant, key, value)
    record_audit(db, user.id, "workspace.variant_updated", "product_variant", variant.id, {"company_id": user.company_id})
    db.commit(); db.refresh(variant)
    return variant


@router.get("/customers", response_model=list[CustomerPublic])
def list_customers(user: RequireCompanyStaff, db: DbSession, search: str | None = Query(default=None, max_length=120)):
    company_id = company_id_for(user)
    query = select(Customer).join(Customer.user).where(Customer.company_id == company_id).order_by(User.name, Customer.id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(User.name.ilike(term) | User.email.ilike(term) | Customer.company_name.ilike(term))
    return [CustomerPublic(id=row.id, name=row.user.name, email=row.user.email, is_active=row.user.is_active,
        company_name=row.company_name, phone=row.phone, billing_address=row.billing_address, created_at=row.created_at)
        for row in db.scalars(query.limit(100)).all()]


@router.get("/subscriptions", response_model=list[SubscriptionPublic])
def list_subscriptions(user: RequireCompanyStaff, db: DbSession, status: str | None = None):
    query = select(Subscription).options(joinedload(Subscription.customer).joinedload(Customer.user)).where(
        Subscription.company_id == company_id_for(user)).order_by(Subscription.created_at.desc())
    if status:
        query = query.where(Subscription.status == status)
    return [scoped_subscription_public(row) for row in db.scalars(query).unique().limit(200).all()]


@router.get("/requests")
def list_change_requests(user: RequireCompanyStaff, db: DbSession, status: str | None = None):
    query = select(SubscriptionChangeRequest).options(
        joinedload(SubscriptionChangeRequest.customer).joinedload(Customer.user),
        joinedload(SubscriptionChangeRequest.subscription), joinedload(SubscriptionChangeRequest.requested_plan),
    ).where(SubscriptionChangeRequest.company_id == company_id_for(user)).order_by(SubscriptionChangeRequest.created_at.desc())
    if status:
        query = query.where(SubscriptionChangeRequest.status == status)
    return [{"id": row.id, "subscription_id": row.subscription_id, "subscription_number": row.subscription.number,
        "customer_id": row.customer_id, "customer_name": row.customer.user.name, "customer_email": row.customer.user.email,
        "request_type": row.request_type, "requested_plan_id": row.requested_plan_id,
        "requested_plan_name": row.requested_plan.name if row.requested_plan else None,
        "status": row.status, "notes": row.notes, "created_at": row.created_at, "decided_at": row.decided_at}
        for row in db.scalars(query.limit(200)).unique().all()]


@router.patch("/requests/{request_id}")
def decide_change_request(request_id: int, payload: ChangeRequestDecision, user: RequireCompanyStaff, db: DbSession):
    company_id = company_id_for(user)
    request = db.scalar(select(SubscriptionChangeRequest).where(
        SubscriptionChangeRequest.id == request_id, SubscriptionChangeRequest.company_id == company_id).with_for_update())
    if not request:
        raise AppError("Change request not found", status_code=404, code="not_found")
    if request.status != "pending":
        raise AppError("Change request has already been decided", status_code=409, code="already_decided")
    subscription = db.scalar(select(Subscription).where(
        Subscription.id == request.subscription_id, Subscription.company_id == company_id).with_for_update())
    if not subscription:
        raise AppError("Subscription not found", status_code=404, code="not_found")
    if payload.status == "approved":
        if request.request_type == "pause":
            if subscription.status != "active": raise AppError("Only active subscriptions can be paused", status_code=409, code="invalid_transition")
            subscription.status = "paused"
        elif request.request_type == "resume":
            if subscription.status != "paused": raise AppError("Only paused subscriptions can be resumed", status_code=409, code="invalid_transition")
            subscription.status = "active"
        elif request.request_type == "cancel":
            if subscription.status in {"cancelled", "expired"}: raise AppError("Subscription is already closed", status_code=409, code="invalid_transition")
            subscription.status = "cancelled"; subscription.cancelled_at = date.today()
        else:
            plan = db.scalar(select(Plan).options(joinedload(Plan.product)).where(
                Plan.id == request.requested_plan_id, Plan.is_active.is_(True)))
            if not plan or plan.product.company_id != company_id:
                raise AppError("Requested plan is no longer available", status_code=409, code="plan_unavailable")
            subscription.plan_id = plan.id
            subscription.product_name = plan.product.name
            subscription.plan_name = plan.name
            subscription.billing_interval = plan.billing_interval
            subscription.interval_count = plan.interval_count
            subscription.unit_price = plan.price
            subscription.features = list(plan.features or [])
            subscription.line_items = [{"plan_id": plan.id, "description": f"{plan.product.name} - {plan.name}",
                "product_name": plan.product.name, "plan_name": plan.name,
                "quantity": subscription.quantity, "unit_price": str(plan.price)}]
    request.status = payload.status
    request.decided_by_user_id = user.id
    request.decided_at = datetime.now(timezone.utc)
    record_audit(db, user.id, "workspace.change_request_decided", "subscription_change_request", request.id,
        {"status": request.status, "request_type": request.request_type})
    db.commit()
    return {"id": request.id, "status": request.status, "request_type": request.request_type}


@router.get("/quotations", response_model=list[QuotationPublic])
def list_quotations(user: RequireCompanyStaff, db: DbSession, status: str | None = None):
    query = select(Quotation).options(joinedload(Quotation.customer).joinedload(Customer.user)).where(
        Quotation.company_id == company_id_for(user)).order_by(Quotation.created_at.desc())
    if status:
        query = query.where(Quotation.status == status)
    return [scoped_quotation_public(row) for row in db.scalars(query.limit(200)).unique().all()]


@router.get("/quotation-templates", response_model=list[QuotationTemplatePublic])
def list_quotation_templates(user: RequireCompanyStaff, db: DbSession):
    rows = db.scalars(select(QuotationTemplate).options(joinedload(QuotationTemplate.plan)).where(
        QuotationTemplate.company_id == company_id_for(user)).order_by(QuotationTemplate.name)).unique().all()
    return [QuotationTemplatePublic(id=row.id, name=row.name, plan_id=row.plan_id,
        plan_name=row.plan.name, quantity=row.quantity, valid_days=row.valid_days,
        notes=row.notes, discount_code=row.discount_code, line_items=row.line_items or [], created_at=row.created_at) for row in rows]


@router.post("/quotation-templates", response_model=QuotationTemplatePublic, status_code=201)
def create_quotation_template(payload: QuotationTemplateCreate, user: RequireCompanyStaff, db: DbSession):
    company_id = company_id_for(user)
    plan = db.scalar(select(Plan).join(Product).where(Plan.id == payload.plan_id,
        Product.company_id == company_id, Plan.is_active.is_(True), Product.is_active.is_(True)))
    if not plan:
        raise AppError("Active plan not found in this workspace", status_code=404, code="plan_not_found")
    lines = quote_line_items(db, company_id, plan, payload.quantity, payload.line_items)
    if db.scalar(select(QuotationTemplate.id).where(QuotationTemplate.company_id == company_id,
        QuotationTemplate.name == payload.name.strip())):
        raise AppError("A quotation template with this name already exists", status_code=409, code="template_name_taken")
    code = payload.discount_code.strip().upper() if payload.discount_code else None
    if code:
        discount = db.scalar(select(Discount).where(Discount.company_id == company_id, Discount.code == code))
        today = date.today()
        subtotal = quote_lines_total(lines)
        if not discount or not discount.is_active or (discount.starts_at and discount.starts_at > today) or (discount.ends_at and discount.ends_at < today):
            raise AppError("Discount code is invalid or inactive for this company", status_code=422, code="invalid_discount_code")
        if discount.usage_limit is not None and discount.times_used >= discount.usage_limit:
            raise AppError("Discount usage limit has been reached", status_code=409, code="discount_limit_reached")
        if subtotal < discount.minimum_amount:
            raise AppError("Quotation does not meet the discount minimum amount", status_code=422, code="discount_minimum_not_met")
    template = QuotationTemplate(company_id=company_id, name=payload.name.strip(), plan_id=plan.id,
        quantity=payload.quantity, valid_days=payload.valid_days, notes=payload.notes,
        discount_code=code, line_items=[{"plan_id": line.plan_id, "quantity": line.quantity} for line in payload.line_items])
    db.add(template); db.flush()
    record_audit(db, user.id, "workspace.quotation_template_created", "quotation_template", template.id,
        {"company_id": company_id, "plan_id": plan.id})
    db.commit(); db.refresh(template)
    return QuotationTemplatePublic(id=template.id, name=template.name, plan_id=template.plan_id,
        plan_name=plan.name, quantity=template.quantity, valid_days=template.valid_days,
        notes=template.notes, discount_code=template.discount_code, line_items=template.line_items or [], created_at=template.created_at)


@router.delete("/quotation-templates/{template_id}", status_code=204)
def delete_quotation_template(template_id: int, user: RequireCompanyStaff, db: DbSession):
    company_id = company_id_for(user)
    template = db.scalar(select(QuotationTemplate).where(QuotationTemplate.id == template_id,
        QuotationTemplate.company_id == company_id))
    if not template:
        raise AppError("Quotation template not found", status_code=404, code="not_found")
    record_audit(db, user.id, "workspace.quotation_template_deleted", "quotation_template", template.id,
        {"company_id": company_id})
    db.delete(template); db.commit()


@router.post("/quotations", response_model=QuotationPublic, status_code=201)
def create_quotation(payload: WorkspaceQuotationCreate, user: RequireCompanyStaff, db: DbSession):
    company_id = company_id_for(user)
    if payload.valid_until < date.today():
        raise AppError("Quotation expiry must be today or later", status_code=422, code="invalid_expiry")
    customer = db.scalar(select(Customer).options(joinedload(Customer.user)).where(
        Customer.id == payload.customer_id, Customer.company_id == company_id))
    plan = db.scalar(select(Plan).options(joinedload(Plan.product)).where(Plan.id == payload.plan_id))
    if not customer or not customer.user.is_active:
        raise AppError("Active customer not found", status_code=404, code="customer_not_found")
    if not plan or not plan.is_active or not plan.product.is_active or plan.product.company_id != company_id:
        raise AppError("Active plan not found in this workspace", status_code=404, code="plan_not_found")
    lines = quote_line_items(db, company_id, plan, payload.quantity, payload.line_items)
    discount = None
    discount_amount = Decimal("0.00")
    discount_code = payload.discount_code.strip().upper() if payload.discount_code else None
    subtotal = quote_lines_total(lines)
    if discount_code:
        discount = db.scalar(select(Discount).where(Discount.company_id == company_id, Discount.code == discount_code))
        today = date.today()
        if not discount or not discount.is_active or (discount.starts_at and discount.starts_at > today) or (discount.ends_at and discount.ends_at < today):
            raise AppError("Discount code is invalid or inactive for this company", status_code=422, code="invalid_discount_code")
        if discount.usage_limit is not None and discount.times_used >= discount.usage_limit:
            raise AppError("Discount usage limit has been reached", status_code=409, code="discount_limit_reached")
        if subtotal < discount.minimum_amount:
            raise AppError("Quotation does not meet the discount minimum amount", status_code=422, code="discount_minimum_not_met")
        discount_amount = (subtotal * discount.value / Decimal("100") if discount.discount_type == "percentage" else discount.value).quantize(Decimal("0.01"))
        discount_amount = min(subtotal, discount_amount)
    quote = Quotation(company_id=company_id, number=f"QT-{date.today():%y%m%d}-{secrets.token_hex(3).upper()}",
        customer_id=customer.id, plan_id=plan.id, product_name=plan.product.name, plan_name=plan.name,
        billing_interval=plan.billing_interval, interval_count=plan.interval_count, quantity=payload.quantity,
        unit_price=plan.price, valid_until=payload.valid_until, notes=payload.notes,
        discount_id=discount.id if discount else None, discount_code=discount.code if discount else None,
        discount_type=discount.discount_type if discount else None, discount_value=discount.value if discount else None,
        discount_amount=discount_amount, line_items=lines, status="draft")
    db.add(quote); db.flush()
    record_audit(db, user.id, "workspace.quotation_created", "quotation", quote.id, {"company_id": company_id})
    db.commit()
    row = db.scalar(select(Quotation).options(joinedload(Quotation.customer).joinedload(Customer.user)).where(Quotation.id == quote.id))
    return scoped_quotation_public(row)


@router.patch("/quotations/{quotation_id}", response_model=QuotationPublic)
def update_quotation_status(quotation_id: int, payload: WorkspaceQuotationUpdate, user: RequireCompanyStaff, db: DbSession):
    quote = db.scalar(select(Quotation).options(joinedload(Quotation.customer).joinedload(Customer.user)).where(
        Quotation.id == quotation_id, Quotation.company_id == company_id_for(user)))
    if not quote:
        raise AppError("Quotation not found", status_code=404, code="not_found")
    if payload.status is None:
        if quote.status != "draft":
            raise AppError("Only draft quotations can be edited", status_code=409, code="quotation_not_editable")
        changes = payload.model_dump(exclude_unset=True)
        if "valid_until" in changes and changes["valid_until"] < date.today():
            raise AppError("Quotation expiry must be today or later", status_code=422, code="invalid_expiry")
        quantity = changes.get("quantity", quote.quantity)
        if changes.get("line_items") is not None:
            base_plan = db.scalar(select(Plan).options(joinedload(Plan.product)).where(Plan.id == quote.plan_id))
            lines = quote_line_items(db, quote.company_id, base_plan, quantity, changes["line_items"])
            lines[0]["unit_price"] = str(quote.unit_price)
        else:
            lines = [dict(line) for line in (quote.line_items or [{"plan_id": quote.plan_id,
                "description": f"{quote.product_name} - {quote.plan_name}", "product_name": quote.product_name,
                "plan_name": quote.plan_name, "quantity": quote.quantity, "unit_price": str(quote.unit_price)}])]
            lines[0]["quantity"] = quantity
        subtotal = quote_lines_total(lines)
        code = changes.get("discount_code", quote.discount_code)
        discount = None
        discount_amount = Decimal("0.00")
        if code:
            code = code.strip().upper()
            discount = db.scalar(select(Discount).where(Discount.company_id == quote.company_id,
                Discount.code == code, Discount.is_active.is_(True)))
            today = date.today()
            if not discount or (discount.starts_at and discount.starts_at > today) or (discount.ends_at and discount.ends_at < today):
                raise AppError("Discount code is invalid or inactive for this company", status_code=422, code="invalid_discount_code")
            if discount.usage_limit is not None and discount.times_used >= discount.usage_limit:
                raise AppError("Discount usage limit has been reached", status_code=409, code="discount_limit_reached")
            if subtotal < discount.minimum_amount:
                raise AppError("Quotation does not meet the discount minimum amount", status_code=422, code="discount_minimum_not_met")
            discount_amount = (subtotal * discount.value / Decimal("100") if discount.discount_type == "percentage" else discount.value).quantize(Decimal("0.01"))
            discount_amount = min(subtotal, discount_amount)
        for key in ("quantity", "valid_until", "notes"):
            if key in changes:
                setattr(quote, key, changes[key])
        quote.discount_id = discount.id if discount else None
        quote.discount_code = discount.code if discount else None
        quote.discount_type = discount.discount_type if discount else None
        quote.discount_value = discount.value if discount else None
        quote.discount_amount = discount_amount
        quote.line_items = lines
        record_audit(db, user.id, "workspace.quotation_edited", "quotation", quote.id,
            {"company_id": quote.company_id, "fields": sorted(changes.keys())})
        db.commit()
        return scoped_quotation_public(quote)
    allowed = {"draft": {"sent", "cancelled"}, "sent": {"accepted", "cancelled"}, "accepted": {"cancelled"}}
    if payload.status not in allowed.get(quote.status, set()):
        raise AppError(f"Cannot change quotation from {quote.status} to {payload.status}", status_code=409, code="invalid_transition")
    if payload.status == "accepted" and quote.valid_until < date.today():
        raise AppError("Expired quotations cannot be accepted", status_code=409, code="quotation_expired")
    quote.status = payload.status
    record_audit(db, user.id, "workspace.quotation_status_changed", "quotation", quote.id, {"status": payload.status})
    db.commit()
    return scoped_quotation_public(quote)


@router.post("/quotations/{quotation_id}/convert", response_model=SubscriptionPublic, status_code=201)
def convert_quotation(quotation_id: int, user: RequireCompanyStaff, db: DbSession):
    company_id = company_id_for(user)
    quote = db.scalar(select(Quotation).options(joinedload(Quotation.customer).joinedload(Customer.user)).where(
        Quotation.id == quotation_id, Quotation.company_id == company_id))
    if not quote or quote.status != "accepted" or quote.valid_until < date.today():
        raise AppError("Only accepted, unexpired quotations can be converted", status_code=409, code="not_convertible")
    if db.scalar(select(Subscription.id).where(Subscription.quotation_id == quote.id)):
        raise AppError("Quotation has already been converted", status_code=409, code="already_converted")
    plan = db.get(Plan, quote.plan_id)
    today = date.today()
    subscription = Subscription(company_id=quote.company_id, number=f"SN-{today:%y%m%d}-{secrets.token_hex(3).upper()}",
        customer_id=quote.customer_id, plan_id=quote.plan_id, quotation_id=quote.id, product_name=quote.product_name,
        plan_name=quote.plan_name, billing_interval=quote.billing_interval, interval_count=quote.interval_count,
        discount_id=quote.discount_id, discount_code=quote.discount_code, discount_type=quote.discount_type,
        discount_value=quote.discount_value, discount_amount=quote.discount_amount,
        quantity=quote.quantity, unit_price=quote.unit_price, features=list(plan.features or []), start_date=today,
        next_billing_date=today, line_items=quote.line_items, status="active")
    db.add(subscription); db.flush()
    if quote.discount_id is not None:
        discount = db.scalar(select(Discount).where(Discount.id == quote.discount_id,
            Discount.company_id == company_id).with_for_update())
        if not discount or not discount.is_active or (discount.starts_at and discount.starts_at > today) or (discount.ends_at and discount.ends_at < today):
            raise AppError("Discount is no longer active", status_code=409, code="discount_inactive")
        if discount.usage_limit is not None and discount.times_used >= discount.usage_limit:
            raise AppError("Discount usage limit has been reached", status_code=409, code="discount_limit_reached")
        discount.times_used += 1
    quote.status = "converted"
    record_audit(db, user.id, "workspace.quotation_converted", "quotation", quote.id, {"subscription_id": subscription.id})
    db.commit()
    row = db.scalar(select(Subscription).options(joinedload(Subscription.customer).joinedload(Customer.user)).where(Subscription.id == subscription.id))
    return scoped_subscription_public(row)


@router.patch("/subscriptions/{subscription_id}", response_model=SubscriptionPublic)
def update_subscription(subscription_id: int, payload: SubscriptionStatusUpdate, user: RequireCompanyStaff, db: DbSession):
    subscription = db.scalar(select(Subscription).options(joinedload(Subscription.customer).joinedload(Customer.user)).where(
        Subscription.id == subscription_id, Subscription.company_id == company_id_for(user)))
    if not subscription:
        raise AppError("Subscription not found", status_code=404, code="not_found")
    if subscription.status in {"cancelled", "expired"}:
        raise AppError("Cancelled or expired subscriptions cannot be changed", status_code=409, code="invalid_transition")
    if payload.status == "cancelled": subscription.cancelled_at = date.today()
    elif payload.status == "active": subscription.cancelled_at = None
    subscription.status = payload.status
    record_audit(db, user.id, "workspace.subscription_status_changed", "subscription", subscription.id, {"status": payload.status})
    db.commit()
    return scoped_subscription_public(subscription)


@router.get("/invoices")
def list_invoices(user: RequireCompanyStaff, db: DbSession, status: str | None = None):
    company_id = company_id_for(user)
    query = select(Invoice).options(joinedload(Invoice.customer).joinedload(Customer.user)).where(
        Invoice.company_id == company_id).order_by(Invoice.created_at.desc())
    if status:
        query = query.where(Invoice.status == status)
    rows = db.scalars(query.limit(200)).unique().all()
    today = date.today()
    changed = False
    for invoice in rows:
        if invoice.status in {"issued", "partially_paid"} and invoice.due_date < today and invoice_balance_due(invoice) > 0:
            invoice.status = "overdue"
            changed = True
    if changed:
        db.commit()
    return [{"id": row.id, "number": row.number, "customer_name": row.customer.user.name,
        "customer_email": row.customer.user.email, "period_start": row.period_start, "period_end": row.period_end,
        "due_date": row.due_date, "product_name": row.product_name, "plan_name": row.plan_name,
        "currency_code": row.currency_code, "quantity": row.quantity, "unit_price": row.unit_price,
        "subtotal": row.subtotal, "tax_amount": row.tax_amount, "tax_details": row.tax_details,
        "discount_amount": row.discount_amount, "total_amount": row.total_amount, "amount_paid": row.amount_paid,
        "line_items": row.line_items or [],
        "credited_amount": row.credited_amount,
        "seller_address": row.seller_address, "seller_email": row.seller_email, "seller_phone": row.seller_phone,
        "seller_gstin": row.seller_gstin, "seller_state_name": row.seller_state_name,
        "seller_state_code": row.seller_state_code, "customer_gstin": row.customer_gstin,
        "customer_state_code": row.customer_state_code, "payment_terms": row.payment_terms,
        "balance_due": invoice_balance_due(row), "status": row.status} for row in rows]


@router.post("/billing/run", response_model=BillingRunResult)
def run_billing(payload: BillingRunRequest, user: RequireCompanyStaff, db: DbSession):
    created, periods = process_due_subscriptions(db, payload.as_of, user.id, company_id=company_id_for(user))
    return BillingRunResult(invoices_created=created, periods_processed=periods, as_of=payload.as_of)


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id: int, user: RequireCompanyStaff, db: DbSession):
    invoice = db.scalar(select(Invoice).options(joinedload(Invoice.customer).joinedload(Customer.user)).where(
        Invoice.id == invoice_id, Invoice.company_id == company_id_for(user)))
    if not invoice:
        raise AppError("Invoice not found", status_code=404, code="not_found")
    return StreamingResponse(BytesIO(render_invoice(invoice)), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.number}.pdf"'})


@router.post("/invoices/{invoice_id}/email", status_code=202)
def email_invoice(invoice_id: int, user: RequireCompanyStaff, db: DbSession):
    invoice = db.scalar(select(Invoice).options(joinedload(Invoice.customer).joinedload(Customer.user)).where(
        Invoice.id == invoice_id, Invoice.company_id == company_id_for(user)))
    if not invoice:
        raise AppError("Invoice not found", status_code=404, code="not_found")
    customer_email = invoice.customer.user.email
    if not customer_email:
        raise AppError("Customer has no email address", status_code=409, code="customer_email_missing")
    invoice_url = f"{settings.FRONTEND_URL.rstrip('/')}/my/invoices"
    if not send_invoice_notice(customer_email, invoice.number, invoice_url):
        raise AppError("Invoice email could not be delivered. Check SMTP configuration and try again.",
            status_code=503, code="email_delivery_failed")
    record_audit(db, user.id, "workspace.invoice_emailed", "invoice", invoice.id,
        {"company_id": invoice.company_id, "customer_email": customer_email})
    db.commit()
    return {"delivered": True, "recipient": customer_email}


@router.get("/credit-notes", response_model=list[CreditNotePublic])
def list_credit_notes(user: RequireCompanyStaff, db: DbSession):
    return db.scalars(select(CreditNote).where(CreditNote.company_id == company_id_for(user)).order_by(CreditNote.created_at.desc())).all()


@router.post("/invoices/{invoice_id}/credit-notes", response_model=CreditNotePublic, status_code=201)
def issue_credit_note(invoice_id: int, payload: CreditNoteCreate, user: RequireCompanyStaff, db: DbSession):
    company_id = company_id_for(user)
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.company_id == company_id).with_for_update())
    if not invoice:
        raise AppError("Invoice not found", status_code=404, code="not_found")
    if invoice.status == "cancelled":
        raise AppError("Cancelled invoices cannot receive credit notes", status_code=409, code="invoice_cancelled")
    balance = invoice_balance_due(invoice)
    if payload.amount > balance:
        raise AppError("Credit note exceeds the remaining invoice balance", status_code=409, code="credit_exceeds_balance")
    note = CreditNote(company_id=company_id, invoice_id=invoice.id,
        number=f"CN-{date.today():%y%m%d}-{secrets.token_hex(3).upper()}", amount=payload.amount,
        reason=payload.reason.strip(), created_by_user_id=user.id, status="issued")
    db.add(note)
    invoice.credited_amount += payload.amount
    refresh_invoice_status(invoice)
    db.flush()
    record_audit(db, user.id, "workspace.credit_note_issued", "credit_note", note.id,
        {"company_id": company_id, "invoice_id": invoice.id, "amount": str(payload.amount)})
    db.commit(); db.refresh(note)
    return note


@router.patch("/credit-notes/{credit_note_id}", response_model=CreditNotePublic)
def void_credit_note(credit_note_id: int, payload: CreditNoteDecision, user: RequireCompanyAdmin, db: DbSession):
    company_id = company_id_for(user)
    note = db.scalar(select(CreditNote).where(CreditNote.id == credit_note_id,
        CreditNote.company_id == company_id).with_for_update())
    if not note:
        raise AppError("Credit note not found", status_code=404, code="not_found")
    if note.status != "issued":
        raise AppError("Only issued credit notes can be voided", status_code=409, code="invalid_transition")
    invoice = db.scalar(select(Invoice).where(Invoice.id == note.invoice_id,
        Invoice.company_id == company_id).with_for_update())
    if not invoice or invoice.credited_amount < note.amount:
        raise AppError("Credit note balance cannot be reconciled", status_code=409, code="credit_reconciliation_error")
    note.status = "void"
    note.voided_by_user_id = user.id
    note.voided_at = datetime.now(timezone.utc)
    invoice.credited_amount -= note.amount
    refresh_invoice_status(invoice)
    record_audit(db, user.id, "workspace.credit_note_voided", "credit_note", note.id,
        {"company_id": company_id, "invoice_id": invoice.id})
    db.commit(); db.refresh(note)
    return note


@router.get("/refunds", response_model=list[PaymentRefundPublic])
def list_payment_refunds(user: RequireCompanyStaff, db: DbSession):
    return db.scalars(select(PaymentRefund).where(PaymentRefund.company_id == company_id_for(user))
        .order_by(PaymentRefund.refunded_at.desc(), PaymentRefund.id.desc())).all()


@router.post("/payments/{payment_id}/refunds", response_model=PaymentRefundPublic, status_code=201)
def record_payment_refund(payment_id: int, payload: PaymentRefundCreate, user: RequireCompanyStaff, db: DbSession):
    company_id = company_id_for(user)
    payment = db.scalar(select(Payment).join(Invoice).where(
        Payment.id == payment_id, Invoice.company_id == company_id).with_for_update())
    if not payment:
        raise AppError("Payment not found", status_code=404, code="not_found")
    invoice = db.scalar(select(Invoice).where(Invoice.id == payment.invoice_id,
        Invoice.company_id == company_id).with_for_update())
    if not invoice or invoice.status == "cancelled":
        raise AppError("Payment invoice cannot be refunded", status_code=409, code="invoice_cancelled")
    refundable = payment.amount - payment.refunded_amount
    if payload.amount > refundable:
        raise AppError("Refund exceeds the unrefunded payment amount", status_code=409, code="refund_exceeds_payment")
    refund = PaymentRefund(company_id=company_id, payment_id=payment.id,
        number=f"RF-{date.today():%y%m%d}-{secrets.token_hex(3).upper()}", amount=payload.amount,
        reason=payload.reason.strip(), reference=payload.reference, refunded_at=date.today(), created_by_user_id=user.id)
    db.add(refund)
    payment.refunded_amount += payload.amount
    invoice.amount_paid -= payload.amount
    refresh_invoice_status(invoice)
    db.flush()
    record_audit(db, user.id, "workspace.payment_refund_recorded", "payment_refund", refund.id,
        {"company_id": company_id, "payment_id": payment.id, "invoice_id": invoice.id, "amount": str(payload.amount)})
    db.commit(); db.refresh(refund)
    return refund


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentPublic, status_code=201)
def record_payment(invoice_id: int, payload: PaymentCreate, user: RequireCompanyStaff, db: DbSession):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.company_id == company_id_for(user)).with_for_update())
    if not invoice:
        raise AppError("Invoice not found", status_code=404, code="not_found")
    if invoice.status == "cancelled":
        raise AppError("Payments cannot be recorded against a cancelled invoice", status_code=409, code="invoice_cancelled")
    if payload.amount > invoice_balance_due(invoice):
        raise AppError("Payment exceeds the invoice balance", status_code=409, code="overpayment")
    payment = Payment(number=f"PAY-{payload.paid_at:%y%m%d}-{secrets.token_hex(3).upper()}", invoice_id=invoice.id,
        amount=payload.amount, method=payload.method, reference=payload.reference, paid_at=payload.paid_at)
    db.add(payment); invoice.amount_paid += payload.amount
    refresh_invoice_status(invoice)
    db.flush()
    record_audit(db, user.id, "workspace.payment_recorded", "payment", payment.id, {"invoice_id": invoice.id, "amount": str(payload.amount)})
    db.commit(); db.refresh(payment)
    return payment


@router.get("/payments")
def list_payments(user: RequireCompanyStaff, db: DbSession):
    rows = db.scalars(select(Payment).join(Payment.invoice).options(
        joinedload(Payment.invoice).joinedload(Invoice.customer).joinedload(Customer.user)
    ).where(Invoice.company_id == company_id_for(user)).order_by(Payment.paid_at.desc(), Payment.id.desc()).limit(200)).unique().all()
    return [{"id": row.id, "number": row.number, "invoice_id": row.invoice_id, "invoice_number": row.invoice.number,
        "customer_name": row.invoice.customer.user.name, "amount": row.amount, "refunded_amount": row.refunded_amount, "method": row.method,
        "reference": row.reference, "paid_at": row.paid_at, "created_at": row.created_at} for row in rows]


@router.get("/staff", response_model=list[UserPublic])
def list_company_staff(user: RequireCompanyAdmin, db: DbSession):
    return db.scalars(select(User).where(User.company_id == company_id_for(user), User.role == "company_staff").order_by(User.name)).all()


@router.post("/staff", response_model=UserPublic, status_code=201)
def create_company_staff(payload: CompanyStaffCreateRequest, user: RequireCompanyAdmin, db: DbSession):
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise AppError("An account with this email already exists", status_code=409, code="email_taken")
    staff = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password), role="company_staff",
        company_id=company_id_for(user), is_active=True)
    db.add(staff)
    db.flush()
    record_audit(db, user.id, "workspace.staff_created", "user", staff.id, {"company_id": staff.company_id})
    db.commit()
    db.refresh(staff)
    return staff


@router.patch("/staff/{staff_id}", response_model=UserPublic)
def update_company_staff(staff_id: int, payload: StaffUpdateRequest, user: RequireCompanyAdmin, db: DbSession):
    staff = db.scalar(select(User).where(User.id == staff_id, User.company_id == company_id_for(user), User.role == "company_staff"))
    if not staff:
        raise AppError("Staff account not found", status_code=404, code="not_found")
    values = payload.model_dump(exclude_unset=True)
    if values.get("name") is not None:
        staff.name = values["name"].strip()
    if values.get("is_active") is not None:
        staff.is_active = values["is_active"]
        if not staff.is_active:
            from datetime import datetime, timezone
            for token in staff.refresh_tokens:
                if token.revoked_at is None:
                    token.revoked_at = datetime.now(timezone.utc)
    record_audit(db, user.id, "workspace.staff_updated", "user", staff.id, {"active": staff.is_active})
    db.commit()
    db.refresh(staff)
    return staff
