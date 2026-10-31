from datetime import date
from decimal import Decimal

from app.models.subscription import Invoice


def invoice_balance_due(invoice: Invoice) -> Decimal:
    credited = getattr(invoice, "credited_amount", Decimal("0.00")) or Decimal("0.00")
    return max(Decimal("0.00"), invoice.total_amount - invoice.amount_paid - credited)


def refresh_invoice_status(invoice: Invoice, as_of: date | None = None) -> None:
    due = invoice_balance_due(invoice)
    if due == 0:
        invoice.status = "paid"
    elif invoice.due_date < (as_of or date.today()):
        invoice.status = "overdue"
    elif invoice.amount_paid > 0 or (getattr(invoice, "credited_amount", Decimal("0.00")) or Decimal("0.00")) > 0:
        invoice.status = "partially_paid"
    else:
        invoice.status = "issued"
