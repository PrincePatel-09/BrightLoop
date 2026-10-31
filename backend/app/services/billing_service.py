import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dates import add_billing_interval
from app.models.base import AppSetting
from app.models.company import Company
from app.models.subscription import Invoice, InvoiceSequence, Subscription
from app.core.exceptions import AppError
from app.services.audit_service import record_audit
from app.services.email_service import send_invoice_notice

logger = logging.getLogger(__name__)


def process_due_subscriptions(db: Session, as_of: date, actor_user_id: int | None = None, company_id: int | None = None) -> tuple[int, int]:
    configured = {row.key: row.value for row in db.scalars(select(AppSetting)).all()}
    invoice_prefix = configured.get("invoice_prefix", "INV")
    company_name = configured.get("company_name", "Brightloop Software")
    currency_code = configured.get("currency_code", "INR")
    payment_terms_days = int(configured.get("payment_terms_days", "14"))
    due_query = select(Subscription).where(Subscription.status == "active", Subscription.next_billing_date <= as_of)
    if company_id is not None:
        due_query = due_query.where(Subscription.company_id == company_id)
    subscriptions = db.scalars(
        due_query
        .order_by(Subscription.next_billing_date, Subscription.id)
        .with_for_update(skip_locked=True)
    ).all()
    created = 0
    periods = 0
    notices: list[tuple[str, str, str]] = []
    for sub in subscriptions:
        company_values = {
            row.key.split(":", 2)[2]: row.value
            for row in db.scalars(select(AppSetting).where(AppSetting.key.like(f"company:{sub.company_id}:%"))).all()
        }
        company_prefix = company_values.get("invoice_prefix", invoice_prefix)
        company_currency = company_values.get("currency_code", currency_code)
        company_payment_terms = int(company_values.get("payment_terms_days", str(payment_terms_days)))
        company = db.get(Company, sub.company_id)
        while sub.status == "active" and sub.next_billing_date <= as_of:
            period_start = sub.next_billing_date
            period_end = add_billing_interval(period_start, sub.billing_interval, sub.interval_count)
            existing_id = db.scalar(select(Invoice.id).where(Invoice.subscription_id == sub.id, Invoice.period_start == period_start))
            if not existing_id:
                line_items = sub.line_items or [{"plan_id": sub.plan_id,
                    "description": f"{sub.product_name} - {sub.plan_name}", "product_name": sub.product_name,
                    "plan_name": sub.plan_name, "quantity": sub.quantity, "unit_price": str(sub.unit_price)}]
                subtotal = sum((Decimal(str(line["unit_price"])) * int(line["quantity"]) for line in line_items), Decimal("0.00")).quantize(Decimal("0.01"))
                if sub.discount_type == "percentage" and sub.discount_value is not None:
                    discount_amount = (subtotal * sub.discount_value / Decimal("100")).quantize(Decimal("0.01"))
                elif sub.discount_type == "fixed" and sub.discount_value is not None:
                    discount_amount = sub.discount_value
                else:
                    discount_amount = Decimal("0.00")
                discount_amount = min(subtotal, discount_amount)
                taxable = subtotal - discount_amount
                gst_rate = Decimal(company_values.get("gst_rate_percent", "0"))
                seller_state = company_values.get("state_code", "").strip().upper()
                tax_details: list[dict[str, str]] = []
                tax_amount = Decimal("0.00")
                if gst_rate > 0:
                    if not company or not company.tax_id or not seller_state or not sub.customer.state_code:
                        raise AppError("Company GSTIN, seller state, and customer state are required before GST billing", status_code=422, code="gst_jurisdiction_incomplete")
                    if sub.customer.state_code.strip().upper() == seller_state:
                        half_rate = gst_rate / Decimal("2")
                        for name in ("CGST", "SGST"):
                            applied = (taxable * half_rate / Decimal("100")).quantize(Decimal("0.01"))
                            tax_amount += applied
                            tax_details.append({"name": name, "rate_percent": str(half_rate), "amount": str(applied)})
                    else:
                        applied = (taxable * gst_rate / Decimal("100")).quantize(Decimal("0.01"))
                        tax_amount = applied
                        tax_details.append({"name": "IGST", "rate_percent": str(gst_rate), "amount": str(applied)})
                total = taxable + tax_amount
                fiscal_start = period_start.year if period_start.month >= 4 else period_start.year - 1
                fiscal_year = f"{fiscal_start}-{(fiscal_start + 1) % 100:02d}"
                # Lock the company row before reading or creating its sequence. This serializes
                # first-time and concurrent sequence allocations for the same tenant/year.
                db.scalar(select(Company).where(Company.id == sub.company_id).with_for_update())
                sequence = db.scalar(select(InvoiceSequence).where(
                    InvoiceSequence.company_id == sub.company_id,
                    InvoiceSequence.fiscal_year == fiscal_year).with_for_update())
                if not sequence:
                    sequence = InvoiceSequence(company_id=sub.company_id, fiscal_year=fiscal_year, next_number=1)
                    db.add(sequence)
                    db.flush()
                invoice_number = sequence.next_number
                sequence.next_number += 1
                invoice = Invoice(
                    company_id=sub.company_id,
                    number=f"{company_prefix}/{fiscal_year}/{invoice_number:04d}",
                    customer_id=sub.customer_id,
                    subscription_id=sub.id,
                    period_start=period_start,
                    period_end=period_end,
                    due_date=period_start + timedelta(days=company_payment_terms),
                    product_name=sub.product_name,
                    plan_name=sub.plan_name,
                    company_name=company.name if company else company_name,
                    currency_code=company_currency,
                    quantity=sub.quantity,
                    unit_price=sub.unit_price,
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    tax_details=tax_details,
                    seller_address=company.address if company else None,
                    seller_email=company.email if company else None,
                    seller_phone=company.phone if company else None,
                    seller_gstin=company.tax_id if company else None,
                    seller_state_name=company_values.get("state_name"),
                    seller_state_code=seller_state or None,
                    customer_gstin=sub.customer.gstin,
                    customer_state_code=sub.customer.state_code,
                    payment_terms=f"Net {company_payment_terms} days",
                    line_items=line_items,
                    discount_amount=discount_amount,
                    total_amount=total,
                    amount_paid=Decimal("0.00"),
                    status="issued",
                )
                db.add(invoice)
                db.flush()
                record_audit(db, actor_user_id, "billing.invoice_created", "invoice", invoice.id, {"subscription_id": sub.id, "period_start": period_start.isoformat(), "total_amount": str(total)})
                notices.append((sub.customer.user.email, invoice.number, f"{settings.FRONTEND_URL}/my/invoices"))
                created += 1
            sub.next_billing_date = period_end
            periods += 1
    db.commit()
    for email, number, url in notices:
        send_invoice_notice(email, number, url)
    logger.info("Billing processed %s periods and created %s invoices", periods, created)
    return created, periods
