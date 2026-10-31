from decimal import Decimal
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class CustomerSummary(BaseModel):
    active_subscriptions: int
    outstanding_balance: Decimal
    overdue_invoices: int
    payments_recorded: int


class CustomerProfilePublic(BaseModel):
    name: str
    email: EmailStr
    company_name: str | None
    phone: str | None
    billing_address: str | None
    gstin: str | None
    state_code: str | None


class CustomerProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    company_name: str | None = Field(default=None, max_length=180)
    phone: str | None = Field(default=None, max_length=40)
    billing_address: str | None = Field(default=None, max_length=2000)
    gstin: str | None = Field(default=None, max_length=20)
    state_code: str | None = Field(default=None, max_length=12, pattern=r"^[A-Za-z0-9-]{2,12}$")


class CustomerCatalogPlan(BaseModel):
    id: int
    name: str
    price: Decimal
    billing_interval: str
    interval_count: int
    features: list[str]


class CustomerCatalogProduct(BaseModel):
    id: int
    name: str
    sku: str
    product_type: str
    description: str | None
    plans: list[CustomerCatalogPlan]


class CustomerCatalog(BaseModel):
    company_name: str
    company_slug: str
    company_email: EmailStr | None
    products: list[CustomerCatalogProduct]


class CustomerSubscriptionRequestCreate(BaseModel):
    plan_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=10000)
    notes: str | None = Field(default=None, max_length=2000)
    discount_code: str | None = Field(default=None, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")


class CustomerDirectSubscriptionCreate(CustomerSubscriptionRequestCreate):
    """Start an active subscription from the customer catalogue without quote approval."""


class CustomerChangeRequestCreate(BaseModel):
    request_type: Literal["pause", "resume", "cancel", "upgrade", "downgrade"]
    requested_plan_id: int | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=2000)


class CustomerRequestPublic(BaseModel):
    id: int
    subscription_id: int
    subscription_number: str
    request_type: str
    requested_plan_id: int | None
    requested_plan_name: str | None
    status: str
    notes: str | None
    created_at: datetime
    decided_at: datetime | None


class PaymentOrderPublic(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str
    company_name: str
    customer_name: str
    customer_email: EmailStr


class PaymentVerificationRequest(BaseModel):
    order_id: str = Field(min_length=8, max_length=48)
    payment_id: str = Field(min_length=8, max_length=48)
    signature: str = Field(min_length=64, max_length=64, pattern=r"^[A-Fa-f0-9]{64}$")
