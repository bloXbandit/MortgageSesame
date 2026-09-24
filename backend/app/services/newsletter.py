"""
Newsletter — recurring market-update email to the sphere.

draft_market_update() builds one email from the latest RateSnapshot plus an
educational tip; the caller fans it out into per-recipient CampaignOutreach
drafts (approval-gated — nothing sends from here).

Kept deliberately template-driven: rates come from the DB, the tip rotates,
and the compliance footer is hardwired. AI polish can layer on later without
changing the contract.
"""

from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.hub import RateSnapshot
from app.routers.unsubscribe import generate_unsubscribe_url

log = structlog.get_logger()

_TIPS = [
    ("Thinking about waiting for rates to drop?",
     "Buying at today's rate with a plan to refinance later often beats waiting — "
     "home prices rarely pause for rates."),
    ("Your equity may be doing more than you think.",
     "Most homeowners are sitting on more equity than they realize. A 10-minute "
     "review can tell you what options it opens up."),
    ("Pre-approval isn't just paperwork.",
     "In a competitive offer situation, a same-day pre-approval letter is often "
     "the difference between winning and losing the house."),
    ("Down payment assistance is real.",
     "Maryland and DC both run programs that can cover part or all of a down "
     "payment for qualified buyers — most people never check."),
]


def _fmt_rate(v) -> str:
    return f"{float(v):.2f}%" if v else "—"


def _tip_for_today() -> tuple:
    return _TIPS[datetime.utcnow().toordinal() % len(_TIPS)]


async def draft_market_update(db: AsyncSession, recipient_email: Optional[str] = None,
                              first_name: str = "there") -> dict:
    """Build one market-update email. Returns {subject, body_text, body_html}."""
    snap = (await db.execute(
        select(RateSnapshot).order_by(desc(RateSnapshot.snapshot_date)).limit(1)
    )).scalar_one_or_none()

    conv = _fmt_rate(snap.rate_conventional_30 if snap else None)
    fha = _fmt_rate(snap.rate_fha_30 if snap else None)
    va = _fmt_rate(getattr(snap, "rate_va_30", None) if snap else None)
    as_of = snap.snapshot_date if snap else datetime.utcnow().strftime("%Y-%m-%d")

    title, tip = _tip_for_today()
    banker = settings.banker_name or "your loan officer"
    nmls = settings.banker_nmls or ""
    booking = settings.calcom_link or "#"
    unsub = generate_unsubscribe_url(recipient_email) if recipient_email else "#unsubscribe"

    subject = f"Rates this week ({as_of}) + one thing worth knowing"
    body_text = (
        f"Hi {first_name},\n\n"
        f"Quick market update — here's where rates sat as of {as_of}:\n\n"
        f"  • Conventional 30-yr: {conv}\n"
        f"  • FHA 30-yr:          {fha}\n"
        + (f"  • VA 30-yr:           {va}\n" if va != "—" else "") +
        f"\n{title}\n{tip}\n\n"
        f"Want me to run your specific numbers? Grab 15 minutes here: {booking}\n\n"
        f"— {banker}\nNMLS #{nmls}\n\n"
        f"To opt out of future emails: {unsub}"
    )
    body_html = (
        f"<p>Hi {first_name},</p>"
        f"<p>Quick market update — here's where rates sat as of <strong>{as_of}</strong>:</p>"
        f'<table style="border-collapse:collapse;margin:12px 0;font-size:15px">'
        f'<tr><td style="padding:4px 16px 4px 0;color:#555">Conventional 30-yr</td><td><strong>{conv}</strong></td></tr>'
        f'<tr><td style="padding:4px 16px 4px 0;color:#555">FHA 30-yr</td><td><strong>{fha}</strong></td></tr>'
        + (f'<tr><td style="padding:4px 16px 4px 0;color:#555">VA 30-yr</td><td><strong>{va}</strong></td></tr>' if va != "—" else "") +
        f"</table>"
        f"<p><strong>{title}</strong><br>{tip}</p>"
        f'<p>Want me to run your specific numbers? <a href="{booking}">Grab 15 minutes here</a>.</p>'
        f"<p>— {banker}<br>NMLS #{nmls}</p>"
        f'<p style="font-size:11px;color:#888">To opt out of future emails, <a href="{unsub}">click here</a>.'
        f" Equal Housing Opportunity. Rates shown are illustrative, not a commitment to lend.</p>"
    )
    return {"subject": subject, "body_text": body_text, "body_html": body_html,
            "as_of": as_of, "rates": {"conventional": conv, "fha": fha, "va": va}}
