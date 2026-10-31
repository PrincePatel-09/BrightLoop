from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Literal

from app.schemas.auth import validate_password


class WorkspaceOverview(BaseModel):
    customers: int
    products: int
    active_subscriptions: int
    revenue_received: Decimal
    outstanding_balance: Decimal
    mrr: Decimal
    arr: Decimal


class CompanyStaffCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        return validate_password(value)


class QuotationLineItemInput(BaseModel):
    plan_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=10000)


class WorkspaceQuotationCreate(BaseModel):
    customer_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=10000)
    valid_until: date
    notes: str | None = Field(default=None, max_length=5000)
    discount_code: str | None = Field(default=None, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    line_items: list[QuotationLineItemInput] = Field(default_factory=list, max_length=49)


class WorkspaceQuotationUpdate(BaseModel):
    status: Literal["sent", "accepted", "cancelled"] | None = None
    quantity: int | None = Field(default=None, ge=1, le=10000)
    valid_until: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    discount_code: str | None = Field(default=None, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    line_items: list[QuotationLineItemInput] | None = Field(default=None, max_length=49)


class QuotationTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    plan_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=10000)
    valid_days: int = Field(default=14, ge=1, le=365)
    notes: str | None = Field(default=None, max_length=5000)
    discount_code: str | None = Field(default=None, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    line_items: list[QuotationLineItemInput] = Field(default_factory=list, max_length=49)


class QuotationTemplatePublic(BaseModel):
    id: int
    name: str
    plan_id: int
    plan_name: str
    quantity: int
    valid_days: int
    notes: str | None
    discount_code: str | None
    line_items: list[dict] = Field(default_factory=list)
    created_at: datetime


class ChangeRequestDecision(BaseModel):
    status: Literal["approved", "rejected"]


class WorkspaceCompanySettings(BaseModel):
    name: str
    legal_name: str | None
    email: EmailStr | None
    phone: str | None
    address: str | None
    tax_id: str | None
    currency_code: str
    invoice_prefix: str
    payment_terms_days: int
    state_name: str | None
    state_code: str | None
    gst_rate_percent: Decimal


class WorkspaceCompanySettingsUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    legal_name: str | None = Field(default=None, max_length=180)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=2000)
    tax_id: str | None = Field(default=None, max_length=80)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    invoice_prefix: str | None = Field(default=None, min_length=2, max_length=12, pattern=r"^[A-Za-z0-9_-]+$")
    payment_terms_days: int | None = Field(default=None, ge=1, le=90)
    state_name: str | None = Field(default=None, max_length=80)
    state_code: str | None = Field(default=None, max_length=12, pattern=r"^[A-Za-z0-9-]{2,12}$")
    gst_rate_percent: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)

    @field_validator("currency_code", "invoice_prefix", "state_code")
    @classmethod
    def uppercase_codes(cls, value: str | None) -> str | None:
        return value.upper() if value else value
