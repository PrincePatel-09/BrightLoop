from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaxRuleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    rate_percent: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)


class TaxRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    rate_percent: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    is_active: bool | None = None


class TaxRulePublic(TaxRuleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime


class DiscountCreate(BaseModel):
    company_id: int | None = Field(default=None, gt=0)
    code: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=120)
    discount_type: Literal["fixed", "percentage"]
    value: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    minimum_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    starts_at: date | None = None
    ends_at: date | None = None
    usage_limit: int | None = Field(default=None, gt=0)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class DiscountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    value: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    minimum_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    starts_at: date | None = None
    ends_at: date | None = None
    usage_limit: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class DiscountPublic(DiscountCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    times_used: int
    is_active: bool
    created_at: datetime
