from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.models.campaign import Campaign, CampaignStep, MessageTemplate, CampaignType, CampaignStatus, CampaignGoal, Channel, CampaignPage
from app.models.user import User
from app.middleware.auth import get_current_user
from app.middleware.audit import log_event
from app.services import ai_service
from app.config import settings as _s

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    campaign_type: CampaignType
    goal: CampaignGoal
    channel: Channel = Channel.EMAIL
    target_segment: Optional[str] = None
    product_id: Optional[str] = None
    voice_tone: Optional[str] = None
    sequence_length: int = 3
    follow_up_days: int = 3
    requires_approval: bool = True
    compliance_notes: Optional[str] = None
    contact_ids: list[str] = []


@router.get("/")
async def list_campaigns(
    status: Optional[CampaignStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Campaign).order_by(Campaign.created_at.desc())
    if status:
        q = q.where(Campaign.status == status)
    result = await db.execute(q)
    return [_serialize(c) for c in result.scalars().all()]


@router.post("/", status_code=201)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = Campaign(**data.model_dump(), created_by=current_user.id)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    await log_event(db, "campaign.create", actor_type="user", actor_id=current_user.id,
                    resource_type="campaign", resource_id=c.id)
    await db.commit()
    return _serialize(c)


@router.patch("/{campaign_id}/status")
async def update_status(
    campaign_id: str,
    status: CampaignStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    c = q.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Campaign not found")
    c.status = status
    await db.commit()
    return {"id": c.id, "status": c.status}


class GenerateStepsRequest(BaseModel):
    overwrite: bool = False


class StepTemplateUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    cta: Optional[str] = None


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Campaign).options(selectinload(Campaign.steps)).where(Campaign.id == campaign_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Campaign not found")

    steps_out = []
    for step in c.steps:
        tmpl = None
        if step.template_id:
            tq = await db.execute(select(MessageTemplate).where(MessageTemplate.id == step.template_id))
            tmpl = tq.scalar_one_or_none()
        steps_out.append({
            "id": step.id,
            "step_order": step.step_order,
            "name": step.name,
            "channel": step.channel,
            "delay_days": step.delay_days,
            "is_approved": step.is_approved,
            "template_id": step.template_id,
            "template": {
                "id": tmpl.id,
                "name": tmpl.name,
                "subject": tmpl.subject,
                "body": tmpl.body,
                "cta": tmpl.cta,
                "compliance_reviewed": tmpl.compliance_reviewed,
            } if tmpl else None,
        })
    return {**_serialize(c), "steps": steps_out}


@router.post("/{campaign_id}/generate-steps")
async def generate_steps(
    campaign_id: str,
    data: GenerateStepsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI-generate message templates for every step in the campaign."""
    result = await db.execute(
        select(Campaign).options(selectinload(Campaign.steps)).where(Campaign.id == campaign_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Campaign not found")

    if c.steps and not data.overwrite:
        return {"skipped": True, "reason": "Steps already exist. Pass overwrite=true to regenerate.", "count": len(c.steps)}

    if data.overwrite:
        for step in list(c.steps):
            await db.delete(step)
        await db.flush()

    system = (
        "You are an elite mortgage sales copywriter. Output a JSON object with key 'steps', "
        "an array of message objects. Each object has: subject (string, email subject line), "
        "body (string, full message body — professional, personal, compliance-safe, no specific rate promises), "
        "cta (string, single call-to-action line). "
        f"Tone: warm, local expert, NMLS #{_s.banker_nmls} compliant. No APR/rate guarantees. "
        "Reference the campaign_type and goal in the messaging. "
        "For SMS: body must be under 160 chars. For email: full paragraph copy. "
        "Generate exactly {n} steps."
    ).replace("{n}", str(c.sequence_length))

    prompt = (
        f"Campaign: {c.name}\n"
        f"Type: {c.campaign_type}\nGoal: {c.goal}\nChannel: {c.channel}\n"
        f"Steps: {c.sequence_length}\nFollow-up interval: every {c.follow_up_days} days"
    )

    try:
        raw = await ai_service.complete_json(prompt, system=system, model=None)
        ai_steps = raw.get("steps", [])
    except Exception:
        ai_steps = []

    created = []
    for i in range(1, c.sequence_length + 1):
        ai = ai_steps[i - 1] if i <= len(ai_steps) else {}
        delay = (i - 1) * c.follow_up_days

        tmpl = MessageTemplate(
            name=f"{c.name} — Step {i}",
            channel=c.channel,
            subject=ai.get("subject", f"Step {i}: {c.name}"),
            body=ai.get("body", f"[Step {i} content — edit this template]"),
            cta=ai.get("cta"),
            created_by=current_user.id,
        )
        db.add(tmpl)
        await db.flush()

        step = CampaignStep(
            campaign_id=c.id,
            step_order=i,
            name=f"Step {i} — Day {delay}",
            channel=c.channel,
            template_id=tmpl.id,
            delay_days=delay,
        )
        db.add(step)
        await db.flush()
        created.append({"step_order": i, "delay_days": delay, "template_id": tmpl.id})

    await db.commit()
    return {"created": len(created), "steps": created}


@router.patch("/{campaign_id}/steps/{step_id}/template")
async def update_step_template(
    campaign_id: str,
    step_id: str,
    data: StepTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sq = await db.execute(
        select(CampaignStep).where(CampaignStep.id == step_id, CampaignStep.campaign_id == campaign_id)
    )
    step = sq.scalar_one_or_none()
    if not step:
        raise HTTPException(404, "Step not found")

    if step.template_id:
        tq = await db.execute(select(MessageTemplate).where(MessageTemplate.id == step.template_id))
        tmpl = tq.scalar_one_or_none()
        if tmpl:
            if data.subject is not None: tmpl.subject = data.subject
            if data.body is not None:    tmpl.body = data.body
            if data.cta is not None:     tmpl.cta = data.cta
            await db.commit()
            return {"success": True, "template_id": tmpl.id}

    raise HTTPException(400, "Step has no template to update")


# ── Campaign Pages (Ad Campaign Landing Pages) ────────────────────────────────

def _page_dict(p: CampaignPage) -> dict:
    return {
        "id":                p.id,
        "slug":              p.slug,
        "avatar":            p.avatar,
        "product":           p.product,
        "market":            p.market,
        "headline":          p.headline,
        "subheadline":       p.subheadline,
        "lead_opening":      p.lead_opening,
        "villain_paragraph": p.villain_paragraph,
        "method_steps":      p.method_steps or [],
        "proof_block":       p.proof_block,
        "cta_primary":       p.cta_primary,
        "cta_secondary":     p.cta_secondary,
        "compliance_footer": p.compliance_footer,
        "flyer_image_url":   p.flyer_image_url,
        "ad_units":          p.ad_units or [],
        "email_sequence":    p.email_sequence or [],
        "is_published":      p.is_published,
        "run_id":            p.run_id,
        "created_at":        p.created_at.isoformat() if p.created_at else None,
        "published_at":      p.published_at.isoformat() if p.published_at else None,
    }


@router.get("/pages", tags=["campaign-pages"])
async def list_campaign_pages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin: list all campaign landing pages."""
    result = await db.execute(
        select(CampaignPage).order_by(CampaignPage.created_at.desc())
    )
    return [_page_dict(p) for p in result.scalars().all()]


@router.get("/pages/public/{slug}", tags=["campaign-pages"])
async def get_campaign_page_public(slug: str, db: AsyncSession = Depends(get_db)):
    """
    Public endpoint — returns a published campaign page by slug.
    Called by the public site /campaign/:slug route.
    Returns 404 if not found or not published.
    """
    result = await db.execute(
        select(CampaignPage).where(
            CampaignPage.slug == slug,
            CampaignPage.is_published == True,
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(404, "Campaign page not found or not published")
    # Return only sales-letter fields for public view (no ad units / emails)
    return {
        "slug":              page.slug,
        "avatar":            page.avatar,
        "product":           page.product,
        "headline":          page.headline,
        "subheadline":       page.subheadline,
        "lead_opening":      page.lead_opening,
        "villain_paragraph": page.villain_paragraph,
        "method_steps":      page.method_steps or [],
        "proof_block":       page.proof_block,
        "cta_primary":       page.cta_primary,
        "cta_secondary":     page.cta_secondary,
        "compliance_footer": page.compliance_footer,
    }


@router.patch("/pages/{slug}/publish", tags=["campaign-pages"])
async def publish_campaign_page(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin: toggle a campaign page live/offline."""
    result = await db.execute(select(CampaignPage).where(CampaignPage.slug == slug))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(404, "Campaign page not found")
    page.is_published = not page.is_published
    page.published_at = datetime.utcnow() if page.is_published else None
    await db.commit()
    await log_event(db, "campaign_page.publish_toggle", actor_type="user",
                    actor_id=current_user.id, resource_type="campaign_page",
                    resource_id=page.id,
                    details={"slug": slug, "is_published": page.is_published})
    await db.commit()
    return {"slug": slug, "is_published": page.is_published, "published_at": page.published_at}


@router.delete("/pages/{slug}", tags=["campaign-pages"])
async def delete_campaign_page(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(CampaignPage).where(CampaignPage.slug == slug))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(404, "Campaign page not found")
    await db.delete(page)
    await db.commit()
    return {"deleted": slug}


def _serialize(c: Campaign) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "campaign_type": c.campaign_type,
        "goal": c.goal,
        "status": c.status,
        "channel": c.channel,
        "target_segment": c.target_segment,
        "sequence_length": c.sequence_length,
        "requires_approval": c.requires_approval,
        "contact_count": len(c.contact_ids or []),
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
