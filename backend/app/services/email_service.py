import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send(to_email: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        logger.info("Email queued for %s: %s", to_email, subject)
        logger.debug("Email body: %s", body)
        return
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)


def send_password_reset(to_email: str, reset_url: str) -> None:
    try:
        _send(to_email, "Reset your Brightloop password", f"Brightloop Software received a password reset request. Use this one-time link to reset your password. It expires soon:\n\n{reset_url}")
    except Exception:
        logger.exception("Failed to send password reset email")


def send_invoice_notice(to_email: str, invoice_number: str, invoice_url: str) -> bool:
    if not settings.SMTP_HOST:
        logger.warning("Invoice email was not sent because SMTP is not configured")
        return False
    try:
        _send(to_email, f"Brightloop invoice {invoice_number}", f"A new Brightloop Software invoice is ready. View or download it here:\n\n{invoice_url}")
        return True
    except Exception:
        logger.exception("Failed to send invoice notification")
        return False
