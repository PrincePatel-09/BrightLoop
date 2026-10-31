from decimal import Decimal

from datetime import date

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("product_type IN ('service', 'physical', 'digital')", name="ck_products_type"),
        CheckConstraint("sales_price >= 0 AND cost_price >= 0", name="ck_products_prices_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    sku: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    product_type: Mapped[str] = mapped_column(String(24), nullable=False, default="service")
    sales_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    plans: Mapped[list["Plan"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    company: Mapped["Company"] = relationship()


class ProductVariant(TimestampMixin, Base):
    __tablename__ = "product_variants"
    __table_args__ = (CheckConstraint("price_extra >= 0", name="ck_product_variants_price_extra"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    price_extra: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    product: Mapped[Product] = relationship(back_populates="variants")


class Plan(TimestampMixin, Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("billing_interval IN ('day', 'week', 'month', 'year')", name="ck_plans_interval"),
        CheckConstraint("price >= 0", name="ck_plans_price_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(16), nullable=False, default="month")
    interval_count: Mapped[int] = mapped_column(nullable=False, default=1)
    features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    product: Mapped[Product] = relationship(back_populates="plans")


class TaxRule(TimestampMixin, Base):
    __tablename__ = "tax_rules"
    __table_args__ = (CheckConstraint("rate_percent >= 0 AND rate_percent <= 100", name="ck_tax_rules_rate"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Discount(TimestampMixin, Base):
    __tablename__ = "discounts"
    __table_args__ = (
        Index("uq_discounts_company_code", "company_id", "code", unique=True),
        CheckConstraint("discount_type IN ('fixed', 'percentage')", name="ck_discounts_type"),
        CheckConstraint("value > 0", name="ck_discounts_value"),
        CheckConstraint("minimum_amount >= 0", name="ck_discounts_minimum"),
        CheckConstraint("usage_limit IS NULL OR usage_limit > 0", name="ck_discounts_usage_limit"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    discount_type: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    minimum_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    starts_at: Mapped[date | None] = mapped_column(Date)
    ends_at: Mapped[date | None] = mapped_column(Date)
    usage_limit: Mapped[int | None] = mapped_column(Integer)
    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    company: Mapped["Company"] = relationship()
