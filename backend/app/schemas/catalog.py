from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    billing_interval: Literal["day", "week", "month", "year"] = "month"
    interval_count: int = Field(default=1, ge=1, le=120)
    features: list[str] = Field(default_factory=list, max_length=30)


class PlanPublic(PlanCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    is_active: bool
    created_at: datetime


class ProductVariantCreate(BaseModel):
    attribute: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    price_extra: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class ProductVariantUpdate(BaseModel):
    attribute: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    price_extra: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    is_active: bool | None = None


class ProductVariantPublic(ProductVariantCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    is_active: bool
    created_at: datetime


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    sku: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    product_type: Literal["service", "physical", "digital"] = "service"
    sales_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    cost_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=5000)
    company_id: int | None = Field(default=None, gt=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    sales_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    cost_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None


class ProductPublic(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime
    plans: list[PlanPublic] = []
    variants: list[ProductVariantPublic] = []


class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    billing_interval: Literal["day", "week", "month", "year"] | None = None
    interval_count: int | None = Field(default=None, ge=1, le=120)
    features: list[str] | None = Field(default=None, max_length=30)
    is_active: bool | None = None
