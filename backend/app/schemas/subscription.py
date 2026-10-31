from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QuotationCreate(BaseModel):
    customer_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)
    variant_id: int | None = Field(default=None, gt=0)
    quantity: int = Field(default=1, ge=1, le=10000)
    valid_until: date
    notes: str | None = Field(default=None, max_length=5000)
    discount_code: str | None = Field(default=None, max_length=40)


class QuotationStatusUpdate(BaseModel):
    status: Literal["sent", "accepted", "cancelled"]


class QuotationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    customer_id: int
    plan_id: int
    product_name: str
    plan_name: str
    billing_interval: str
    interval_count: int
    quantity: int
    unit_price: Decimal
    status: str
    valid_until: date
    notes: str | None
    discount_code: str | None
    discount_amount: Decimal
    line_items: list[dict] = Field(default_factory=list)
    created_at: datetime
    customer_name: str
    customer_email: str


class SubscriptionStatusUpdate(BaseModel):
    status: Literal["active", "paused", "cancelled"]


class SubscriptionChangeRequestCreate(BaseModel):
    request_type: Literal["pause", "resume", "cancel", "upgrade", "downgrade"]
    requested_plan_id: int | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=2000)


class SubscriptionChangeRequestPublic(BaseModel):
    id: int
    subscription_id: int
    subscription_number: str
    customer_id: int
    customer_name: str
    request_type: str
    requested_plan_id: int | None
    requested_plan_name: str | None
    status: str
    notes: str | None
    created_at: datetime
    decided_at: datetime | None


class SubscriptionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    customer_id: int
    plan_id: int
    quotation_id: int | None
    product_name: str
    plan_name: str
    billing_interval: str
    interval_count: int
    features: list[str]
    line_items: list[dict] = Field(default_factory=list)
    quantity: int
    unit_price: Decimal
    discount_code: str | None
    discount_amount: Decimal
    status: str
    start_date: date
    next_billing_date: date
    created_at: datetime
    customer_name: str
    customer_email: str
