import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_email(recipients: list[str], subject: str, text: str) -> bool:
    """Send a plain-text notification. A missing SMTP setup intentionally becomes a no-op."""
    settings = get_settings()
    recipients = sorted({address.strip() for address in recipients if address and address.strip()})
    sender = settings.smtp_from_email or settings.smtp_username
    if not recipients:
        return False
    if not settings.smtp_host or not sender:
        logger.info("SMTP is not configured; skipped email %r to %s", subject, recipients)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.smtp_from_name, sender))
    message["To"] = ", ".join(recipients)
    message.set_content(text)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(message)
        return True
    except Exception:
        logger.exception("Failed to send email %r to %s", subject, recipients)
        return False
