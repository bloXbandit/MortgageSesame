"""
Unsubscribe / opt-out router.

GET  /unsubscribe?token={token}        Show confirmation page (GET = safe, idempotent)
POST /unsubscribe                      Process opt-out, add to suppression

Token = HMAC-SHA256(email, SECRET_KEY) encoded as URL-safe base64.
Signed so we can't be used to unsubscribe arbitrary addresses via URL guessing.

Helper: generate_unsubscribe_url(email) → full URL to embed in emails.
"""

import base64
import hashlib
import hmac
import os
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.outreach import SuppressionEntry

log = structlog.get_logger()

router = APIRouter(tags=["unsubscribe"])

# ── Token helpers ─────────────────────────────────────────────────────────────

def _secret() -> bytes:
    key = os.getenv("SECRET_KEY", "CHANGE_ME")
    return key.encode()


def generate_unsubscribe_token(email: str) -> str:
    """HMAC-sign an email address to produce a tamper-proof unsubscribe token."""
    sig = hmac.new(_secret(), email.lower().encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def verify_unsubscribe_token(email: str, token: str) -> bool:
    """Return True if token is a valid signature for this email."""
    expected = generate_unsubscribe_token(email)
    return hmac.compare_digest(expected, token)


def generate_unsubscribe_url(email: str, base_url: Optional[str] = None) -> str:
    """
    Return a full unsubscribe URL for embedding in email footers.

    Usage in campaign_writer.py:
        from app.routers.unsubscribe import generate_unsubscribe_url
        unsub_url = generate_unsubscribe_url(prospect_email)
        html = html.replace("{{unsubscribe_url}}", unsub_url)
    """
    base = base_url or os.getenv("BACKEND_URL", "http://localhost:8000")
    token = generate_unsubscribe_token(email)
    encoded_email = base64.urlsafe_b64encode(email.lower().encode()).decode().rstrip("=")
    return f"{base}/unsubscribe?email={encoded_email}&token={token}"


# ── Pages ─────────────────────────────────────────────────────────────────────

_CONFIRM_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Unsubscribe — MortgageSesame</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f9f7f4; display: flex; align-items: center;
            justify-content: center; min-height: 100vh; padding: 20px; }}
    .card {{ background: #fff; border-radius: 10px; padding: 40px 36px;
             max-width: 420px; width: 100%; text-align: center;
             box-shadow: 0 4px 24px rgba(0,0,0,0.07); }}
    .icon {{ font-size: 40px; margin-bottom: 16px; }}
    h1 {{ font-size: 1.3rem; color: #1f1f1f; margin-bottom: 8px; }}
    p {{ font-size: 0.9rem; color: #666; line-height: 1.6; margin-bottom: 20px; }}
    .email {{ font-weight: 600; color: #1f1f1f; }}
    form {{ margin-top: 8px; }}
    button {{ background: #1f1f1f; color: #f5c87a; border: none; padding: 12px 28px;
              border-radius: 6px; font-size: 0.95rem; font-weight: 600; cursor: pointer;
              width: 100%; }}
    button:hover {{ background: #333; }}
    .already {{ color: #999; font-size: 0.82rem; margin-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✉️</div>
    <h1>Unsubscribe from emails?</h1>
    <p>We'll stop sending marketing emails to<br>
       <span class="email">{email}</span></p>
    <form method="POST" action="/unsubscribe">
      <input type="hidden" name="email" value="{email_encoded}">
      <input type="hidden" name="token" value="{token}">
      <button type="submit">Yes, unsubscribe me</button>
    </form>
    <p class="already">You'll still receive any transactional emails related to an active loan application.</p>
  </div>
</body>
</html>"""

_SUCCESS_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Unsubscribed — MortgageSesame</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f9f7f4; display: flex; align-items: center;
            justify-content: center; min-height: 100vh; padding: 20px; }}
    .card {{ background: #fff; border-radius: 10px; padding: 40px 36px;
             max-width: 420px; width: 100%; text-align: center;
             box-shadow: 0 4px 24px rgba(0,0,0,0.07); }}
    .icon {{ font-size: 40px; margin-bottom: 16px; }}
    h1 {{ font-size: 1.3rem; color: #1f1f1f; margin-bottom: 8px; }}
    p {{ font-size: 0.9rem; color: #666; line-height: 1.6; }}
    .email {{ font-weight: 600; color: #1f1f1f; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✅</div>
    <h1>You've been unsubscribed</h1>
    <p><span class="email">{email}</span> has been removed from our marketing list.
       You won't receive any further emails from us.<br><br>
       If this was a mistake, reply to any previous email and we'll add you back.</p>
  </div>
</body>
</html>"""

_INVALID_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Invalid Link — MortgageSesame</title>
  <style>
    body {{ font-family: sans-serif; background: #f9f7f4; display: flex;
            align-items: center; justify-content: center; min-height: 100vh; }}
    .card {{ background: #fff; border-radius: 10px; padding: 40px; max-width: 380px;
             text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,0.07); }}
  </style>
</head>
<body>
  <div class="card">
    <div style="font-size:36px;margin-bottom:16px">⚠️</div>
    <h2 style="margin-bottom:8px">Invalid or expired link</h2>
    <p style="color:#666;font-size:0.9rem">This unsubscribe link is not valid.
    Please use the link from your original email, or reply to the email directly to opt out.</p>
  </div>
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
async def unsubscribe_page(
    email: str = Query(...),
    token: str = Query(...),
):
    """Show the unsubscribe confirmation page."""
    try:
        decoded = base64.urlsafe_b64decode(email + "==").decode()
    except Exception:
        return HTMLResponse(_INVALID_PAGE, status_code=400)

    if not verify_unsubscribe_token(decoded, token):
        return HTMLResponse(_INVALID_PAGE, status_code=400)

    html = _CONFIRM_PAGE.format(
        email=decoded,
        email_encoded=email,
        token=token,
    )
    return HTMLResponse(html)


from fastapi import Request as FARequest
from typing import Optional

@router.post("/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
async def process_unsubscribe_form(
    request: FARequest,
    db: AsyncSession = Depends(get_db),
):
    """Process the unsubscribe confirmation form (form-encoded POST)."""
    try:
        form = await request.form()
        email_encoded = form.get("email", "")
        token = form.get("token", "")

        decoded = base64.urlsafe_b64decode(email_encoded + "==").decode()

        if not verify_unsubscribe_token(decoded, token):
            return HTMLResponse(_INVALID_PAGE, status_code=400)

        # Add to suppression if not already there
        existing = await db.execute(
            select(SuppressionEntry).where(SuppressionEntry.value == decoded.lower())
        )
        if not existing.scalar_one_or_none():
            entry = SuppressionEntry(
                value=decoded.lower(),
                value_type="email",
                reason="opt_out",
                source="email_unsubscribe_link",
            )
            db.add(entry)
            await db.commit()
            log.info("unsubscribe.processed", email=decoded)

        return HTMLResponse(_SUCCESS_PAGE.format(email=decoded))

    except Exception as e:
        log.error("unsubscribe.error", error=str(e))
        return HTMLResponse(_INVALID_PAGE, status_code=400)
