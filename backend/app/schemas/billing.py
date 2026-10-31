from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BillingRunRequest(BaseModel):
    as_of: date = Field(default_factory=date.today)


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: Literal["cash", "bank_transfer", "card", "other"]
    reference: str | None = Field(default=None, max_length=120)
    paid_at: date = Field(default_factory=date.today)


class CreditNoteCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=3, max_length=2000)


class CreditNoteDecision(BaseModel):
    status: Literal["void"]


class CreditNotePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    invoice_id: int
    amount: Decimal
    reason: str
    status: str
    created_by_user_id: int
    voided_by_user_id: int | None
    voided_at: datetime | None
    created_at: datetime


class PaymentRefundCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=3, max_length=2000)
    reference: str | None = Field(default=None, max_length=120)


class PaymentRefundPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    payment_id: int
    amount: Decimal
    reason: str
    reference: str | None
    refunded_at: date
    created_by_user_id: int
    created_at: datetime


class PaymentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    invoice_id: int
    amount: Decimal
    refunded_amount: Decimal
    method: str
    reference: str | None
    paid_at: date
    created_at: datetime


class PaymentRecord(PaymentPublic):
    invoice_number: str
    customer_name: str


class InvoicePublic(BaseModel):
    id: int
    number: str
    customer_id: int
    customer_name: str
    customer_email: str
    subscription_id: int
    period_start: date
    period_end: date
    due_date: date
    product_name: str
    plan_name: str
    company_name: str
    currency_code: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    tax_amount: Decimal
    tax_details: list[dict[str, Any]] | None
    seller_address: str | None = None
    seller_email: str | None = None
    seller_phone: str | None = None
    seller_gstin: str | None = None
    seller_state_name: str | None = None
    seller_state_code: str | None = None
    customer_gstin: str | None = None
    customer_state_code: str | None = None
    payment_terms: str | None = None
    discount_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    credited_amount: Decimal
    balance_due: Decimal
    status: str
    created_at: datetime


class BillingRunResult(BaseModel):
    invoices_created: int
    periods_processed: int
    as_of: date
