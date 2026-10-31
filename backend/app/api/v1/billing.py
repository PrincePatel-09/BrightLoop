import secrets
from datetime import date
from io import BytesIO

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.deps import DbSession, RequireStaff
from app.core.exceptions import AppError
from app.models.customer import Customer
from app.models.subscription import Invoice, Payment
from app.schemas.billing import BillingRunRequest, BillingRunResult, InvoicePublic, PaymentCreate, PaymentPublic, PaymentRecord
from app.services.invoice_pdf import render_invoice
from app.services.invoice_service import invoice_balance_due, refresh_invoice_status
from app.services.audit_service import record_audit
from app.services.billing_service import process_due_subscriptions

router = APIRouter()


def invoice_public(row: Invoice) -> InvoicePublic:
    return InvoicePublic(
        id=row.id,
        number=row.number,
        customer_id=row.customer_id,
        customer_name=row.customer.user.name,
        customer_email=row.customer.user.email,
        subscription_id=row.subscription_id,
        period_start=row.period_start,
        period_end=row.period_end,
        due_date=row.due_date,
        product_name=row.product_name,
        plan_name=row.plan_name,
        company_name=row.company_name,
        currency_code=row.currency_code,
        quantity=row.quantity,
        unit_price=row.unit_price,
        subtotal=row.subtotal,
        line_items=row.line_items or [],
        tax_amount=row.tax_amount,
        tax_details=row.tax_details,
        seller_address=row.seller_address,
        seller_email=row.seller_email,
        seller_phone=row.seller_phone,
        seller_gstin=row.seller_gstin,
        seller_state_name=row.seller_state_name,
        seller_state_code=row.seller_state_code,
        customer_gstin=row.customer_gstin,
        customer_state_code=row.customer_state_code,
        payment_terms=row.payment_terms,
        discount_amount=row.discount_amount,
        total_amount=row.total_amount,
        amount_paid=row.amount_paid,
        credited_amount=row.credited_amount,
        balance_due=invoice_balance_due(row),
        status=row.status,
        created_at=row.created_at,
    )


@router.post("/run", response_model=BillingRunResult)
def run_billing(payload: BillingRunRequest, _staff: RequireStaff, db: DbSession):
    created, periods = process_due_subscriptions(db, payload.as_of, _staff.id)
    return BillingRunResult(invoices_created=created, periods_processed=periods, as_of=payload.as_of)


@router.get("/invoices", response_model=list[InvoicePublic])
def list_invoices(_staff: RequireStaff, db: DbSession, status: str | None = Query(default=None), customer_id: int | None = None):
    query = select(Invoice).options(joinedload(Invoice.customer).joinedload(Customer.user)).order_by(Invoice.created_at.desc())
    if status:
        query = query.where(Invoice.status == status)
    if customer_id:
        query = query.where(Invoice.customer_id == customer_id)
    rows = db.scalars(query).unique().all()
    today = date.today()
    updated = False
    for invoice in rows:
        if invoice.status in {"issued", "partially_paid"} and invoice.due_date < today and invoice_balance_due(invoice) > 0:
            invoice.status = "overdue"
            updated = True
    if updated:
        db.commit()
    return [invoice_public(row) for row in rows]


@router.get("/invoices/{invoice_id}/pdf")
def download_invoice(invoice_id: int, _staff: RequireStaff, db: DbSession):
    invoice = db.scalar(select(Invoice).options(joinedload(Invoice.customer).joinedload(Customer.user)).where(Invoice.id == invoice_id))
    if not invoice:
        raise AppError("Invoice not found", status_code=404, code="not_found")
    return StreamingResponse(BytesIO(render_invoice(invoice)), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{invoice.number}.pdf"'})


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentPublic, status_code=201)
def record_payment(invoice_id: int, payload: PaymentCreate, _staff: RequireStaff, db: DbSession):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    if not invoice:
        raise AppError("Invoice not found", status_code=404, code="not_found")
    if invoice.status == "cancelled":
        raise AppError("Payments cannot be recorded against a cancelled invoice", status_code=409, code="invoice_cancelled")
    balance = invoice_balance_due(invoice)
    if payload.amount > balance:
        raise AppError("Payment exceeds the invoice balance", status_code=409, code="overpayment")
    payment = Payment(
        number=f"PAY-{payload.paid_at:%y%m%d}-{secrets.token_hex(3).upper()}",
        invoice_id=invoice.id,
        amount=payload.amount,
        method=payload.method,
        reference=payload.reference,
        paid_at=payload.paid_at,
    )
    db.add(payment)
    invoice.amount_paid += payload.amount
    refresh_invoice_status(invoice)
    db.flush()
    record_audit(db, _staff.id, "payment.recorded", "payment", payment.id, {"invoice_id": invoice.id, "amount": str(payload.amount), "method": payload.method})
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/payments", response_model=list[PaymentRecord])
def list_payments(_staff: RequireStaff, db: DbSession, limit: int = Query(default=100, ge=1, le=200)):
    rows = db.scalars(
        select(Payment)
        .options(joinedload(Payment.invoice).joinedload(Invoice.customer).joinedload(Customer.user))
        .order_by(Payment.paid_at.desc(), Payment.id.desc())
        .limit(limit)
    ).unique().all()
    return [
        PaymentRecord(
            id=row.id,
            number=row.number,
            invoice_id=row.invoice_id,
            amount=row.amount,
            refunded_amount=row.refunded_amount,
            method=row.method,
            reference=row.reference,
            paid_at=row.paid_at,
            created_at=row.created_at,
            invoice_number=row.invoice.number,
            customer_name=row.invoice.customer.user.name,
        )
        for row in rows
    ]
