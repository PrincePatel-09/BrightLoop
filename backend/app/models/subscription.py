from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Quotation(TimestampMixin, Base):
    __tablename__ = "quotations"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'sent', 'accepted', 'converted', 'expired', 'cancelled')", name="ck_quotations_status"),
        CheckConstraint("quantity > 0 AND unit_price >= 0", name="ck_quotations_amounts"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False)
    discount_id: Mapped[int | None] = mapped_column(ForeignKey("discounts.id", ondelete="RESTRICT"))
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(180), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(16), nullable=False)
    interval_count: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", index=True)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    discount_code: Mapped[str | None] = mapped_column(String(40))
    discount_type: Mapped[str | None] = mapped_column(String(16))
    discount_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    line_items: Mapped[list[dict] | None] = mapped_column(JSON)
    customer: Mapped["Customer"] = relationship()
    plan: Mapped["Plan"] = relationship()


class QuotationTemplate(TimestampMixin, Base):
    __tablename__ = "quotation_templates"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_quotation_templates_company_name"),
        CheckConstraint("quantity > 0", name="ck_quotation_templates_quantity_positive"),
        CheckConstraint("valid_days > 0", name="ck_quotation_templates_valid_days_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    valid_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    notes: Mapped[str | None] = mapped_column(Text)
    discount_code: Mapped[str | None] = mapped_column(String(40))
    line_items: Mapped[list[dict] | None] = mapped_column(JSON)

    plan: Mapped["Plan"] = relationship()


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'cancelled', 'expired')", name="ck_subscriptions_status"),
        CheckConstraint("quantity > 0 AND unit_price >= 0", name="ck_subscriptions_amounts"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id", ondelete="RESTRICT"), unique=True)
    discount_id: Mapped[int | None] = mapped_column(ForeignKey("discounts.id", ondelete="RESTRICT"))
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(180), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(16), nullable=False)
    interval_count: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_billing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cancelled_at: Mapped[date | None] = mapped_column(Date)
    discount_code: Mapped[str | None] = mapped_column(String(40))
    discount_type: Mapped[str | None] = mapped_column(String(16))
    discount_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    line_items: Mapped[list[dict] | None] = mapped_column(JSON)

    customer: Mapped["Customer"] = relationship()
    plan: Mapped["Plan"] = relationship()


class SubscriptionChangeRequest(TimestampMixin, Base):
    __tablename__ = "subscription_change_requests"
    __table_args__ = (
        CheckConstraint("request_type IN ('pause', 'resume', 'cancel', 'upgrade', 'downgrade')", name="ck_subscription_change_request_type"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_subscription_change_request_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id", ondelete="RESTRICT"), nullable=False, index=True)
    requested_plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"))
    request_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    decided_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped["Customer"] = relationship()
    subscription: Mapped[Subscription] = relationship()
    requested_plan: Mapped["Plan | None"] = relationship()


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("status IN ('issued', 'partially_paid', 'paid', 'overdue', 'cancelled')", name="ck_invoices_status"),
        CheckConstraint("quantity > 0 AND subtotal >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND total_amount >= 0 AND amount_paid >= 0", name="ck_invoices_amounts"),
        CheckConstraint("amount_paid <= total_amount", name="ck_invoices_paid_limit"),
        CheckConstraint("credited_amount >= 0 AND amount_paid + credited_amount <= total_amount", name="ck_invoices_paid_credit_limit"),
        UniqueConstraint("subscription_id", "period_start", name="uq_invoice_subscription_period"),
        Index("uq_invoices_company_number", "company_id", "number", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    number: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id", ondelete="RESTRICT"), index=True, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(180), nullable=False)
    company_name: Mapped[str] = mapped_column(String(180), nullable=False, default="Brightloop Software")
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    credited_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="issued", index=True)
    tax_details: Mapped[list[dict] | None] = mapped_column(JSON)
    seller_address: Mapped[str | None] = mapped_column(Text)
    seller_email: Mapped[str | None] = mapped_column(String(255))
    seller_phone: Mapped[str | None] = mapped_column(String(40))
    seller_gstin: Mapped[str | None] = mapped_column(String(20))
    seller_state_name: Mapped[str | None] = mapped_column(String(80))
    seller_state_code: Mapped[str | None] = mapped_column(String(2))
    customer_gstin: Mapped[str | None] = mapped_column(String(20))
    customer_state_code: Mapped[str | None] = mapped_column(String(2))
    payment_terms: Mapped[str | None] = mapped_column(String(120))
    line_items: Mapped[list[dict] | None] = mapped_column(JSON)

    customer: Mapped["Customer"] = relationship()
    subscription: Mapped[Subscription] = relationship()
    credit_notes: Mapped[list["CreditNote"]] = relationship(back_populates="invoice")


class InvoiceSequence(Base):
    __tablename__ = "invoice_sequences"
    __table_args__ = (
        UniqueConstraint("company_id", "fiscal_year", name="uq_invoice_sequence_company_year"),
        CheckConstraint("next_number > 0", name="ck_invoice_sequence_next_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    fiscal_year: Mapped[str] = mapped_column(String(7), nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint("refunded_amount >= 0 AND refunded_amount <= amount", name="ck_payments_refund_limit"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="RESTRICT"), index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    method: Mapped[str] = mapped_column(String(24), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120))
    paid_at: Mapped[date] = mapped_column(Date, nullable=False)

    invoice: Mapped[Invoice] = relationship()
    refunds: Mapped[list["PaymentRefund"]] = relationship(back_populates="payment")


class CreditNote(TimestampMixin, Base):
    __tablename__ = "credit_notes"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_credit_notes_amount_positive"),
        CheckConstraint("status IN ('issued', 'void')", name="ck_credit_notes_status"),
        Index("uq_credit_notes_company_number", "company_id", "number", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True)
    number: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="issued", index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    voided_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    invoice: Mapped[Invoice] = relationship(back_populates="credit_notes")
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_user_id])


class PaymentRefund(TimestampMixin, Base):
    __tablename__ = "payment_refunds"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_refunds_amount_positive"),
        Index("uq_payment_refunds_company_number", "company_id", "number", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True)
    number: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120))
    refunded_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    payment: Mapped[Payment] = relationship(back_populates="refunds")
    created_by: Mapped["User"] = relationship()


class PaymentAttempt(TimestampMixin, Base):
    __tablename__ = "payment_attempts"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_payment_attempts_amount_positive"),
        CheckConstraint("status IN ('pending', 'paid', 'failed', 'captured_unapplied')", name="ck_payment_attempts_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True)
    payment_record_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"), unique=True)
    gateway_order_id: Mapped[str] = mapped_column(String(48), nullable=False, unique=True, index=True)
    gateway_payment_id: Mapped[str | None] = mapped_column(String(48), unique=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)

    company: Mapped["Company"] = relationship()
    customer: Mapped["Customer"] = relationship()
    invoice: Mapped[Invoice] = relationship()
    payment_record: Mapped[Payment | None] = relationship()
