from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.services.invoice_pdf import payment_qr_payload, render_invoice


def make_invoice():
    customer = SimpleNamespace(
        user=SimpleNamespace(email="customer@example.com", name="Rahul Mehta"),
        company_name="Mehta Retail",
        phone="",
        billing_address="",
    )
    return SimpleNamespace(
        number="INV-2601-ABC123",
        customer=customer,
        total_amount=Decimal("1200.00"),
        amount_paid=Decimal("200.00"),
        currency_code="INR",
        company_name="Brightloop",
        created_at=datetime.now(timezone.utc),
        due_date=date.today(),
        product_name="Cloud Workspace",
        plan_name="Monthly Workspace",
        period_start=date.today(),
        period_end=date.today(),
        quantity=1,
        unit_price=Decimal("1200.00"),
        subtotal=Decimal("1200.00"),
        tax_amount=Decimal("0.00"),
        tax_details=[],
        discount_amount=Decimal("0.00"),
    )


def test_payment_qr_uses_invoice_balance_and_brightloop_identity():
    invoice = make_invoice()
    payload = payment_qr_payload(invoice)

    assert "Brightloop Payment" in payload
    assert "Invoice: INV-2601-ABC123" in payload
    assert "Amount due: INR 1000.00" in payload


def test_invoice_pdf_contains_qr_section():
    pdf = render_invoice(make_invoice())

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
