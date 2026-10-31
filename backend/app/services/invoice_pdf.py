from io import BytesIO
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from app.models.subscription import Invoice
from app.services.invoice_service import invoice_balance_due


def payment_qr_payload(invoice: Invoice) -> str:
    balance = invoice_balance_due(invoice)
    return "\n".join(
        [
            "Brightloop Payment",
            f"Invoice: {invoice.number}",
            f"Customer: {invoice.customer.user.email}",
            f"Amount due: {invoice.currency_code} {balance:.2f}",
            "Payment status: pending",
        ]
    )


def payment_qr(invoice: Invoice) -> Drawing:
    code = QrCodeWidget(payment_qr_payload(invoice))
    size = 1.05 * inch
    code.barWidth = size
    code.barHeight = size
    drawing = Drawing(size, size)
    drawing.add(code)
    return drawing


def render_invoice(invoice: Invoice) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Invoice {invoice.number}",
        author=invoice.company_name,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Brand", parent=styles["Title"], textColor=colors.HexColor("#714B67"), alignment=TA_RIGHT, fontSize=23, leading=28))
    styles.add(ParagraphStyle(name="MutedSmall", parent=styles["BodyText"], textColor=colors.HexColor("#64748B"), fontSize=9, leading=13))
    styles.add(ParagraphStyle(name="RightBody", parent=styles["BodyText"], alignment=TA_RIGHT))

    story = []
    heading = Table(
        [[Paragraph(escape(invoice.company_name), styles["Brand"]), Paragraph("INVOICE", styles["Heading1"])],
         [Paragraph("<br/>".join(escape(line) for line in (getattr(invoice, "seller_address", None) or "", getattr(invoice, "seller_email", None) or "", getattr(invoice, "seller_phone", None) or "") if line) or "Business invoice", styles["MutedSmall"]), Paragraph(f"<b>{invoice.number}</b><br/>Issued: {invoice.created_at:%d %b %Y}<br/>Due: {invoice.due_date:%d %b %Y}<br/>Terms: {escape(getattr(invoice, 'payment_terms', None) or 'Due on receipt')}", styles["RightBody"]) ]],
        colWidths=[3.4 * inch, 3.4 * inch],
    )
    heading.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.extend([heading, Spacer(1, 0.35 * inch)])

    customer = invoice.customer
    contact = [f"<b>{customer.user.name}</b>"]
    if customer.company_name:
        contact.append(customer.company_name)
    if getattr(invoice, "customer_gstin", None):
        contact.append(f"GSTIN: {invoice.customer_gstin}")
    if getattr(invoice, "customer_state_code", None):
        contact.append(f"State code: {invoice.customer_state_code}")
    contact.extend([customer.user.email, customer.phone or "", customer.billing_address or ""])
    contact = [Paragraph(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), styles["BodyText"]) for line in contact if line]
    bill_to = Table([[Paragraph("BILL TO", styles["Heading3"])], *[[line] for line in contact]], colWidths=[3.5 * inch])
    bill_to.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F8FC")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story.extend([bill_to, Spacer(1, 0.35 * inch)])
    seller_tax = []
    if getattr(invoice, "seller_gstin", None):
        seller_tax.append(f"GSTIN: {invoice.seller_gstin}")
    if getattr(invoice, "seller_state_name", None) or getattr(invoice, "seller_state_code", None):
        seller_tax.append(f"State: {invoice.seller_state_name or ''} ({invoice.seller_state_code or ''})")
    if seller_tax:
        story.extend([Paragraph("<b>SELLER TAX DETAILS</b> &nbsp; " + escape("  ·  ".join(seller_tax)), styles["MutedSmall"]), Spacer(1, 0.2 * inch)])

    invoice_items = getattr(invoice, "line_items", None) or [{"description": f"{invoice.product_name} - {invoice.plan_name}",
        "quantity": invoice.quantity, "unit_price": str(invoice.unit_price)}]
    rows = [["Description", "Period", "Qty", "Unit price", "Amount"]]
    for item in invoice_items:
        item_quantity = int(item["quantity"])
        item_price = Decimal(str(item["unit_price"]))
        rows.append([escape(str(item["description"])), f"{invoice.period_start:%d %b %Y} - {invoice.period_end:%d %b %Y}",
            str(item_quantity), f"{invoice.currency_code} {item_price:.2f}",
            f"{invoice.currency_code} {item_quantity * item_price:.2f}"])
    table = Table(rows, colWidths=[2.05 * inch, 1.75 * inch, 0.45 * inch, 1.1 * inch, 1.1 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([table, Spacer(1, 0.2 * inch)])
    tax_rows = [[f"{escape(tax['name'])} ({tax['rate_percent']}%)", f"{invoice.currency_code} {tax['amount']}"] for tax in (invoice.tax_details or [])]
    if not tax_rows:
        tax_rows = [["Tax", f"{invoice.tax_amount:.2f}"]]
    totals = [
        ["Subtotal", f"{invoice.currency_code} {invoice.subtotal:.2f}"],
        *tax_rows,
        ["Discount", f"-{invoice.currency_code} {invoice.discount_amount:.2f}"],
        [Paragraph("<b>Total</b>", styles["BodyText"]), Paragraph(f"<b>{invoice.currency_code} {invoice.total_amount:.2f}</b>", styles["RightBody"])],
        ["Paid", f"-{invoice.currency_code} {invoice.amount_paid:.2f}"],
        ["Credit notes", f"-{invoice.currency_code} {getattr(invoice, 'credited_amount', Decimal('0.00')):.2f}"],
        [Paragraph("<b>Balance due</b>", styles["BodyText"]), Paragraph(f"<b>{invoice.currency_code} {invoice_balance_due(invoice):.2f}</b>", styles["RightBody"])],
    ]
    summary = Table(totals, colWidths=[1.45 * inch, 1.35 * inch], hAlign="RIGHT")
    total_row = len(tax_rows) + 3
    balance_row = len(tax_rows) + 5
    summary.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"), ("LINEABOVE", (0, total_row), (-1, total_row), 0.7, colors.HexColor("#111827")), ("LINEABOVE", (0, balance_row), (-1, balance_row), 0.7, colors.HexColor("#111827")), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    payment_note = Paragraph(
        f"<b>Scan to view payment details</b><br/>{invoice.currency_code} {invoice_balance_due(invoice):.2f} due<br/><font color='#64748B'>The QR identifies this Brightloop invoice and amount.</font>",
        styles["MutedSmall"],
    )
    payment_box = Table([[payment_qr(invoice), payment_note]], colWidths=[1.25 * inch, 2.6 * inch], hAlign="RIGHT")
    payment_box.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.extend([summary, Spacer(1, 0.25 * inch), payment_box, Spacer(1, 0.25 * inch), Paragraph("Payment terms: " + escape(getattr(invoice, "payment_terms", None) or "Due on receipt"), styles["MutedSmall"]), Spacer(1, 0.12 * inch), Paragraph("Authorized signature: ____________________________________", styles["MutedSmall"]), Spacer(1, 0.12 * inch), Paragraph("Thank you for your business.", styles["MutedSmall"])])
    document.build(story)
    return buffer.getvalue()
