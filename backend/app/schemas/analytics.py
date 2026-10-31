from decimal import Decimal

from pydantic import BaseModel


class OverviewMetrics(BaseModel):
    companies: int
    users: int
    customers: int
    subscriptions: int
    active_subscriptions: int
    mrr: Decimal
    arr: Decimal
    revenue_received: Decimal
    outstanding_balance: Decimal
    overdue_invoices: int
    upcoming_renewals: int
