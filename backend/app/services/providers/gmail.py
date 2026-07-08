"""
Gmail SMTP Email Provider — sends campaign emails via Gmail using aiosmtplib.

Uses STARTTLS on port 587 (standard Gmail App Password setup).
Set CAMPAIGN_EMAIL_PROVIDER=gmail in .env to activate.

Requirements:
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=you@gmail.com
  SMTP_PASSWORD=your-app-password   # Gmail → Security → App Passwords
  CAMPAIGN_FROM_EMAIL=you@yourdomain.com
  CAMPAIGN_FROM_NAME=Your Name

Note: Gmail limits ~500 sends/day on a free account.
Flip to CAMPAIGN_EMAIL_PROVIDER=resend when you're ready to scale.
"""

import uuid
import structlog
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid

import aiosmtplib

from app.services.providers.base import EmailProvider, ProviderResult

log = structlog.get_logger()


class GmailEmailProvider(EmailProvider):
    """
    Async SMTP email sender via Gmail (or any STARTTLS SMTP server).

    drop-in for CAMPAIGN_EMAIL_PROVIDER=gmail
    """
    name = "gmail"

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        from_name: str,
    ):
        self.smtp_host     = smtp_host
        self.smtp_port     = smtp_port
        self.smtp_user     = smtp_user
        self.smtp_password = smtp_password
        self.from_email    = from_email
        self.from_name     = from_name

    async def send_email(self, payload: dict) -> ProviderResult:
        """
        Send a single email via Gmail SMTP (STARTTLS / port 587).

        payload keys:
          to_email      (required)
          to_name       (optional)
          subject       (required)
          html_body     (optional but recommended)
          text_body     (optional fallback)
          reply_to      (optional)
        """
        to_email = payload.get("to_email")
        if not to_email:
            return ProviderResult(success=False, error="to_email is required")

        if not self.smtp_user or not self.smtp_password:
            return ProviderResult(success=False, error="SMTP_USER or SMTP_PASSWORD not set")

        subject   = payload.get("subject", "(no subject)")
        html_body = payload.get("html_body", "")
        text_body = payload.get("text_body", "")
        reply_to  = payload.get("reply_to", "")
        to_name   = payload.get("to_name", "")

        # Allow per-send override of from identity (campaign-level white-label)
        from_name  = payload.get("from_name", self.from_name)
        from_email = payload.get("from_email", self.from_email)

        # Build MIME message
        msg = MIMEMultipart("alternative")
        msg["Subject"]  = subject
        msg["From"]     = formataddr((from_name, from_email))
        msg["To"]       = formataddr((to_name, to_email)) if to_name else to_email
        msg["Date"]     = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=from_email.split("@")[-1] if "@" in from_email else "mail")

        if reply_to:
            msg["Reply-To"] = reply_to

        # Attach text first, HTML second (email clients prefer the last part)
        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))
        if not text_body and not html_body:
            msg.attach(MIMEText("(no content)", "plain", "utf-8"))

        provider_id = msg["Message-ID"]

        try:
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True,
            )
            log.info(
                "gmail.email_sent",
                to=to_email,
                subject=subject,
                message_id=provider_id,
            )
            return ProviderResult(
                success=True,
                provider_id=provider_id,
                status="sent",
            )

        except aiosmtplib.SMTPAuthenticationError as exc:
            log.error("gmail.auth_failed", error=str(exc))
            return ProviderResult(
                success=False,
                error=f"Gmail authentication failed. Check SMTP_USER / SMTP_PASSWORD (use an App Password, not your Gmail password). {exc}",
            )
        except aiosmtplib.SMTPException as exc:
            log.error("gmail.smtp_error", to=to_email, error=str(exc))
            return ProviderResult(success=False, error=f"SMTP error: {exc}")
        except Exception as exc:
            log.error("gmail.unexpected_error", to=to_email, error=str(exc))
            return ProviderResult(success=False, error=str(exc))

    # ── Suppression ───────────────────────────────────────────────────────────
    # Gmail SMTP has no API suppression list — we rely on the app's own DB.

    async def add_suppression(self, email: str, reason: str) -> bool:
        """No-op — suppression is managed in the app DB, not by Gmail."""
        log.info("gmail.suppression_noted", email=email, reason=reason)
        return True

    async def get_suppressions(self) -> list[str]:
        """No-op — Gmail doesn't expose a suppression list via SMTP."""
        return []

    async def handle_webhook(self, payload: dict) -> dict:
        """Gmail SMTP has no webhooks. Return empty."""
        return {}
