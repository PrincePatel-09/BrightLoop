from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from app.core.deps import DbSession, RequireStaff
from app.core.exceptions import AppError
from app.models.customer import Customer
from app.models.user import User
from app.models.subscription import Invoice, Payment, Subscription
from app.schemas.customer import CustomerPublic, CustomerUpdate
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("/{customer_id}/history")
def customer_history(customer_id: int, _staff: RequireStaff, db: DbSession):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise AppError("Customer not found", status_code=404, code="not_found")
    subscriptions = db.scalars(select(Subscription).where(Subscription.customer_id == customer_id).order_by(Subscription.created_at.desc())).all()
    invoices = db.scalars(select(Invoice).where(Invoice.customer_id == customer_id).order_by(Invoice.created_at.desc())).all()
    payments = db.scalars(select(Payment).join(Payment.invoice).where(Invoice.customer_id == customer_id).order_by(Payment.paid_at.desc())).all()
    return {
        "subscriptions": [{"number": row.number, "plan": row.plan_name, "status": row.status, "next_billing_date": row.next_billing_date.isoformat(), "unit_price": str(row.unit_price), "quantity": row.quantity} for row in subscriptions],
        "invoices": [{"number": row.number, "status": row.status, "issued": row.period_start.isoformat(), "total": str(row.total_amount), "credited": str(row.credited_amount), "balance": str(row.total_amount - row.amount_paid - row.credited_amount)} for row in invoices],
        "payments": [{"number": row.number, "amount": str(row.amount), "refunded_amount": str(row.refunded_amount), "method": row.method, "paid_at": row.paid_at.isoformat(), "reference": row.reference} for row in payments],
    }


def customer_public(customer: Customer) -> CustomerPublic:
    return CustomerPublic(
        id=customer.id,
        name=customer.user.name,
        email=customer.user.email,
        is_active=customer.user.is_active,
        company_name=customer.company_name,
        phone=customer.phone,
        billing_address=customer.billing_address,
        created_at=customer.created_at,
    )


@router.get("", response_model=list[CustomerPublic])
def list_customers(
    _staff: RequireStaff,
    db: DbSession,
    search: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(Customer).join(Customer.user).order_by(User.name, Customer.id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(or_(User.name.ilike(term), User.email.ilike(term), Customer.company_name.ilike(term)))
    rows = db.scalars(query.offset(offset).limit(limit)).all()
    return [customer_public(customer) for customer in rows]


@router.patch("/{customer_id}", response_model=CustomerPublic)
def update_customer(customer_id: int, payload: CustomerUpdate, staff: RequireStaff, db: DbSession):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise AppError("Customer not found", status_code=404, code="not_found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, value.strip() if isinstance(value, str) else value)
    record_audit(db, staff.id, "customer.contact_updated", "customer", customer.id)
    db.commit()
    db.refresh(customer)
    return customer_public(customer)
