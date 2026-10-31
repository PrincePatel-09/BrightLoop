from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.deps import DbSession, RequireStaff
from app.models.customer import Customer
from app.models.company import Company
from app.models.user import User
from app.models.subscription import Invoice, Payment, PaymentRefund, Quotation, Subscription
from app.schemas.analytics import OverviewMetrics

router = APIRouter()


@router.get("/overview", response_model=OverviewMetrics)
def overview(_staff: RequireStaff, db: DbSession):
    today = date.today()
    active_subscriptions = db.scalars(select(Subscription).where(Subscription.status == "active")).all()
    monthly_revenue = Decimal("0.00")
    for subscription in active_subscriptions:
        interval = subscription.billing_interval
        count = max(subscription.interval_count, 1)
        recurring_amount = (sum((Decimal(str(line["unit_price"])) * int(line["quantity"])
            for line in subscription.line_items), Decimal("0.00")) if subscription.line_items
            else subscription.unit_price * subscription.quantity)
        if interval == "month":
            monthly_revenue += recurring_amount / count
        elif interval == "year":
            monthly_revenue += recurring_amount / (12 * count)
        elif interval == "week":
            monthly_revenue += recurring_amount * Decimal(52) / (12 * count)
        elif interval == "day":
            monthly_revenue += recurring_amount * Decimal(365) / (12 * count)
    monthly_revenue = monthly_revenue.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return OverviewMetrics(
        companies=db.scalar(select(func.count()).select_from(Company)) or 0,
        users=db.scalar(select(func.count()).select_from(User)) or 0,
        customers=db.scalar(select(func.count()).select_from(Customer)) or 0,
        subscriptions=db.scalar(select(func.count()).select_from(Subscription)) or 0,
        active_subscriptions=len(active_subscriptions),
        mrr=monthly_revenue,
        arr=(monthly_revenue * 12).quantize(Decimal("0.01")),
        revenue_received=db.scalar(select(func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0))) or 0,
        outstanding_balance=db.scalar(select(func.coalesce(func.sum(Invoice.total_amount - Invoice.amount_paid - Invoice.credited_amount), 0)).where(Invoice.status != "cancelled")) or 0,
        overdue_invoices=db.scalar(select(func.count()).select_from(Invoice).where(Invoice.status.in_(["overdue", "issued", "partially_paid"]), Invoice.due_date < today, Invoice.amount_paid + Invoice.credited_amount < Invoice.total_amount)) or 0,
        upcoming_renewals=db.scalar(select(func.count()).select_from(Subscription).where(Subscription.status == "active", Subscription.next_billing_date.between(today, today + timedelta(days=30)))) or 0,
    )


@router.get("/revenue")
def revenue_trend(_staff: RequireStaff, db: DbSession, months: int = 6):
    months = min(max(months, 1), 24)
    today = date.today()
    first_month = today.replace(day=1)
    for _ in range(months - 1):
        first_month = (first_month - timedelta(days=1)).replace(day=1)
    rows = db.scalars(select(Payment).where(Payment.paid_at >= first_month).order_by(Payment.paid_at)).all()
    totals: dict[str, Decimal] = {}
    cursor = first_month
    for _ in range(months):
        totals[cursor.strftime("%Y-%m")] = Decimal("0.00")
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    for payment in rows:
        key = payment.paid_at.strftime("%Y-%m")
        if key in totals:
            totals[key] += payment.amount - payment.refunded_amount
    return [{"month": key, "revenue": value} for key, value in totals.items()]


@router.get("/subscription-statuses")
def subscription_statuses(_staff: RequireStaff, db: DbSession):
    rows = db.execute(select(Subscription.status, func.count()).group_by(Subscription.status)).all()
    return [{"status": status, "count": count} for status, count in rows]


@router.get("/report")
def report(_staff: RequireStaff, db: DbSession, start_date: date, end_date: date):
    if end_date < start_date:
        from app.core.exceptions import AppError
        raise AppError("End date must be on or after start date", status_code=422, code="invalid_date_range")
    start_at = datetime.combine(start_date, time.min)
    end_at = datetime.combine(end_date + timedelta(days=1), time.min)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "revenue_received": db.scalar(select(func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)).where(Payment.paid_at.between(start_date, end_date))) or 0,
        "payments_count": db.scalar(select(func.count()).select_from(Payment).where(Payment.paid_at.between(start_date, end_date))) or 0,
        "subscriptions_created": db.scalar(select(func.count()).select_from(Subscription).where(Subscription.created_at >= start_at, Subscription.created_at < end_at)) or 0,
        "invoices_issued": db.scalar(select(func.count()).select_from(Invoice).where(Invoice.created_at >= start_at, Invoice.created_at < end_at)) or 0,
        "outstanding_balance": db.scalar(select(func.coalesce(func.sum(Invoice.total_amount - Invoice.amount_paid - Invoice.credited_amount), 0)).where(Invoice.status != "cancelled", Invoice.created_at < end_at)) or 0,
    }


@router.get("/activity")
def recent_activity(_staff: RequireStaff, db: DbSession, limit: int = 8):
    limit = min(max(limit, 1), 20)
    items = []
    for row in db.scalars(select(Payment).order_by(Payment.created_at.desc()).limit(limit)).all():
        items.append({"type": "payment", "label": f"Payment {row.number} recorded", "date": row.created_at, "amount": str(row.amount - row.refunded_amount)})
    for row in db.scalars(select(PaymentRefund).order_by(PaymentRefund.created_at.desc()).limit(limit)).all():
        items.append({"type": "refund", "label": f"Refund {row.number} recorded", "date": row.created_at, "amount": str(row.amount)})
    for row in db.scalars(select(Invoice).order_by(Invoice.created_at.desc()).limit(limit)).all():
        items.append({"type": "invoice", "label": f"Invoice {row.number} issued", "date": row.created_at, "amount": str(row.total_amount)})
    for row in db.scalars(select(Quotation).order_by(Quotation.created_at.desc()).limit(limit)).all():
        amount = (sum((Decimal(str(line["unit_price"])) * int(line["quantity"]) for line in row.line_items), Decimal("0.00"))
            if row.line_items else row.unit_price * row.quantity)
        items.append({"type": "quotation", "label": f"Quotation {row.number} {row.status}", "date": row.created_at, "amount": str(amount)})
    return sorted(items, key=lambda item: item["date"], reverse=True)[:limit]
