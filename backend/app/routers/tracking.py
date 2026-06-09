"""
QR code / tracking link router.

GET  /r/{code}                      — Redirect to destination, record scan event
POST /api/v1/track/links            — Admin: create standalone QR link
GET  /api/v1/track/qr-image/{code}  — Admin: base64 QR image data URI
GET  /api/v1/track/links            — Admin: list all QR links
GET  /api/v1/track/links/{code}     — Admin: QR link details + event log
"""

import os
import uuid
from datetime import datetime
from typing import Optional
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.outreach import (
    QRLink, QREvent, CampaignOutreach, CallTask,
    OutreachStatus, CallTaskStatus,
)
from app.routers.auth import get_current_user

log = structlog.get_logger()

# Short-link router (no /api/v1 prefix — mounted at root for clean /r/{code} URLs)
short_router = APIRouter(tags=["tracking"])

# Admin tracking router (mounted at /api/v1)
router = APIRouter(prefix="/track", tags=["tracking"])

from app.config import settings as _s
BOOKING_URL = _s.calcom_link


# ── Short link redirect — GET /r/{code} ───────────────────────────────────────

@short_router.get("/r/{code}", include_in_schema=False)
async def qr_redirect(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Core tracking redirect. Called when someone scans a QR code or clicks a tracked link.

    1. Look up the QRLink by code
    2. Record a QREvent
    3. Update scan_count and last_scanned_at on the QRLink
    4. Update the linked CampaignOutreach status to QR_SCANNED
    5. Create a CallTask for the hot lead
    6. Redirect to destination URL
    """
    result = await db.execute(
        select(QRLink).where(QRLink.code == code.upper())
    )
    qr = result.scalar_one_or_none()

    if not qr or not qr.is_active:
        log.warning("qr_redirect.not_found", code=code)
        return RedirectResponse(url=BOOKING_URL, status_code=302)

    # Determine event type — QR scan vs. email click (referrer hint)
    referrer = request.headers.get("referer", "")
    ua = request.headers.get("user-agent", "")
    is_email_click = "mail" in referrer.lower() or "email" in referrer.lower()
    event_type = "click" if is_email_click else "scan"

    # Record event
    event = QREvent(
        qr_link_id=qr.id,
        outreach_id=qr.outreach_id,
        event_type=event_type,
        ip_address=request.client.host if request.client else None,
        user_agent=ua[:500] if ua else None,
        referrer=referrer[:500] if referrer else None,
        metadata={"code": code},
    )
    db.add(event)

    # Update QR link stats
    qr.scan_count = (qr.scan_count or 0) + 1
    qr.last_scanned_at = datetime.utcnow()

    # Update outreach status
    if qr.outreach_id:
        out_result = await db.execute(
            select(CampaignOutreach).where(CampaignOutreach.id == qr.outreach_id)
        )
        outreach = out_result.scalar_one_or_none()
        if outreach and outreach.status in (
            OutreachStatus.SENT, OutreachStatus.DELIVERED, OutreachStatus.MAILED
        ):
            outreach.status = OutreachStatus.QR_SCANNED
            outreach.qr_scanned_at = datetime.utcnow()

        # Create hot-lead call task (only on first scan)
        if outreach and qr.scan_count == 1:
            # Check if task already exists for this outreach
            existing_task = await db.execute(
                select(CallTask).where(CallTask.outreach_id == qr.outreach_id)
            )
            if not existing_task.scalar_one_or_none():
                # Get prospect info for task
                from app.models.outreach import Prospect
                prospect = None
                if outreach.prospect_id:
                    p_result = await db.execute(
                        select(Prospect).where(Prospect.id == outreach.prospect_id)
                    )
                    prospect = p_result.scalar_one_or_none()

                call_task = CallTask(
                    outreach_id=qr.outreach_id,
                    campaign_id=qr.campaign_id,
                    prospect_id=qr.prospect_id,
                    prospect_name=prospect.full_name if prospect else None,
                    phone=prospect.phone if prospect else None,
                    property_address=prospect.property_address if prospect else None,
                    trigger="qr_scan",
                    trigger_detail=(
                        f"Scanned QR code from {outreach.template_name or outreach.template_key} mailer. "
                        f"IP: {event.ip_address}"
                    ),
                    priority=1,  # Highest priority — they literally scanned it
                    score=None,
                    campaign_context=outreach.template_name or outreach.template_key,
                    call_script=outreach.call_script,
                    talking_points=(outreach.merge_data or {}).get("talking_points"),
                )
                db.add(call_task)
                log.info("call_task.created_from_qr", code=code, outreach_id=qr.outreach_id)

    await db.commit()
    log.info("qr.scanned", code=code, event_type=event_type, destination=qr.destination_url)
    return RedirectResponse(url=qr.destination_url, status_code=302)


# ── Pixel endpoint — GET /api/v1/track/qr/{code} ─────────────────────────────

@router.get("/qr/{code}", include_in_schema=False)
async def track_open(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    1×1 tracking pixel endpoint for email opens. Returns JSON (not an image).
    Email clients that block images won't call this — it's a best-effort signal.
    For full open tracking, use an actual transparent GIF via CDN.
    """
    result = await db.execute(
        select(QRLink).where(QRLink.code == code.upper())
    )
    qr = result.scalar_one_or_none()

    if qr:
        event = QREvent(
            qr_link_id=qr.id,
            outreach_id=qr.outreach_id,
            event_type="open",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:500],
        )
        db.add(event)
        qr.click_count = (qr.click_count or 0) + 1

        if qr.outreach_id:
            out_result = await db.execute(
                select(CampaignOutreach).where(CampaignOutreach.id == qr.outreach_id)
            )
            outreach = out_result.scalar_one_or_none()
            if outreach and not outreach.opened_at:
                outreach.opened_at = datetime.utcnow()
                outreach.status = OutreachStatus.OPENED

        await db.commit()

    # Return 1×1 transparent GIF
    gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    from fastapi.responses import Response
    return Response(content=gif, media_type="image/gif")


# ── Admin tracking routes ─────────────────────────────────────────────────────


class QRLinkCreate(BaseModel):
    label: str
    destination_url: str
    campaign_tag: Optional[str] = None   # free-form tag, e.g. "business_card_q1"


@router.post("/links", status_code=201)
async def create_qr_link(
    body: QRLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a standalone QR tracking link (not tied to an outreach piece)."""
    code = uuid.uuid4().hex[:10].upper()
    base = os.getenv("BACKEND_URL", "http://localhost:8000")
    qr = QRLink(
        code=code,
        label=body.label,
        destination_url=body.destination_url,
        # Re-use campaign_id field as a free-form tag
        campaign_id=body.campaign_tag,
    )
    db.add(qr)
    await db.commit()
    await db.refresh(qr)
    log.info("qr_link.created", code=code, label=body.label, destination=body.destination_url)
    return {
        "id": qr.id,
        "code": code,
        "label": qr.label,
        "destination_url": qr.destination_url,
        "tracking_url": f"{base}/r/{code}",
        "campaign_tag": body.campaign_tag,
        "scan_count": 0,
        "is_active": True,
        "created_at": qr.created_at,
    }


@router.get("/qr-image/{code}")
async def get_qr_image(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return a base64 data URI of the QR code image for the given tracking link."""
    result = await db.execute(select(QRLink).where(QRLink.code == code.upper()))
    qr = result.scalar_one_or_none()
    if not qr:
        raise HTTPException(404, "QR link not found")
    base = os.getenv("BACKEND_URL", "http://localhost:8000")
    tracking_url = f"{base}/r/{qr.code}"
    from app.services.qr_service import qr_data_uri
    data_uri = qr_data_uri(tracking_url, size=14, border=3)
    return {
        "code": qr.code,
        "label": qr.label,
        "tracking_url": tracking_url,
        "destination_url": qr.destination_url,
        "qr_image": data_uri,   # "data:image/png;base64,..."
    }


@router.get("/links")
async def list_qr_links(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(QRLink)
        .order_by(QRLink.created_at.desc())
        .offset(skip).limit(limit)
    )
    links = result.scalars().all()
    return [
        {
            "id": qr.id,
            "code": qr.code,
            "label": qr.label,
            "outreach_id": qr.outreach_id,
            "destination_url": qr.destination_url,
            "scan_count": qr.scan_count,
            "click_count": qr.click_count,
            "last_scanned_at": qr.last_scanned_at,
            "is_active": qr.is_active,
            "created_at": qr.created_at,
        }
        for qr in links
    ]


@router.get("/links/{code}")
async def get_qr_link_detail(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(QRLink).where(QRLink.code == code.upper())
    )
    qr = result.scalar_one_or_none()
    if not qr:
        raise HTTPException(404, "QR link not found")

    events_result = await db.execute(
        select(QREvent)
        .where(QREvent.qr_link_id == qr.id)
        .order_by(QREvent.created_at.desc())
        .limit(50)
    )
    events = events_result.scalars().all()

    return {
        "id": qr.id,
        "code": qr.code,
        "label": qr.label,
        "outreach_id": qr.outreach_id,
        "campaign_id": qr.campaign_id,
        "prospect_id": qr.prospect_id,
        "destination_url": qr.destination_url,
        "scan_count": qr.scan_count,
        "click_count": qr.click_count,
        "last_scanned_at": qr.last_scanned_at,
        "is_active": qr.is_active,
        "expires_at": qr.expires_at,
        "created_at": qr.created_at,
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "ip_address": e.ip_address,
                "user_agent": e.user_agent,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }


@router.get("/summary")
async def tracking_summary(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Overall tracking stats across all campaigns."""
    from sqlalchemy import func

    total_qr = await db.execute(select(func.count(QRLink.id)))
    total_scans = await db.execute(select(func.sum(QRLink.scan_count)))
    total_sent = await db.execute(
        select(func.count(CampaignOutreach.id))
        .where(CampaignOutreach.status != OutreachStatus.DRAFT)
    )
    total_opened = await db.execute(
        select(func.count(CampaignOutreach.id))
        .where(CampaignOutreach.opened_at.isnot(None))
    )
    total_qr_scanned = await db.execute(
        select(func.count(CampaignOutreach.id))
        .where(CampaignOutreach.qr_scanned_at.isnot(None))
    )
    total_call_tasks = await db.execute(
        select(func.count(CallTask.id))
        .where(CallTask.status == CallTaskStatus.PENDING)
    )

    return {
        "total_qr_links": total_qr.scalar() or 0,
        "total_scans": total_scans.scalar() or 0,
        "total_sent": total_sent.scalar() or 0,
        "total_opened": total_opened.scalar() or 0,
        "total_qr_scanned": total_qr_scanned.scalar() or 0,
        "pending_call_tasks": total_call_tasks.scalar() or 0,
    }
