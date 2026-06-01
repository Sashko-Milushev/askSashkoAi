"""
Async email notification service using aiosmtplib.
Sends plain-text emails to the owner for:
  - New contact form submissions
  - Daily OpenAI cost cap alerts
"""
import datetime
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)


def _is_configured() -> bool:
    """Return True only if SMTP credentials are fully set."""
    return bool(
        settings.smtp_host
        and settings.smtp_user
        and settings.smtp_pass
        and settings.owner_email
    )


async def _send(subject: str, body: str) -> None:
    """Low-level async SMTP send. Logs warning if credentials not configured."""
    if not _is_configured():
        logger.warning("Email not sent — SMTP credentials not configured. Subject: %s", subject)
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.smtp_user
    message["To"] = settings.owner_email
    message.attach(MIMEText(body, "plain"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_pass,
            start_tls=True,
        )
        logger.info("Email sent | subject=%s | to=%s", subject, settings.owner_email)
    except aiosmtplib.SMTPException as exc:
        logger.error("Failed to send email | subject=%s | error=%s", subject, exc)
    except Exception as exc:
        logger.error("Unexpected email error | subject=%s | error=%s", subject, exc)


# ── Public functions ───────────────────────────────────────────────────────────

async def send_contact_notification(name: str, email: str, message: str) -> None:
    """Notify owner when a contact form is submitted."""
    subject = f"[askSashkoAi] New contact message from {name}"
    body = f"""You have a new message from your portfolio website.

From:    {name}
Email:   {email}
Time:    {datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d %H:%M UTC')}

Message:
--------
{message}
--------

Reply directly to: {email}
"""
    await _send(subject, body)


async def send_cap_alert(daily_cost: float) -> None:
    """Notify owner when the daily OpenAI cost cap is hit."""
    today = datetime.date.today().isoformat()
    subject = f"[askSashkoAi] ⚠️ Daily cost cap hit — {today}"
    body = f"""Daily OpenAI cost cap reached on {today}.

Accumulated cost : ${daily_cost:.4f} USD
Cap limit        : ${settings.daily_cost_cap_usd:.2f} USD

The chatbot is now blocking new AI requests until midnight UTC.
No further emails will be sent today for this alert.

To raise the cap, update DAILY_COST_CAP_USD in your environment variables.
"""
    await _send(subject, body)
