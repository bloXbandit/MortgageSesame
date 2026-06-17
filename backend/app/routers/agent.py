"""
Agent Tool API — 13 endpoints for Clawdbot/OpenClaw/Hermes or any OpenAI-function-calling agent.

Auth: Bearer token = AGENT_API_KEY from .env
Every action is logged. No external sends without explicit approval.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Any
from app.database import get_db
from app.models.product import Product
from app.models.contact import Contact
from app.models.campaign import Campaign
from app.models.agent import AgentRun, AgentAction, ApprovalQueue, Task, AgentActionType, AgentActionStatus, ApprovalItemType
from app.models.content import SocialPost, ApprovalStatus
from app.models.lead import LeadIntake
from app.services import ai_service
from app.services.compliance import check_content
from app.services.integrations.elevenlabs import generate_audio
from app.middleware.auth import require_agent_key
from app.middleware.audit import log_event
from app.models.agent_memory import AgentMemoryLog, AgentAsk
import json
import httpx

router = APIRouter(prefix="/agent", tags=["agent"], dependencies=[Depends(require_agent_key)])


# ── GET /agent/context ─────────────────────────────────────────────────────
@router.get("/context")
async def get_context(db: AsyncSession = Depends(get_db)):
    """Returns current system state summary for agent orientation."""
    products_q = await db.execute(select(Product).where(Product.is_active == True))
    contacts_q = await db.execute(select(Contact).where(Contact.is_dnc == False))
    campaigns_q = await db.execute(select(Campaign))
    pending_q = await db.execute(select(ApprovalQueue).where(ApprovalQueue.status == "pending"))

    return {
        "active_products": products_q.scalars().all().__len__(),
        "total_contacts": contacts_q.scalars().all().__len__(),
        "total_campaigns": campaigns_q.scalars().all().__len__(),
        "pending_approvals": pending_q.scalars().all().__len__(),
        "timestamp": datetime.utcnow().isoformat(),
        "agent_instructions": (
            "You are operating within MortgageSesame. "
            "All outbound actions require human approval unless explicitly unlocked. "
            "Never contact DNC/opted-out contacts. "
            "Always run compliance checks before queuing outreach."
        ),
    }


# ── GET /agent/products ────────────────────────────────────────────────────
@router.get("/products")
async def get_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.is_active == True))
    return [
        {
            "id": p.id, "name": p.name, "product_type": p.product_type,
            "audience": p.audience, "benefits": p.benefits,
            "cta_language": p.cta_language, "prohibited_claims": p.prohibited_claims,
        }
        for p in result.scalars().all()
    ]


# ── GET /agent/campaigns ───────────────────────────────────────────────────
@router.get("/campaigns")
async def get_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign))
    return [
        {
            "id": c.id, "name": c.name, "campaign_type": c.campaign_type,
            "goal": c.goal, "status": c.status, "channel": c.channel,
            "requires_approval": c.requires_approval,
        }
        for c in result.scalars().all()
    ]


# ── GET /agent/contacts ────────────────────────────────────────────────────
@router.get("/contacts")
async def get_contacts(contact_type: Optional[str] = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    q = select(Contact).where(Contact.is_dnc == False, Contact.is_opted_out == False).limit(limit)
    if contact_type:
        q = q.where(Contact.contact_type == contact_type)
    result = await db.execute(q)
    return [
        {
            "id": c.id,
            "name": f"{c.first_name or ''} {c.last_name or ''}".strip(),
            "email": c.email, "phone": c.phone, "company": c.company,
            "contact_type": c.contact_type, "city": c.city, "state": c.state,
            "consent_email": c.consent_email, "consent_sms": c.consent_sms,
            "lead_score": c.lead_score,
        }
        for c in result.scalars().all()
    ]


# ── Shared request/response models ────────────────────────────────────────
class ResearchTargetRequest(BaseModel):
    contact_id: str
    research_type: str = "general"
    context: Optional[str] = None

class GenerateOutreachRequest(BaseModel):
    contact_id: str
    product_id: Optional[str] = None
    goal: str
    channel: str = "email"
    run_id: Optional[str] = None

class GenerateContentRequest(BaseModel):
    platform: str
    category: str
    product_id: Optional[str] = None
    run_id: Optional[str] = None

class ScoreLeadRequest(BaseModel):
    intake_id: str

class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: Optional[str] = None
    priority: str = "normal"
    contact_id: Optional[str] = None
    campaign_id: Optional[str] = None

class QueueActionRequest(BaseModel):
    item_type: ApprovalItemType
    item_id: str
    title: str
    preview: str
    priority: int = 0

class ReportRunRequest(BaseModel):
    agent_name: str
    run_type: str
    status: str
    input_payload: Optional[dict] = None
    output_payload: Optional[dict] = None
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None

class LogEventRequest(BaseModel):
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict] = None

class ComplianceCheckRequest(BaseModel):
    text: str
    channel: str = "general"
    is_ad: bool = False

class VoiceGenerateRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    save_as: Optional[str] = None


# ── POST /agent/research-target ────────────────────────────────────────────
@router.post("/research-target")
async def research_target(data: ResearchTargetRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == data.contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")

    summary = await ai_service.complete(
        f"Summarize what we know about this contact and suggest talking points:\n"
        f"Name: {contact.first_name} {contact.last_name}\n"
        f"Company: {contact.company}\nRole: {contact.role_title}\n"
        f"Type: {contact.contact_type}\nCity: {contact.city}, {contact.state}\n"
        f"Research context: {data.context or 'general outreach'}",
        system="You are a mortgage banker's research assistant. Be concise. No invented facts.",
    )
    await log_event(db, "agent.research_target", actor_type="agent", resource_type="contact", resource_id=data.contact_id)
    await db.commit()
    return {"contact_id": data.contact_id, "research_summary": summary}


# ── POST /agent/generate-outreach ──────────────────────────────────────────
class AgentGenerateOutreachRequest(BaseModel):
    """Extended generate-outreach that supports both Contact and Prospect targets."""
    contact_id: Optional[str] = None
    prospect_id: Optional[str] = None
    product_id: Optional[str] = None
    goal: str = "refi_rate_reduction"
    channel: str = "email"
    step: int = 1
    run_id: Optional[str] = None

@router.post("/generate-outreach")
async def generate_outreach(data: AgentGenerateOutreachRequest, db: AsyncSession = Depends(get_db)):
    from app.services.campaign_writer import get_writer
    from app.models.outreach import Prospect

    writer = get_writer()
    target_dict: dict = {}
    resource_id = data.contact_id or data.prospect_id or "unknown"

    # Resolve target — prefer Prospect (has rate/equity data), fall back to Contact
    if data.prospect_id:
        p_q = await db.execute(select(Prospect).where(Prospect.id == data.prospect_id))
        prospect = p_q.scalar_one_or_none()
        if not prospect:
            raise HTTPException(404, "Prospect not found")
        if prospect.is_do_not_contact or prospect.is_suppressed:
            raise HTTPException(403, "Prospect is on DNC/suppression list.")
        target_dict = {
            "first_name": prospect.first_name, "last_name": prospect.last_name,
            "full_name": prospect.full_name, "email": prospect.email, "phone": prospect.phone,
            "property_address": prospect.property_address, "property_city": prospect.property_city,
            "current_rate_estimate": prospect.current_rate_estimate,
            "estimated_equity_pct": prospect.estimated_equity_pct,
            "estimated_equity_dollars": prospect.estimated_equity_dollars,
            "current_loan_amount": prospect.current_loan_amount,
            "loan_type": prospect.loan_type, "is_owner_occupied": prospect.is_owner_occupied,
            "prospect_type": prospect.prospect_type.value if prospect.prospect_type else "homeowner",
        }
    elif data.contact_id:
        contact_q = await db.execute(select(Contact).where(Contact.id == data.contact_id))
        contact = contact_q.scalar_one_or_none()
        if not contact:
            raise HTTPException(404, "Contact not found")
        if contact.is_dnc or contact.is_opted_out:
            raise HTTPException(403, "Contact is DNC or opted out.")
        target_dict = {
            "first_name": contact.first_name, "last_name": contact.last_name,
            "email": contact.email, "phone": contact.phone,
            "company_name": contact.company,
            "prospect_type": contact.contact_type or "homeowner",
        }
    else:
        raise HTTPException(400, "Provide contact_id or prospect_id")

    # Generate via campaign writer
    campaign_type = data.goal
    result: dict = {}

    if data.channel == "email":
        draft = await writer.generate_email(target_dict, campaign_type=campaign_type, step=data.step)
        result = {"subject": draft.subject, "body_html": draft.body_html, "body_text": draft.body_text}
    elif data.channel == "sms":
        sms = await writer.generate_sms(target_dict, campaign_type=campaign_type, step=data.step)
        result = {"body": sms.body, "char_count": sms.char_count}
    elif data.channel == "direct_mail":
        from app.services.mail_templates import render_mail_template
        merge = await writer.generate_mail_merge_data(target_dict)
        html = render_mail_template(merge.get("template_key", "equity_voucher"), merge)
        result = {"body_html": html, "merge_data": merge}
    elif data.channel == "call_script":
        script = await writer.generate_call_script(target_dict, campaign_type=campaign_type)
        result = {
            "opener": script.opener, "pitch": script.pitch,
            "talking_points": script.talking_points,
            "objection_handlers": script.objection_handlers,
            "close": script.close, "voicemail": script.voicemail,
        }
    else:
        draft = await writer.generate_email(target_dict, campaign_type=campaign_type, step=data.step)
        result = {"subject": draft.subject, "body_html": draft.body_html, "body_text": draft.body_text}

    compliance = check_content(
        result.get("body_html") or result.get("body") or result.get("pitch", ""),
        channel=data.channel,
    )

    await log_event(db, "agent.generate_outreach", actor_type="agent",
                    resource_type="prospect" if data.prospect_id else "contact",
                    resource_id=resource_id,
                    details={"channel": data.channel, "campaign_type": campaign_type,
                             "step": data.step, "compliance_passed": compliance.passed})
    await db.commit()

    return {
        "draft": result,
        "channel": data.channel,
        "campaign_type": campaign_type,
        "compliance": {"passed": compliance.passed, "flags": compliance.flags},
        "requires_approval": True,
        "note": "Queue via /agent/queue-action before any send.",
    }


# ── POST /agent/generate-content ───────────────────────────────────────────
@router.post("/generate-content")
async def generate_content(data: GenerateContentRequest, db: AsyncSession = Depends(get_db)):
    product_context = ""
    if data.product_id:
        p_q = await db.execute(select(Product).where(Product.id == data.product_id))
        prod = p_q.scalar_one_or_none()
        if prod:
            product_context = f"{prod.name}: {prod.benefits or ''}"

    content = await ai_service.generate_content(data.platform, data.category, product_context)
    compliance = check_content(content.get("caption", "") + " " + content.get("script", ""), is_ad=True)

    post = SocialPost(
        platform=data.platform,
        category=data.category,
        hook=content.get("hook"),
        script=content.get("script"),
        caption=content.get("caption"),
        cta=content.get("cta"),
        visual_concept=content.get("visual_concept"),
        image_prompt=content.get("image_prompt"),
        voiceover_script=content.get("voiceover_script"),
        broll_instructions=content.get("broll_instructions"),
        compliance_notes=content.get("compliance_notes"),
        is_fictional_example=content.get("is_fictional_example", False),
        approval_status=ApprovalStatus.PENDING,
        generated_by="agent",
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    return {"post_id": post.id, "content": content, "compliance": {"passed": compliance.passed, "flags": compliance.flags}}


# ── POST /agent/score-lead ─────────────────────────────────────────────────
@router.post("/score-lead")
async def score_lead(data: ScoreLeadRequest, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(LeadIntake).where(LeadIntake.id == data.intake_id))
    intake = q.scalar_one_or_none()
    if not intake:
        raise HTTPException(404, "Lead intake not found")

    intake_dict = {
        "loan_interest_type": intake.loan_interest_type,
        "timeline": intake.timeline,
        "credit_score_range": intake.credit_score_range,
        "income_range": intake.income_range,
        "cash_available": intake.cash_available,
        "state": intake.state,
    }
    score = await ai_service.score_lead(intake_dict)
    return {"intake_id": data.intake_id, "score": score}


# ── POST /agent/create-task ────────────────────────────────────────────────
@router.post("/create-task", status_code=201)
async def create_task(data: CreateTaskRequest, db: AsyncSession = Depends(get_db)):
    task = Task(**data.model_dump(), created_by="agent")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return {"task_id": task.id, "title": task.title, "status": task.status}


# ── POST /agent/queue-action ───────────────────────────────────────────────
@router.post("/queue-action", status_code=201)
async def queue_action(data: QueueActionRequest, db: AsyncSession = Depends(get_db)):
    item = ApprovalQueue(
        item_type=data.item_type,
        item_id=data.item_id,
        title=data.title,
        preview=data.preview,
        priority=data.priority,
        created_by="agent",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"queue_id": item.id, "status": "pending_approval"}


# ── POST /agent/report-run ─────────────────────────────────────────────────
@router.post("/report-run", status_code=201)
async def report_run(data: ReportRunRequest, db: AsyncSession = Depends(get_db)):
    run = AgentRun(
        agent_name=data.agent_name,
        run_type=data.run_type,
        status=data.status,
        input_payload=data.input_payload,
        output_payload=data.output_payload,
        error_message=data.error_message,
        duration_ms=data.duration_ms,
        completed_at=datetime.utcnow(),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return {"run_id": run.id}


# ── GET /agent/pending-approvals ───────────────────────────────────────────
@router.get("/pending-approvals")
async def get_pending_approvals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ApprovalQueue).where(ApprovalQueue.status == "pending").order_by(
            ApprovalQueue.priority.desc(), ApprovalQueue.created_at.asc()
        )
    )
    items = result.scalars().all()
    return [
        {"id": i.id, "item_type": i.item_type, "item_id": i.item_id,
         "title": i.title, "preview": i.preview, "created_at": i.created_at.isoformat()}
        for i in items
    ]


# ── POST /agent/compliance-check ───────────────────────────────────────────
@router.post("/compliance-check")
async def compliance_check(data: ComplianceCheckRequest):
    result = check_content(data.text, channel=data.channel, is_ad=data.is_ad)
    return {"passed": result.passed, "flags": result.flags}


# ── POST /agent/log-event ──────────────────────────────────────────────────
@router.post("/log-event")
async def log_agent_event(data: LogEventRequest, db: AsyncSession = Depends(get_db)):
    await log_event(db, data.action, actor_type="agent", resource_type=data.resource_type,
                    resource_id=data.resource_id, details=data.details)
    await db.commit()
    return {"logged": True}


# ── POST /agent/content-pipeline ──────────────────────────────────────────
class ContentPipelineRequest(BaseModel):
    """
    Run the full content production pipeline on a post.
    Can also generate a new post first if no post_id is given.
    """
    post_id: Optional[str] = None           # Existing SocialPost to run through pipeline
    # If post_id is None, generate a new post first:
    platform: Optional[str] = "tiktok"
    category: Optional[str] = "refi_triggers"
    product_id: Optional[str] = None
    # Pipeline steps to run:
    generate_voice: bool = True
    generate_video: bool = False            # Off until HEYGEN_API_KEY is set
    auto_queue: bool = True
    run_id: Optional[str] = None


@router.post("/content-pipeline")
async def run_content_pipeline(data: ContentPipelineRequest, db: AsyncSession = Depends(get_db)):
    """
    Orchestrate: generate → compliance → voice → video → approval queue.
    The agent calls this to run a full production cycle autonomously.
    """
    from app.services.content_agent import run_content_pipeline as _run_pipeline
    from app.models.content import SocialPost, ContentPlatform, ContentCategory, ApprovalStatus

    post_id = data.post_id

    # If no existing post, generate one first
    if not post_id:
        if not data.platform or not data.category:
            raise HTTPException(400, "Provide post_id OR platform+category to generate a new post")

        # Load script templates for context
        from app.routers.content import _load_template_context
        template_ctx = await _load_template_context(db, data.platform, data.category)

        product_context = ""
        if data.product_id:
            p_q = await db.execute(select(Product).where(Product.id == data.product_id))
            prod = p_q.scalar_one_or_none()
            if prod:
                product_context = f"{prod.name}: {prod.benefits or ''}"

        content = await ai_service.generate_content(
            data.platform, data.category, product_context,
            template_context=template_ctx
        )
        compliance = check_content(
            (content.get("caption") or "") + " " + (content.get("script") or ""),
            is_ad=True,
        )

        if not compliance.passed:
            await log_event(db, "agent.content_pipeline.compliance_block", actor_type="agent",
                            details={"flags": compliance.flags, "platform": data.platform})
            await db.commit()
            return {
                "status": "blocked",
                "reason": "compliance_failed",
                "flags": compliance.flags,
                "message": "Content failed compliance check. Review flags and adjust templates before retrying.",
            }

        try:
            plat_enum = ContentPlatform(data.platform)
            cat_enum  = ContentCategory(data.category)
        except ValueError:
            raise HTTPException(400, f"Invalid platform '{data.platform}' or category '{data.category}'")

        post = SocialPost(
            platform=plat_enum,
            category=cat_enum,
            hook=content.get("hook"),
            script=content.get("script"),
            voiceover_script=content.get("voiceover_script"),
            caption=content.get("caption"),
            cta=content.get("cta"),
            visual_concept=content.get("visual_concept"),
            image_prompt=content.get("image_prompt"),
            video_prompt=content.get("video_prompt"),
            broll_instructions=content.get("broll_instructions"),
            compliance_notes=content.get("compliance_notes"),
            is_fictional_example=content.get("is_fictional_example", False),
            approval_status=ApprovalStatus.PENDING,
            pipeline_stage="script_only",
            generated_by="agent",
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)
        post_id = post.id

        await log_event(db, "agent.content_generated", actor_type="agent",
                        resource_type="social_post", resource_id=post_id,
                        details={"platform": data.platform, "category": data.category,
                                 "compliance_passed": True})
        await db.commit()

    # Run the production pipeline
    result = await _run_pipeline(
        db, post_id,
        generate_voice=data.generate_voice,
        generate_video=data.generate_video,
        auto_queue=data.auto_queue,
    )

    await log_event(db, "agent.pipeline_run", actor_type="agent",
                    resource_type="social_post", resource_id=post_id,
                    details={"steps": result.get("steps", []), "run_id": data.run_id})
    await db.commit()

    return {
        "status": "pipeline_complete",
        "post_id": post_id,
        "steps": result.get("steps", []),
        "pipeline_stage": result.get("pipeline_stage"),
        "media_assets": result.get("media_assets", []),
        "note": "Post is queued for your approval. Review in Content Studio before publishing.",
    }


# ── POST /agent/analyze-performance ───────────────────────────────────────────
class PerformanceAnalysisRequest(BaseModel):
    days: int = 30


@router.post("/analyze-performance")
async def analyze_performance(data: PerformanceAnalysisRequest, db: AsyncSession = Depends(get_db)):
    """
    Analyze content pipeline health and return structured decisions.
    The agent calls this to determine whether to continue, pause, or adjust.

    Returns:
      - overall health assessment
      - per-category approval/publish rates
      - specific decisions: pause | adjust | scale | review
      - estimated video generation costs
      - recommended next action
    """
    from app.services.content_agent import analyze_content_performance
    analysis = await analyze_content_performance(db, days=data.days)

    await log_event(db, "agent.analyze_performance", actor_type="agent",
                    details={"days": data.days, "decisions_count": len(analysis.get("decisions", []))})
    await db.commit()

    return analysis


# ── POST /agent/publish-content ───────────────────────────────────────────────
class AgentPublishRequest(BaseModel):
    post_id: str
    platform: Optional[str] = None
    caption_override: Optional[str] = None
    hashtags: Optional[list] = None


@router.post("/publish-content")
async def agent_publish_content(data: AgentPublishRequest, db: AsyncSession = Depends(get_db)):
    """
    Agent-triggered publish. Only works on APPROVED posts.
    The agent should call analyze-performance + check approval before calling this.
    """
    from app.models.content import SocialPost, ApprovalStatus

    q = await db.execute(select(SocialPost).where(SocialPost.id == data.post_id))
    post = q.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")
    if post.approval_status != ApprovalStatus.APPROVED:
        return {
            "status": "blocked",
            "reason": f"Post status is '{post.approval_status}' — only APPROVED posts can be published by the agent",
            "post_id": data.post_id,
        }

    # Delegate to the content router's publish logic
    media_ids = post.media_asset_ids or []
    video_url = None
    for m in reversed(media_ids):
        if m.get("type") in ("video_final", "video_raw") and m.get("url"):
            video_url = m["url"]
            break

    if not video_url:
        return {"status": "blocked", "reason": "No video asset found", "post_id": data.post_id}

    target = data.platform or (post.platform.value if post.platform else None)
    if not target:
        return {"status": "blocked", "reason": "No platform specified", "post_id": data.post_id}

    from app.services.publishers.registry import get_publisher
    from app.services.publishers.base import PublishPayload
    publisher = get_publisher(target)
    payload   = PublishPayload(
        video_url=video_url,
        caption=data.caption_override or post.caption or "",
        platform=target,
        hashtags=data.hashtags,
        post_id=data.post_id,
    )
    result = await publisher.publish(payload)

    if result.success:
        post.approval_status  = ApprovalStatus.PUBLISHED
        post.published_at     = datetime.utcnow()
        post.external_post_id = result.external_post_id
        await db.commit()
        await log_event(db, "agent.published", actor_type="agent",
                        resource_type="social_post", resource_id=data.post_id,
                        details={"platform": target, "external_id": result.external_post_id})
        await db.commit()

    return {
        "success":          result.success,
        "post_id":          data.post_id,
        "platform":         target,
        "external_post_id": result.external_post_id,
        "platform_url":     result.platform_url,
        "error":            result.error,
    }


# ── POST /agent/voice-generate ─────────────────────────────────────────────
@router.post("/voice-generate")
async def voice_generate(data: VoiceGenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate audio via ElevenLabs. Returns base64-encoded MP3 bytes."""
    import base64
    audio_bytes = await generate_audio(data.text, voice_id=data.voice_id)
    await log_event(db, "agent.voice_generate", actor_type="agent",
                    details={"chars": len(data.text), "voice_id": data.voice_id})
    await db.commit()
    return {
        "audio_base64": base64.b64encode(audio_bytes).decode(),
        "mime_type": "audio/mpeg",
        "char_count": len(data.text),
    }


# ── GET /agent/campaign-templates ──────────────────────────────────────────
@router.get("/campaign-templates")
async def get_campaign_templates():
    """
    Returns all pre-built plug-and-play campaign scenarios.
    Agent uses this to show the operator what's available and launch any scenario
    with a single build-campaign call using template_id.
    """
    from app.services.ad_campaign_builder import CAMPAIGN_TEMPLATES
    return {
        "templates": list(CAMPAIGN_TEMPLATES.values()),
        "count": len(CAMPAIGN_TEMPLATES),
        "note": "Pass template_id to /agent/build-campaign to launch any scenario. "
                "avatar/product/market/budget_hint from the template are used as defaults "
                "and can be overridden in the same request.",
    }


# ── POST /agent/build-campaign ─────────────────────────────────────────────
class BuildCampaignRequest(BaseModel):
    """
    Trigger the full 9-step advertising skill chain.

    template_id:          (optional) Pre-built scenario slug — auto-fills avatar/product/market/budget_hint.
                          Get available templates from GET /agent/campaign-templates.
    avatar:               declined_buyer | first_timer | equity_prisoner | realtor_client
    product:              fha | va | dpa | conventional | heloc | dscr | refi
    market:               MD | DC | both
    budget_hint:          low | mid | scale
    proof:                (optional) Real result to weave in — e.g. "Closed $390k FHA in 9 days"
    flyer_id:             (optional) ID of a completed GeneratedFlyer to use as visual creative
    reference_page_slug:  (optional) Existing CampaignPage slug — pulls headline/proof and uses
                          as inspiration context so the new campaign builds on proven copy.
    """
    template_id: Optional[str] = None
    avatar: Optional[str] = None
    product: Optional[str] = None
    proof: Optional[str] = None
    market: str = "MD"
    budget_hint: str = "low"
    flyer_id: Optional[int] = None
    reference_page_slug: Optional[str] = None


@router.post("/build-campaign")
async def build_campaign(data: BuildCampaignRequest, db: AsyncSession = Depends(get_db)):
    """
    Run the full advertising skill chain:
    Avatar → Offer → Awareness → Mechanism → Angles → Creative → Sales Letter → Objections → QA + Facebook Setup

    Returns 3 ad units + sales letter + 3-email sequence + Facebook ad setup block.
    All assets route to the Approval Queue — nothing goes live without human review.

    Use template_id for plug-and-play scenarios. Use reference_page_slug to build
    on an existing sales letter. Use flyer_id to attach a branded visual.
    """
    from app.services.ad_campaign_builder import build_ad_campaign, CAMPAIGN_TEMPLATES
    from app.models.flyer import GeneratedFlyer
    from sqlalchemy import select as _select

    # Require either template_id or avatar+product
    avatar  = data.avatar  or (CAMPAIGN_TEMPLATES.get(data.template_id or "", {}).get("avatar"))
    product = data.product or (CAMPAIGN_TEMPLATES.get(data.template_id or "", {}).get("product"))
    if not avatar or not product:
        raise HTTPException(status_code=422, detail="Provide template_id OR both avatar and product.")

    flyer_image_url = None
    if data.flyer_id:
        flyer = (await db.execute(
            _select(GeneratedFlyer).where(
                GeneratedFlyer.id == data.flyer_id,
                GeneratedFlyer.status == "complete",
            )
        )).scalar_one_or_none()
        if flyer:
            flyer_image_url = flyer.flyer_image_url

    result = await build_ad_campaign(
        db=db,
        avatar=avatar,
        product=product,
        proof=data.proof,
        market=data.market,
        budget_hint=data.budget_hint,
        flyer_image_url=flyer_image_url,
        template_id=data.template_id,
        reference_page_slug=data.reference_page_slug,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Attach the Facebook targeting spec from the template if one was used
    if data.template_id and data.template_id in CAMPAIGN_TEMPLATES:
        result["facebook_setup"] = CAMPAIGN_TEMPLATES[data.template_id].get("facebook", {})
        result["template_used"] = data.template_id

    return result


class FlyerToCampaignRequest(BaseModel):
    """
    Full autonomous chain: build a flyer → wait for completion → build campaign with it.
    Agent calls this when it wants to create a campaign with a fresh visual creative.

    Pass template_id to use a pre-built scenario (avatar/product/market/budget auto-filled).
    Or pass avatar + product manually. template_id takes precedence for defaults.
    """
    # Flyer params
    use_case: str = "purchase"
    flyer_format: str = "social_square"
    headline: str
    subheadline: Optional[str] = ""
    cta_text: Optional[str] = "Book a Free Call →"
    style_preset: Optional[str] = "suit_headshot"
    skip_ai: bool = False
    # Campaign params — template_id fills defaults; avatar/product override if provided
    template_id: Optional[str] = None
    avatar: Optional[str] = None
    product: Optional[str] = None
    proof: Optional[str] = None
    market: str = "MD"
    budget_hint: str = "low"
    reference_page_slug: Optional[str] = None


@router.post("/flyer-to-campaign")
async def flyer_to_campaign(data: FlyerToCampaignRequest, db: AsyncSession = Depends(get_db)):
    """
    Agent full-chain: generate a branded flyer → build ad campaign around it.

    Step 1: Builds a flyer synchronously (avatar generation + bg removal + compositing).
    Step 2: Passes the flyer URL into build_ad_campaign so all copy is written around the visual.

    Returns: campaign result + flyer_id + flyer_image_url.
    Everything routes to Approval Queue — nothing goes live without human review.
    """
    from app.models.flyer import GeneratedFlyer, ReferencePhoto
    from app.services.avatar_generator import generate_avatar, remove_background, get_style_preset
    from app.services.flyer_builder import build_flyer_async
    from app.services.ad_campaign_builder import build_ad_campaign, CAMPAIGN_TEMPLATES

    # ── Step 1: Flyer ─────────────────────────────────────────────────────────
    ref = (await db.execute(select(ReferencePhoto).limit(1))).scalar_one_or_none()
    if not ref or not ref.file_path:
        raise HTTPException(400, "No reference photo. POST /flyers/reference-photo first.")

    style_prompt = get_style_preset(data.style_preset or "suit_headshot")

    avatar_result = await generate_avatar(
        reference_photo_path=ref.file_path,
        style_prompt=style_prompt,
        output_size={"social_square": "square_hd", "story": "story",
                     "facebook_banner": "landscape", "wide_banner": "landscape"}.get(data.flyer_format, "square_hd"),
    )

    if not avatar_result.success:
        raise HTTPException(500, f"Avatar generation failed: {avatar_result.error}")

    # Background removal
    bg_path, bg_url = await remove_background(avatar_result.image_path)

    # Composite flyer
    flyer_result = await build_flyer_async(
        avatar_image_path=bg_path,
        avatar_image_url=bg_url,
        headline=data.headline,
        subheadline=data.subheadline or "",
        cta_text=data.cta_text or "",
        flyer_format=data.flyer_format,
    )

    # Save flyer record
    flyer = GeneratedFlyer(
        use_case=data.use_case,
        flyer_format=data.flyer_format,
        avatar_style=style_prompt,
        headline=data.headline,
        subheadline=data.subheadline,
        cta_text=data.cta_text,
        avatar_image_path=bg_path,
        avatar_image_url=bg_url,
        flyer_image_path=flyer_result["path"],
        flyer_image_url=flyer_result["url"],
        provider=avatar_result.provider,
        status="complete",
        created_by="agent",
    )
    db.add(flyer)
    await db.flush()
    flyer_id = flyer.id

    # ── Step 2: Campaign ──────────────────────────────────────────────────────
    # Resolve avatar/product from template defaults if not explicitly provided
    tmpl = CAMPAIGN_TEMPLATES.get(data.template_id or "", {})
    resolved_avatar  = data.avatar   or tmpl.get("avatar")
    resolved_product = data.product  or tmpl.get("product")
    resolved_market  = tmpl.get("market", data.market) if tmpl else data.market
    resolved_budget  = tmpl.get("budget_hint", data.budget_hint) if tmpl else data.budget_hint

    if not resolved_avatar or not resolved_product:
        raise HTTPException(
            status_code=422,
            detail="Provide template_id OR both avatar and product.",
        )

    campaign_result = await build_ad_campaign(
        db=db,
        avatar=resolved_avatar,
        product=resolved_product,
        proof=data.proof,
        market=resolved_market,
        budget_hint=resolved_budget,
        flyer_image_url=flyer_result["url"],
        template_id=data.template_id,
        reference_page_slug=data.reference_page_slug,
    )

    await db.commit()

    if "error" in campaign_result:
        raise HTTPException(500, campaign_result["error"])

    # Attach facebook_setup from template if available
    if data.template_id and data.template_id in CAMPAIGN_TEMPLATES:
        campaign_result["facebook_setup"] = CAMPAIGN_TEMPLATES[data.template_id].get("facebook", {})

    return {
        **campaign_result,
        "flyer_id": flyer_id,
        "flyer_image_url": flyer_result["url"],
        "avatar_provider": avatar_result.provider,
        "template_used": data.template_id,
    }


# ══════════════════════════════════════════════════════════════════════════════
# AGENT MEMORY — persistent logs + ask-queue for autonomous Clawdbot operation
# ══════════════════════════════════════════════════════════════════════════════

# ── POST /agent/memory — write a run log ─────────────────────────────────────
class MemoryLogRequest(BaseModel):
    run_id: str
    run_type: str                                    # daily_check | weekly_audit | campaign_build | lead_review | custom
    summary: str                                     # plain-English what the agent did
    actions_taken: list = []                         # [{action, result, timestamp}]
    results: dict = {}                               # key metrics for this run
    needs_from_operator: list = []                   # items the agent couldn't resolve
    status: str = "completed"                        # completed | needs_input | failed


@router.post("/memory")
async def write_memory(data: MemoryLogRequest, db: AsyncSession = Depends(get_db)):
    """
    Agent writes a run log after completing work.
    This is the agent's persistent memory — it reads this before each new run
    to know what was done, what was skipped, and what's still pending.
    """
    log_entry = AgentMemoryLog(
        run_id=data.run_id,
        run_type=data.run_type,
        summary=data.summary,
        actions_taken=data.actions_taken,
        results=data.results,
        needs_from_operator=data.needs_from_operator,
        status=data.status,
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)

    await log_event(db, "agent.memory_written", actor_type="agent",
                    details={"run_id": data.run_id, "run_type": data.run_type, "status": data.status})
    await db.commit()

    return {"id": log_entry.id, "run_id": log_entry.run_id, "status": "logged"}


# ── GET /agent/memory — read last N run logs ─────────────────────────────────
@router.get("/memory")
async def read_memory(limit: int = 10, run_type: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """
    Agent reads its own run history before starting a new session.
    Use this to know: what was done last time, what's still pending, what to skip.
    """
    from sqlalchemy import desc
    q = select(AgentMemoryLog).order_by(desc(AgentMemoryLog.created_at)).limit(limit)
    if run_type:
        q = q.where(AgentMemoryLog.run_type == run_type)
    rows = (await db.execute(q)).scalars().all()

    return {
        "count": len(rows),
        "logs": [
            {
                "id": r.id,
                "run_id": r.run_id,
                "run_type": r.run_type,
                "summary": r.summary,
                "actions_taken": r.actions_taken,
                "results": r.results,
                "needs_from_operator": r.needs_from_operator,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


# ── POST /agent/ask — post a question/request to the operator ────────────────
class AgentAskRequest(BaseModel):
    question: str
    context: str = ""                                # why the agent needs this
    urgency: str = "normal"                          # low | normal | high
    category: str = "general"                        # budget | content | access | decision | other


@router.post("/ask")
async def agent_ask(data: AgentAskRequest, db: AsyncSession = Depends(get_db)):
    """
    Agent posts a question or request to the operator.
    Fires a webhook to AGENT_WEBHOOK_URL so the operator gets notified immediately.
    Stored in DB — operator can view and resolve from admin app.
    """
    from app.config import settings

    ask = AgentAsk(
        question=data.question,
        context=data.context,
        urgency=data.urgency,
        category=data.category,
    )
    db.add(ask)
    await db.commit()
    await db.refresh(ask)

    # Fire webhook notification if configured
    if settings.agent_webhook_url:
        try:
            payload = {
                "event": "agent_ask",
                "id": ask.id,
                "urgency": ask.urgency,
                "category": ask.category,
                "question": ask.question,
                "context": ask.context,
            }
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(settings.agent_webhook_url, json=payload)
        except Exception:
            pass  # Never block agent operation because webhook failed

    await log_event(db, "agent.ask_posted", actor_type="agent",
                    details={"ask_id": ask.id, "urgency": data.urgency, "category": data.category})
    await db.commit()

    return {"ask_id": ask.id, "status": "posted", "note": "Operator will be notified via webhook."}


# ── GET /agent/brief — pipeline snapshot for autonomous decision-making ──────
@router.get("/brief")
async def get_brief(db: AsyncSession = Depends(get_db)):
    """
    Returns a current pipeline snapshot so the agent can decide what to do next.
    Read this at the start of every autonomous run.
    """
    from sqlalchemy import func, desc
    from app.models.lead import LeadIntake
    from app.models.contact import Contact
    from app.models.campaign import CampaignPage
    from app.config import settings

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Leads
    leads_today_q   = await db.execute(select(func.count()).select_from(LeadIntake).where(LeadIntake.created_at >= today_start))
    leads_total_q   = await db.execute(select(func.count()).select_from(LeadIntake))
    leads_today     = leads_today_q.scalar() or 0
    leads_total     = leads_total_q.scalar() or 0

    # Approvals pending
    pending_q       = await db.execute(select(func.count()).select_from(ApprovalQueue).where(ApprovalQueue.status == "pending"))
    pending_count   = pending_q.scalar() or 0

    # Campaign pages
    unpublished_q   = await db.execute(select(func.count()).select_from(CampaignPage).where(CampaignPage.is_published == False))
    published_q     = await db.execute(select(func.count()).select_from(CampaignPage).where(CampaignPage.is_published == True))
    unpublished     = unpublished_q.scalar() or 0
    published       = published_q.scalar() or 0

    # Open asks from agent
    open_asks_q     = await db.execute(select(func.count()).select_from(AgentAsk).where(AgentAsk.is_resolved == False))
    open_asks       = open_asks_q.scalar() or 0

    # Last memory log
    last_log_q      = await db.execute(select(AgentMemoryLog).order_by(desc(AgentMemoryLog.created_at)).limit(1))
    last_log        = last_log_q.scalar_one_or_none()

    # Unresolved asks (most urgent first)
    asks_q          = await db.execute(
        select(AgentAsk)
        .where(AgentAsk.is_resolved == False)
        .order_by(desc(AgentAsk.created_at))
        .limit(5)
    )
    pending_asks    = asks_q.scalars().all()

    return {
        "as_of": now.isoformat(),
        "operator": settings.banker_name,
        "pipeline": {
            "leads_today": leads_today,
            "leads_total": leads_total,
            "approvals_pending": pending_count,
            "campaign_pages_unpublished": unpublished,
            "campaign_pages_published": published,
        },
        "agent_state": {
            "open_asks": open_asks,
            "last_run": {
                "run_id": last_log.run_id if last_log else None,
                "run_type": last_log.run_type if last_log else None,
                "summary": last_log.summary if last_log else None,
                "status": last_log.status if last_log else None,
                "at": last_log.created_at.isoformat() if last_log and last_log.created_at else None,
            },
        },
        "pending_asks": [
            {
                "id": a.id,
                "urgency": a.urgency,
                "category": a.category,
                "question": a.question,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in pending_asks
        ],
        "suggested_actions": _suggest_actions(leads_today, pending_count, unpublished, open_asks),
    }


# ── POST /agent/build-flyer ──────────────────────────────────────────────────
class AgentFlyerRequest(BaseModel):
    """
    Agent triggers a flyer build autonomously.

    use_case:       purchase | dpa | refi | realtor | generic
    flyer_format:   social_square | facebook_banner | story | wide_banner
    style_preset:   suit_headshot | casual_expert | outdoor_realtor | dark_brand | community
    headline, subheadline, cta_text: copy for the flyer
    skip_ai:        True = use reference photo directly (faster, no AI credits used)
    """
    use_case: str = "purchase"
    flyer_format: str = "social_square"
    headline: str
    subheadline: Optional[str] = ""
    cta_text: Optional[str] = "Book a Free Call →"
    style_preset: Optional[str] = "suit_headshot"
    style_prompt_override: Optional[str] = None
    skip_ai: bool = False


@router.post("/build-flyer")
async def agent_build_flyer(data: AgentFlyerRequest, db: AsyncSession = Depends(get_db)):
    """
    Agent-triggered flyer generation pipeline.
    Runs synchronously (blocks until complete) so the agent gets the result immediately.
    Returns flyer_id, status, and URLs when done.
    """
    from app.models.flyer import GeneratedFlyer, ReferencePhoto
    from app.services.avatar_generator import generate_avatar, get_style_preset, _passthrough
    from app.services.flyer_builder import build_flyer
    from sqlalchemy import select

    # Check reference photo
    ref = (await db.execute(select(ReferencePhoto).limit(1))).scalar_one_or_none()
    if not ref or not ref.file_path:
        raise HTTPException(400, "No reference photo uploaded. Have the operator POST /flyers/reference-photo first.")

    style_prompt = data.style_prompt_override or get_style_preset(data.style_preset or "suit_headshot")

    # Create DB record
    flyer = GeneratedFlyer(
        use_case=data.use_case,
        flyer_format=data.flyer_format,
        avatar_style=style_prompt,
        headline=data.headline,
        subheadline=data.subheadline,
        cta_text=data.cta_text,
        status="pending",
        created_by="agent",
    )
    db.add(flyer)
    await db.flush()
    flyer_id = flyer.id

    # Avatar generation
    if data.skip_ai:
        avatar_result = await _passthrough(ref.file_path)
    else:
        avatar_result = await generate_avatar(
            reference_photo_path=ref.file_path,
            style_prompt=style_prompt,
            output_size={"social_square": "square_hd", "story": "story",
                         "facebook_banner": "landscape", "wide_banner": "landscape"}.get(data.flyer_format, "square_hd"),
        )

    if not avatar_result.success:
        flyer.status = "failed"
        flyer.error = avatar_result.error
        await db.commit()
        raise HTTPException(500, f"Avatar generation failed: {avatar_result.error}")

    flyer.avatar_image_path = avatar_result.image_path
    flyer.avatar_image_url = avatar_result.image_url
    flyer.provider = avatar_result.provider
    flyer.status = "avatar_ready"
    await db.flush()

    # Flyer compositing
    flyer_result = build_flyer(
        avatar_image_path=avatar_result.image_path,
        headline=data.headline,
        subheadline=data.subheadline or "",
        cta_text=data.cta_text or "",
        flyer_format=data.flyer_format,
    )

    flyer.flyer_image_path = flyer_result["path"]
    flyer.flyer_image_url = flyer_result["url"]
    flyer.status = "complete"
    await db.commit()

    await log_event(db, "agent.flyer_built", actor_type="agent",
                    details={"flyer_id": flyer_id, "format": data.flyer_format,
                             "use_case": data.use_case, "provider": avatar_result.provider})
    await db.commit()

    return {
        "flyer_id": flyer_id,
        "status": "complete",
        "flyer_url": flyer_result["url"],
        "avatar_url": avatar_result.image_url,
        "provider": avatar_result.provider,
        "format": data.flyer_format,
    }


def _suggest_actions(leads_today: int, pending: int, unpublished: int, open_asks: int) -> list:
    """Give the agent a prioritized action list based on current pipeline state."""
    actions = []
    if open_asks > 0:
        actions.append({"priority": 1, "action": "check_asks", "reason": f"{open_asks} unresolved question(s) from a previous run — operator may have responded."})
    if pending > 5:
        actions.append({"priority": 2, "action": "review_approvals", "reason": f"{pending} items pending approval — queue may be backing up."})
    if leads_today == 0:
        actions.append({"priority": 3, "action": "build_campaign", "reason": "No leads today yet — consider building a new campaign to drive intake."})
    if unpublished > 0:
        actions.append({"priority": 4, "action": "notify_operator", "reason": f"{unpublished} campaign page(s) built but not published — flag for operator review."})
    if not actions:
        actions.append({"priority": 5, "action": "monitor", "reason": "Pipeline looks healthy. Continue monitoring."})
    return actions


# ══════════════════════════════════════════════════════════════════════════════
# GET /agent/diagnose — full system integration check + punch list
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/diagnose")
async def diagnose(db: AsyncSession = Depends(get_db)):
    """
    Full system diagnostic. Tests every integration and returns a punch list.
    Clawdbot calls this to answer "what's broken?" or "what's missing?"

    Returns a structured list of checks with status: ok | warn | error
    and a plain-English summary for the operator.
    """
    import os
    from app.models.flyer import ReferencePhoto

    checks = []

    def check(name: str, status: str, detail: str, fix: str = ""):
        checks.append({"name": name, "status": status, "detail": detail, "fix": fix or ""})

    # ── AI / Content ──────────────────────────────────────────────────────────
    openai_key = settings.openai_api_key
    check("OpenAI",
          "ok" if openai_key else "error",
          "API key set" if openai_key else "OPENAI_API_KEY not set",
          "" if openai_key else "Add OPENAI_API_KEY to .env")

    check("Avatar provider",
          "ok",
          f"AVATAR_PROVIDER={settings.avatar_provider}. "
          + ("fal.ai key set" if settings.fal_api_key else "fal.ai key not set (using OpenAI or passthrough)"))

    removebg = os.getenv("REMOVE_BG_API_KEY", "")
    try:
        import rembg as _r
        bg_status, bg_detail = "ok", "rembg installed (local, free)"
    except ImportError:
        if removebg:
            bg_status, bg_detail = "ok", "rembg not installed but remove.bg API key set"
        else:
            bg_status, bg_detail = "warn", "No background removal available (rembg not installed, REMOVE_BG_API_KEY not set)"
    check("Background removal", bg_status, bg_detail,
          "" if bg_status == "ok" else "pip install rembg  OR  set REMOVE_BG_API_KEY in .env")

    check("ElevenLabs voice",
          "ok" if settings.elevenlabs_api_key else "warn",
          "API key set" if settings.elevenlabs_api_key else "ELEVENLABS_API_KEY not set — voice generation disabled",
          "" if settings.elevenlabs_api_key else "Set ELEVENLABS_API_KEY in .env")

    heygen_key = os.getenv("HEYGEN_API_KEY", "")
    check("Video (HeyGen)",
          "ok" if (settings.campaign_video_provider != "mock" and heygen_key) else "warn",
          f"CAMPAIGN_VIDEO_PROVIDER={settings.campaign_video_provider}" + (" — key set" if heygen_key else " — HEYGEN_API_KEY not set"),
          "" if settings.campaign_video_provider != "mock" else "Set CAMPAIGN_VIDEO_PROVIDER=heygen + HEYGEN_API_KEY to enable real video")

    # ── Flyer ─────────────────────────────────────────────────────────────────
    ref = (await db.execute(select(ReferencePhoto).limit(1))).scalar_one_or_none()
    check("Reference photo",
          "ok" if (ref and ref.file_path) else "error",
          f"Uploaded: {ref.file_url}" if (ref and ref.file_path) else "No face photo uploaded",
          "" if (ref and ref.file_path) else "POST /api/v1/flyers/reference-photo to upload a face photo")

    check("Flyer composer",
          "ok",
          f"FLYER_COMPOSER={settings.flyer_composer}"
          + (" (Bannerbear templates configured)" if settings.flyer_composer == "bannerbear" and settings.bannerbear_api_key else
             " (Bannerbear key missing — using Pillow fallback)" if settings.flyer_composer == "bannerbear" else
             " (Pillow — local, free)"))

    # ── Email ─────────────────────────────────────────────────────────────────
    email_provider = settings.campaign_email_provider
    if email_provider == "mock":
        check("Email sending", "warn", "CAMPAIGN_EMAIL_PROVIDER=mock — emails are logged only, not sent",
              "Set CAMPAIGN_EMAIL_PROVIDER=gmail and configure SMTP_USER/SMTP_PASSWORD")
    elif email_provider == "gmail":
        has_creds = bool(settings.smtp_user and settings.smtp_password)
        check("Email sending",
              "ok" if has_creds else "error",
              f"Gmail SMTP — {'credentials set' if has_creds else 'SMTP_USER or SMTP_PASSWORD missing'}",
              "" if has_creds else "Set SMTP_USER and SMTP_PASSWORD (Gmail App Password) in .env")
    else:
        check("Email sending", "ok", f"CAMPAIGN_EMAIL_PROVIDER={email_provider}")

    # ── SMS ───────────────────────────────────────────────────────────────────
    sms_provider = settings.campaign_sms_provider
    check("SMS sending",
          "warn" if sms_provider == "mock" else "ok",
          f"CAMPAIGN_SMS_PROVIDER={sms_provider}" + (" — SMS not sending" if sms_provider == "mock" else ""),
          "" if sms_provider != "mock" else "Set CAMPAIGN_SMS_PROVIDER=signalwire or twilio (TCPA consent required first)")

    # ── Direct mail ───────────────────────────────────────────────────────────
    mail_provider = settings.campaign_direct_mail_provider
    check("Direct mail",
          "warn" if mail_provider == "mock" else "ok",
          f"CAMPAIGN_DIRECT_MAIL_PROVIDER={mail_provider}",
          "" if mail_provider != "mock" else "Set CAMPAIGN_DIRECT_MAIL_PROVIDER=lob + LOB_API_KEY for live mail")

    # ── Social publishing ─────────────────────────────────────────────────────
    publish_mode = settings.content_publish_mode
    check("Social publishing",
          "warn" if publish_mode == "mock" else "ok",
          f"CONTENT_PUBLISH_MODE={publish_mode}" + (" — posts not going live" if publish_mode == "mock" else ""),
          "" if publish_mode != "mock" else "Set CONTENT_PUBLISH_MODE=live and configure social API tokens")

    # ── Booking / Cal.com ─────────────────────────────────────────────────────
    check("Booking link",
          "ok" if settings.calcom_link else "warn",
          f"Cal.com: {settings.calcom_link}" if settings.calcom_link else "CALCOM_LINK not set",
          "" if settings.calcom_link else "Set CALCOM_LINK in .env")

    # ── Property data ─────────────────────────────────────────────────────────
    prop_provider = settings.campaign_property_provider
    check("Property data (ATTOM)",
          "warn" if prop_provider == "mock" else "ok",
          f"CAMPAIGN_PROPERTY_PROVIDER={prop_provider}",
          "" if prop_provider != "mock" else "Set CAMPAIGN_PROPERTY_PROVIDER=attom + ATTOM_API_KEY for live property data")

    # ── Agent webhook ─────────────────────────────────────────────────────────
    check("Agent webhook",
          "ok" if settings.agent_webhook_url else "warn",
          f"AGENT_WEBHOOK_URL={'set' if settings.agent_webhook_url else 'not set — ask notifications will not push to you'}",
          "" if settings.agent_webhook_url else "Set AGENT_WEBHOOK_URL to receive push notifications when agent asks you something")

    # ── Summary ───────────────────────────────────────────────────────────────
    errors   = [c for c in checks if c["status"] == "error"]
    warnings = [c for c in checks if c["status"] == "warn"]
    ok_count = len([c for c in checks if c["status"] == "ok"])

    if errors:
        overall = "degraded"
        summary = f"{len(errors)} critical issue(s) blocking key features. {len(warnings)} warning(s). {ok_count} checks passing."
    elif warnings:
        overall = "partial"
        summary = f"Core features working. {len(warnings)} integration(s) in mock/disabled mode. {ok_count} checks passing."
    else:
        overall = "healthy"
        summary = f"All {ok_count} checks passing. System fully operational."

    return {
        "overall": overall,
        "summary": summary,
        "checks": checks,
        "counts": {"ok": ok_count, "warn": len(warnings), "error": len(errors)},
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /agent/system-prompt — rendered prompt with all .env values injected
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/system-prompt")
async def get_system_prompt(target: str = "clawdbot"):
    """
    Returns the agent system prompt with all {PLACEHOLDER} values filled in
    from the current .env settings. Copy-paste ready.

    target: clawdbot (default) | elevenlabs
    """
    from app.config import settings
    from pathlib import Path

    target = target.lower()
    skill_dir = Path(__file__).parent.parent / "agents" / "skills"

    filename_map = {
        "clawdbot":   "CLAWDBOT_SYSTEM_PROMPT.md",
        "elevenlabs": "ELEVENLABS_AGENT_PROMPT.md",
    }
    filename = filename_map.get(target)
    if not filename:
        raise HTTPException(400, f"Unknown target '{target}'. Valid: {list(filename_map.keys())}")

    prompt_path = skill_dir / filename
    if not prompt_path.exists():
        raise HTTPException(404, f"Prompt file not found: {prompt_path}")

    raw = prompt_path.read_text()

    # Strip comment header lines (lines starting with #) for clean output
    lines = raw.splitlines()
    content_lines = []
    header_done = False
    for line in lines:
        if not header_done and line.startswith("#"):
            continue   # skip comment header
        else:
            header_done = True
            content_lines.append(line)
    template = "\n".join(content_lines).strip()

    # Inject all .env-driven values
    rendered = (
        template
        .replace("{OPERATOR_NAME}",    settings.banker_name)
        .replace("{BANKER_NMLS}",      settings.banker_nmls)
        .replace("{SERVICE_STATES}",   settings.service_states)
        .replace("{BACKEND_URL}",      settings.backend_url)
        .replace("{PUBLIC_SITE_URL}",  settings.public_site_url)
        .replace("{ADMIN_APP_URL}",    settings.admin_app_url)
        .replace("{AGENT_API_KEY}",    settings.agent_api_key)
        .replace("{AGENT_PERSONA_NAME}", settings.agent_persona_name)
        .replace("{APP_NAME}",         settings.app_name)
        .replace("{CALCOM_LINK}",      settings.calcom_link)
        .replace("{APP_1003_URL}",     settings.app_1003_url)
        .replace("{ZILLOW_URL}",       settings.zillow_url)
    )

    return {
        "target": target,
        "rendered": rendered,
        "note": "Copy the 'rendered' field verbatim into your agent config. All placeholders have been filled from your .env.",
        "placeholders_filled": {
            "OPERATOR_NAME":     settings.banker_name,
            "BANKER_NMLS":       settings.banker_nmls,
            "SERVICE_STATES":    settings.service_states,
            "BACKEND_URL":       settings.backend_url,
            "AGENT_API_KEY":     f"{settings.agent_api_key[:8]}...{settings.agent_api_key[-4:]}",
            "AGENT_PERSONA_NAME": settings.agent_persona_name,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# AGENT WRITE SURFACE — full CRUD for the orchestrator
# All write actions are logged to the audit trail.
# ══════════════════════════════════════════════════════════════════════════════

from app.models.contact import ContactType, LeadScore as ContactLeadScore
from app.models.hub import Listing, ListingStatus, RateSnapshot, DpaProgram, DpaType, RateAlert
from app.models.lead import (
    LoanInterestType, CreditScoreRange, IncomeRange, Timeline, PropertyGoal
)
from datetime import date


# ── Lookup / search ──────────────────────────────────────────────────────────

@router.get("/lookup")
async def agent_lookup(
    q: str,
    entity: str = "contact",   # contact | lead | listing | campaign | product
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    Quick search across any entity type by name, email, address, or keyword.
    Returns lightweight records the agent can use to get IDs before writing.
    """
    from sqlalchemy import or_
    from app.models.campaign import Campaign as CampaignModel
    from app.models.product import Product as ProductModel

    entity = entity.lower()

    if entity == "contact":
        stmt = select(Contact).where(
            or_(
                Contact.first_name.ilike(f"%{q}%"),
                Contact.last_name.ilike(f"%{q}%"),
                Contact.email.ilike(f"%{q}%"),
                Contact.company.ilike(f"%{q}%"),
                Contact.phone.ilike(f"%{q}%"),
            )
        ).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [{"id": r.id, "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
                 "email": r.email, "phone": r.phone, "type": r.contact_type,
                 "company": r.company, "city": r.city, "state": r.state} for r in rows]

    if entity == "lead":
        stmt = select(LeadIntake).where(
            or_(
                LeadIntake.first_name.ilike(f"%{q}%"),
                LeadIntake.last_name.ilike(f"%{q}%"),
                LeadIntake.email.ilike(f"%{q}%"),
                LeadIntake.phone.ilike(f"%{q}%"),
            )
        ).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [{"id": r.id, "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
                 "email": r.email, "phone": r.phone, "pipeline_status": r.pipeline_status,
                 "loan_purpose": r.loan_purpose} for r in rows]

    if entity == "listing":
        stmt = select(Listing).where(
            or_(
                Listing.address.ilike(f"%{q}%"),
                Listing.city.ilike(f"%{q}%"),
                Listing.zip_code.ilike(f"%{q}%"),
            )
        ).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [{"id": r.id, "address": r.address, "city": r.city, "state": r.state,
                 "list_price": r.list_price, "status": r.status} for r in rows]

    if entity == "campaign":
        stmt = select(CampaignModel).where(
            CampaignModel.name.ilike(f"%{q}%")
        ).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [{"id": r.id, "name": r.name, "status": r.status,
                 "campaign_type": r.campaign_type, "channel": r.channel} for r in rows]

    if entity == "product":
        stmt = select(ProductModel).where(
            or_(
                ProductModel.name.ilike(f"%{q}%"),
                ProductModel.product_type.ilike(f"%{q}%"),
            )
        ).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [{"id": r.id, "name": r.name, "product_type": r.product_type,
                 "is_active": r.is_active} for r in rows]

    if entity == "dpa":
        from app.models.hub import DpaProgram as DpaProgramModel
        stmt = select(DpaProgramModel).where(
            or_(
                DpaProgramModel.program_name.ilike(f"%{q}%"),
                DpaProgramModel.county.ilike(f"%{q}%"),
                DpaProgramModel.state.ilike(f"%{q}%"),
                DpaProgramModel.administering_agency.ilike(f"%{q}%"),
            )
        ).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [{"id": r.id, "program_name": r.program_name, "state": r.state,
                 "county": r.county, "dpa_type": r.dpa_type,
                 "assistance_amount": r.assistance_amount, "is_active": r.is_active} for r in rows]

    raise HTTPException(400, f"Unknown entity '{entity}'. Valid: contact, lead, listing, campaign, product, dpa")


# ── Contact writes ───────────────────────────────────────────────────────────

class AgentContactWrite(BaseModel):
    first_name: Optional[str] = None
    last_name:  Optional[str] = None
    email:      Optional[str] = None
    phone:      Optional[str] = None
    company:    Optional[str] = None
    role_title: Optional[str] = None
    city:       Optional[str] = None
    state:      Optional[str] = None
    contact_type: str = "consumer"   # consumer | realtor | title_agent | investor | ...
    source:     Optional[str] = "agent"
    notes:      Optional[str] = None
    consent_email: bool = False
    consent_sms:   bool = False
    consent_call:  bool = False


@router.post("/write/contact", status_code=201)
async def agent_create_contact(data: AgentContactWrite, db: AsyncSession = Depends(get_db)):
    """Create a new contact (any type — realtor, consumer, investor, etc.)."""
    try:
        ct = ContactType(data.contact_type)
    except ValueError:
        raise HTTPException(400, f"Invalid contact_type '{data.contact_type}'")

    contact = Contact(
        first_name=data.first_name, last_name=data.last_name,
        email=data.email, phone=data.phone, company=data.company,
        role_title=data.role_title, city=data.city, state=data.state,
        contact_type=ct, source=data.source, notes=data.notes,
        consent_email=data.consent_email, consent_sms=data.consent_sms,
        consent_call=data.consent_call,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    await log_event(db, "agent.contact.created", actor_type="agent",
                    resource_type="contact", resource_id=contact.id,
                    details={"name": f"{data.first_name} {data.last_name}", "type": data.contact_type})
    return {"id": contact.id, "name": f"{contact.first_name or ''} {contact.last_name or ''}".strip(),
            "contact_type": contact.contact_type, "email": contact.email}


class AgentContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name:  Optional[str] = None
    email:      Optional[str] = None
    phone:      Optional[str] = None
    company:    Optional[str] = None
    role_title: Optional[str] = None
    city:       Optional[str] = None
    state:      Optional[str] = None
    contact_type: Optional[str] = None
    notes:      Optional[str] = None
    source:     Optional[str] = None
    lead_score: Optional[str] = None   # hot | warm | long_term | bad_fit | unscored
    consent_email: Optional[bool] = None
    consent_sms:   Optional[bool] = None
    consent_call:  Optional[bool] = None


@router.patch("/write/contact/{contact_id}")
async def agent_update_contact(contact_id: str, data: AgentContactUpdate, db: AsyncSession = Depends(get_db)):
    """Update any field on an existing contact."""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, f"Contact {contact_id} not found")

    for field, val in data.model_dump(exclude_none=True).items():
        if field == "contact_type":
            try:
                val = ContactType(val)
            except ValueError:
                raise HTTPException(400, f"Invalid contact_type '{val}'")
        if field == "lead_score":
            try:
                val = ContactLeadScore(val)
            except ValueError:
                raise HTTPException(400, f"Invalid lead_score '{val}'")
        setattr(contact, field, val)

    await db.commit()
    await log_event(db, "agent.contact.updated", actor_type="agent",
                    resource_type="contact", resource_id=contact_id,
                    details=data.model_dump(exclude_none=True))
    return {"id": contact.id, "updated": True}


# ── Lead writes ───────────────────────────────────────────────────────────────

class AgentLeadUpdate(BaseModel):
    # Pipeline
    pipeline_status:    Optional[str] = None   # new|contacted|appointment_set|pre_approved|closed|lost
    notes:              Optional[str] = None   # appended with timestamp to existing notes
    agent_notes:        Optional[str] = None   # alias for notes
    # Identity corrections (e.g. typo in phone/email from form)
    first_name:         Optional[str] = None
    last_name:          Optional[str] = None
    email:              Optional[str] = None
    phone:              Optional[str] = None
    # Location
    state:              Optional[str] = None
    city:               Optional[str] = None
    county:             Optional[str] = None
    # Loan context
    loan_interest_type: Optional[str] = None   # purchase|refinance|heloc|fha|va|usda|conventional|dscr_investor|dpa
    target_price:       Optional[float] = None
    property_goal:      Optional[str] = None   # primary_residence|investment|vacation|refinance_existing
    # Qualification info
    credit_score_range: Optional[str] = None   # below_580|580_619|620_659|660_699|700_739|740_plus|unknown
    income_range:       Optional[str] = None   # below_30k|30k_50k|50k_75k|75k_100k|100k_150k|150k_plus|unknown
    timeline:           Optional[str] = None   # asap|within_30_days|within_90_days|within_6_months|within_1_year|just_exploring
    cash_available:     Optional[str] = None   # freeform e.g. "$15,000"


@router.patch("/write/lead/{lead_id}")
async def agent_update_lead(lead_id: str, data: AgentLeadUpdate, db: AsyncSession = Depends(get_db)):
    """Update any field on a lead. Notes are appended (timestamped) not replaced."""
    result = await db.execute(select(LeadIntake).where(LeadIntake.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")

    valid_statuses = {"new", "contacted", "appointment_set", "pre_approved", "closed", "lost"}
    if data.pipeline_status and data.pipeline_status not in valid_statuses:
        raise HTTPException(400, f"Invalid pipeline_status. Valid: {valid_statuses}")

    # Simple string/float fields — set directly
    for field in ("first_name", "last_name", "email", "phone",
                  "state", "city", "county", "target_price", "cash_available"):
        val = getattr(data, field)
        if val is not None:
            setattr(lead, field, val)

    if data.pipeline_status:
        lead.pipeline_status = data.pipeline_status

    # Enum fields — validate before setting
    if data.loan_interest_type:
        try:
            lead.loan_interest_type = LoanInterestType(data.loan_interest_type)
        except ValueError:
            raise HTTPException(400, f"Invalid loan_interest_type '{data.loan_interest_type}'")
    if data.property_goal:
        try:
            lead.property_goal = PropertyGoal(data.property_goal)
        except ValueError:
            raise HTTPException(400, f"Invalid property_goal '{data.property_goal}'")
    if data.credit_score_range:
        try:
            lead.credit_score_range = CreditScoreRange(data.credit_score_range)
        except ValueError:
            raise HTTPException(400, f"Invalid credit_score_range '{data.credit_score_range}'")
    if data.income_range:
        try:
            lead.income_range = IncomeRange(data.income_range)
        except ValueError:
            raise HTTPException(400, f"Invalid income_range '{data.income_range}'")
    if data.timeline:
        try:
            lead.timeline = Timeline(data.timeline)
        except ValueError:
            raise HTTPException(400, f"Invalid timeline '{data.timeline}'")

    # Notes: append with timestamp so history is preserved
    note_text = data.notes or data.agent_notes
    if note_text:
        existing = lead.notes or ""
        lead.notes = f"{existing}\n[Agent {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {note_text}".strip()

    await db.commit()
    await log_event(db, "agent.lead.updated", actor_type="agent",
                    resource_type="lead", resource_id=lead_id,
                    details=data.model_dump(exclude_none=True))
    return {"id": lead.id, "pipeline_status": lead.pipeline_status, "updated": True}


# ── Rate writes ───────────────────────────────────────────────────────────────

class AgentRateWrite(BaseModel):
    rate_conventional_30: Optional[float] = None
    rate_conventional_15: Optional[float] = None
    rate_fha_30:          Optional[float] = None
    rate_va_30:           Optional[float] = None
    rate_usda_30:         Optional[float] = None
    rate_dscr:            Optional[float] = None
    rate_heloc_prime_plus:Optional[float] = None
    rate_jumbo_30:        Optional[float] = None
    notes:                Optional[str] = None
    snapshot_date:        Optional[str] = None   # defaults to today


@router.post("/write/rates")
async def agent_set_rates(data: AgentRateWrite, db: AsyncSession = Depends(get_db)):
    """
    Set today's mortgage rates directly from the agent.
    Works exactly like the admin Rate Snapshot panel — upserts by date.
    """
    target_date = data.snapshot_date or date.today().isoformat()

    result = await db.execute(select(RateSnapshot).where(RateSnapshot.snapshot_date == target_date))
    snapshot = result.scalar_one_or_none()
    if not snapshot:
        snapshot = RateSnapshot(snapshot_date=target_date)
        db.add(snapshot)

    rate_fields = [
        "rate_conventional_30", "rate_conventional_15", "rate_fha_30",
        "rate_va_30", "rate_usda_30", "rate_dscr", "rate_heloc_prime_plus", "rate_jumbo_30",
    ]
    changed = {}
    for field in rate_fields:
        val = getattr(data, field)
        if val is not None:
            setattr(snapshot, field, val)
            changed[field] = val

    snapshot.source = "agent"
    snapshot.is_admin_override = True
    if data.notes:
        snapshot.notes = data.notes

    await db.commit()
    await log_event(db, "agent.rates.set", actor_type="agent",
                    resource_type="rate_snapshot", resource_id=target_date,
                    details={"date": target_date, "rates_set": changed})
    return {"snapshot_date": target_date, "rates_updated": changed, "success": True}


@router.post("/write/rates/sync-fred")
async def agent_sync_fred(db: AsyncSession = Depends(get_db)):
    """Trigger a FRED sync from the agent — same as clicking the button in the admin UI."""
    from app.services.fred_service import fetch_fred_two_weeks

    fred_data = await fetch_fred_two_weeks()
    if not fred_data["has_key"] or fred_data["error"]:
        return {"success": False, "message": fred_data.get("error", "FRED_API_KEY not set")}

    rate_fields = [
        "rate_conventional_30", "rate_conventional_15", "rate_fha_30",
        "rate_va_30", "rate_usda_30", "rate_dscr", "rate_heloc_prime_plus", "rate_jumbo_30",
    ]
    saved = []
    for week_key in ("current", "previous"):
        week = fred_data.get(week_key)
        if not week:
            continue
        snap_date = week["date"]
        result = await db.execute(select(RateSnapshot).where(RateSnapshot.snapshot_date == snap_date))
        snapshot = result.scalar_one_or_none()
        if snapshot and snapshot.is_admin_override and week_key == "current":
            saved.append({"date": snap_date, "status": "skipped_manual_override"})
            continue
        if not snapshot:
            snapshot = RateSnapshot(snapshot_date=snap_date)
            db.add(snapshot)
        for field in rate_fields:
            val = week.get(field)
            if val is not None:
                setattr(snapshot, field, val)
        snapshot.source = "fred"
        snapshot.is_admin_override = False
        saved.append({"date": snap_date, "status": "saved"})

    await db.commit()
    return {"success": True, "saved": saved}


# ── Listing writes ────────────────────────────────────────────────────────────

class AgentListingWrite(BaseModel):
    address:       str
    city:          str
    state:         str = "MD"
    county:        Optional[str] = None
    zip_code:      Optional[str] = None
    list_price:    float
    bedrooms:      Optional[int] = None
    bathrooms:     Optional[float] = None
    sqft:          Optional[int] = None
    property_type: Optional[str] = None
    photo_url:     Optional[str] = None
    zillow_url:    Optional[str] = None
    description:   Optional[str] = None
    status:        str = "active"
    is_featured:   bool = True
    hoa_monthly:   Optional[float] = None
    annual_taxes:  Optional[float] = None
    annual_insurance: Optional[float] = None
    listing_agent_contact_id: Optional[str] = None
    listing_agent_name:       Optional[str] = None
    listing_agent_phone:      Optional[str] = None
    listing_agent_email:      Optional[str] = None


@router.post("/write/listing", status_code=201)
async def agent_create_listing(data: AgentListingWrite, db: AsyncSession = Depends(get_db)):
    """Create a new property listing directly from the agent."""
    try:
        status = ListingStatus(data.status)
    except ValueError:
        raise HTTPException(400, f"Invalid status '{data.status}'")

    listing = Listing(
        address=data.address, city=data.city, state=data.state,
        county=data.county, zip_code=data.zip_code, list_price=data.list_price,
        bedrooms=data.bedrooms, bathrooms=data.bathrooms, sqft=data.sqft,
        property_type=data.property_type, photo_url=data.photo_url,
        zillow_url=data.zillow_url, description=data.description,
        status=status, is_featured=data.is_featured,
        hoa_monthly=data.hoa_monthly, annual_taxes=data.annual_taxes,
        annual_insurance=data.annual_insurance,
        listing_agent_contact_id=data.listing_agent_contact_id,
        listing_agent_name=data.listing_agent_name,
        listing_agent_phone=data.listing_agent_phone,
        listing_agent_email=data.listing_agent_email,
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    await log_event(db, "agent.listing.created", actor_type="agent",
                    resource_type="listing", resource_id=listing.id,
                    details={"address": data.address, "price": data.list_price})
    return {"id": listing.id, "address": listing.address, "list_price": listing.list_price}


class AgentListingUpdate(BaseModel):
    list_price:    Optional[float] = None
    status:        Optional[str] = None
    description:   Optional[str] = None
    photo_url:     Optional[str] = None
    zillow_url:    Optional[str] = None
    is_featured:   Optional[bool] = None
    bedrooms:      Optional[int] = None
    bathrooms:     Optional[float] = None
    sqft:          Optional[int] = None
    hoa_monthly:   Optional[float] = None
    annual_taxes:  Optional[float] = None
    annual_insurance:         Optional[float] = None
    listing_agent_contact_id: Optional[str] = None
    listing_agent_name:       Optional[str] = None
    listing_agent_phone:      Optional[str] = None
    listing_agent_email:      Optional[str] = None


@router.patch("/write/listing/{listing_id}")
async def agent_update_listing(listing_id: str, data: AgentListingUpdate, db: AsyncSession = Depends(get_db)):
    """Update a listing — price, status, description, photo, etc."""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(404, f"Listing {listing_id} not found")

    for field, val in data.model_dump(exclude_none=True).items():
        if field == "status":
            try:
                val = ListingStatus(val)
            except ValueError:
                raise HTTPException(400, f"Invalid status '{val}'")
        setattr(listing, field, val)

    await db.commit()
    await log_event(db, "agent.listing.updated", actor_type="agent",
                    resource_type="listing", resource_id=listing_id,
                    details=data.model_dump(exclude_none=True))
    return {"id": listing_id, "updated": True}


# ── Campaign writes ───────────────────────────────────────────────────────────

class AgentCampaignUpdate(BaseModel):
    status:       Optional[str] = None   # draft | active | paused | completed | archived
    name:         Optional[str] = None
    notes:        Optional[str] = None
    contact_ids:  Optional[list] = None  # replace full contact list


@router.patch("/write/campaign/{campaign_id}")
async def agent_update_campaign(campaign_id: str, data: AgentCampaignUpdate, db: AsyncSession = Depends(get_db)):
    """Update a campaign's status, name, or contact list."""
    from app.models.campaign import CampaignStatus
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, f"Campaign {campaign_id} not found")

    if data.status:
        try:
            campaign.status = CampaignStatus(data.status)
            if data.status == "active" and not campaign.started_at:
                campaign.started_at = datetime.utcnow()
            if data.status == "completed":
                campaign.completed_at = datetime.utcnow()
        except ValueError:
            raise HTTPException(400, f"Invalid status '{data.status}'")
    if data.name:
        campaign.name = data.name
    if data.contact_ids is not None:
        campaign.contact_ids = data.contact_ids
    if data.notes:
        campaign.compliance_notes = (campaign.compliance_notes or "") + f"\n[Agent] {data.notes}"

    campaign.updated_at = datetime.utcnow()
    await db.commit()
    await log_event(db, "agent.campaign.updated", actor_type="agent",
                    resource_type="campaign", resource_id=campaign_id,
                    details=data.model_dump(exclude_none=True))
    return {"id": campaign_id, "status": str(campaign.status), "updated": True}


@router.post("/write/campaign/{campaign_id}/add-contacts")
async def agent_add_campaign_contacts(
    campaign_id: str,
    body: dict,   # {"contact_ids": ["id1", "id2"]}
    db: AsyncSession = Depends(get_db),
):
    """Append contacts to a campaign without replacing the existing list."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, f"Campaign {campaign_id} not found")

    new_ids = body.get("contact_ids", [])
    existing = list(campaign.contact_ids or [])
    merged = list(dict.fromkeys(existing + new_ids))   # dedup, preserve order
    campaign.contact_ids = merged
    campaign.updated_at = datetime.utcnow()
    await db.commit()
    return {"id": campaign_id, "total_contacts": len(merged), "added": len(new_ids)}


# ══════════════════════════════════════════════════════════════════════════════
# FULL RECORD READS — let the agent pull complete detail on any entity
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/read/contact/{contact_id}")
async def agent_read_contact(contact_id: str, db: AsyncSession = Depends(get_db)):
    """Full contact record — every field, including consent, score, notes."""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, f"Contact {contact_id} not found")
    return {
        "id": c.id,
        "first_name": c.first_name, "last_name": c.last_name,
        "email": c.email, "phone": c.phone,
        "company": c.company, "role_title": c.role_title,
        "address": c.address, "city": c.city, "state": c.state,
        "county": c.county, "zip_code": c.zip_code,
        "contact_type": c.contact_type,
        "source": c.source, "tags": c.tags or [],
        "notes": c.notes,
        "lead_score": c.lead_score, "lead_score_notes": c.lead_score_notes,
        "consent_email": c.consent_email, "consent_sms": c.consent_sms,
        "consent_call": c.consent_call,
        "is_dnc": c.is_dnc, "is_opted_out": c.is_opted_out,
        "last_contacted_at": c.last_contacted_at.isoformat() if c.last_contacted_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/read/lead/{lead_id}")
async def agent_read_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    """Full lead record — every intake field plus AI score if available."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(LeadIntake)
        .options(selectinload(LeadIntake.score))
        .where(LeadIntake.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, f"Lead {lead_id} not found")

    score = lead.score
    return {
        "id": lead.id,
        "first_name": lead.first_name, "last_name": lead.last_name,
        "email": lead.email, "phone": lead.phone,
        "state": lead.state, "city": lead.city, "county": lead.county,
        "loan_interest_type": lead.loan_interest_type,
        "timeline": lead.timeline,
        "credit_score_range": lead.credit_score_range,
        "income_range": lead.income_range,
        "cash_available": lead.cash_available,
        "property_goal": lead.property_goal,
        "target_price": lead.target_price,
        "notes": lead.notes,
        "pipeline_status": lead.pipeline_status,
        "consent_email": lead.consent_email,
        "consent_sms": lead.consent_sms,
        "consent_call": lead.consent_call,
        "utm_source": lead.utm_source, "utm_campaign": lead.utm_campaign,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "score": {
            "score_value": score.score_value,
            "score_label": score.score_label,
            "recommended_product": score.recommended_product,
            "readiness_score": score.readiness_score,
            "summary": score.summary,
            "questions_for_call": score.questions_for_call,
            "recommended_cta": score.recommended_cta,
        } if score else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# DELETE ENDPOINTS — contacts, listings
# ══════════════════════════════════════════════════════════════════════════════

@router.delete("/write/contact/{contact_id}", status_code=200)
async def agent_delete_contact(contact_id: str, db: AsyncSession = Depends(get_db)):
    """
    Permanently delete a contact. Logs to audit trail before deletion.
    Use with care — prefer updating is_dnc=True / is_opted_out=True for compliance records.
    """
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, f"Contact {contact_id} not found")

    name = f"{contact.first_name or ''} {contact.last_name or ''}".strip() or contact.email or contact_id
    await log_event(db, "agent.contact.deleted", actor_type="agent",
                    resource_type="contact", resource_id=contact_id,
                    details={"name": name, "contact_type": str(contact.contact_type)})
    await db.delete(contact)
    await db.commit()
    return {"deleted": True, "id": contact_id, "name": name}


@router.delete("/write/listing/{listing_id}", status_code=200)
async def agent_delete_listing(listing_id: str, db: AsyncSession = Depends(get_db)):
    """Permanently remove a listing from the public hub."""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(404, f"Listing {listing_id} not found")

    await log_event(db, "agent.listing.deleted", actor_type="agent",
                    resource_type="listing", resource_id=listing_id,
                    details={"address": listing.address, "price": listing.list_price})
    await db.delete(listing)
    await db.commit()
    return {"deleted": True, "id": listing_id, "address": listing.address}


# ══════════════════════════════════════════════════════════════════════════════
# LISTING IMAGE UPLOAD — save a photo and return a permanent hosted URL
# ══════════════════════════════════════════════════════════════════════════════

class AgentImageUpload(BaseModel):
    image_url: str   # URL the agent found on Zillow / Redfin / anywhere — we download + rehost


@router.post("/write/listing/upload-image", status_code=201)
async def agent_upload_listing_image(data: AgentImageUpload):
    """
    Download an image from any URL and save it to /media/listings/.
    Returns a permanent backend-hosted URL safe to store in listing.photo_url.
    Use this when Zillow/Redfin photo URLs may expire or be hotlink-blocked.
    """
    import uuid, os, mimetypes
    from app.config import settings

    media_dir = os.getenv("MEDIA_STORAGE_PATH", "./media")
    listings_dir = os.path.join(media_dir, "listings")
    os.makedirs(listings_dir, exist_ok=True)

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resp = await client.get(data.image_url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                raise HTTPException(400, f"Could not fetch image — HTTP {resp.status_code}")

            content_type = resp.headers.get("content-type", "image/jpeg")
            ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".jpg"
            # Normalize weird ext mappings
            ext = {".jpe": ".jpg", ".jpeg": ".jpg"}.get(ext, ext)
            if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                ext = ".jpg"

            filename  = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(listings_dir, filename)
            with open(file_path, "wb") as f:
                f.write(resp.content)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Image download failed: {e}")

    hosted_url = f"{settings.backend_url}/media/listings/{filename}"
    return {
        "url":      hosted_url,
        "filename": filename,
        "note":     "Use this URL as photo_url when creating or updating the listing.",
    }


@router.post("/write/listing/upload-image/file", status_code=201)
async def agent_upload_listing_image_file(file: UploadFile = File(...)):
    """
    Accept a multipart/form-data image upload directly (e.g. from Telegram or local file).
    Saves to /media/listings/ and returns a permanent hosted URL.

    POST with:  -F "file=@/path/to/photo.jpg"
    Returns:    { "url": "...", "filename": "..." }
    """
    import uuid, os, mimetypes
    from app.config import settings

    media_dir    = os.getenv("MEDIA_STORAGE_PATH", "./media")
    listings_dir = os.path.join(media_dir, "listings")
    os.makedirs(listings_dir, exist_ok=True)

    content_type = file.content_type or "image/jpeg"
    ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".jpg"
    ext = {".jpe": ".jpg", ".jpeg": ".jpg"}.get(ext, ext)
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        # Fall back to original file extension if mime type is unhelpful
        orig_ext = os.path.splitext(file.filename or "")[-1].lower()
        ext = orig_ext if orig_ext in (".jpg", ".jpeg", ".png", ".webp", ".gif") else ".jpg"

    filename  = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(listings_dir, filename)

    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(400, "Uploaded file is empty")
        with open(file_path, "wb") as f:
            f.write(contents)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"File save failed: {e}")

    hosted_url = f"{settings.backend_url}/media/listings/{filename}"
    return {
        "url":           hosted_url,
        "filename":      filename,
        "original_name": file.filename,
        "note":          "Use this URL as photo_url when creating or updating the listing.",
    }


# ══════════════════════════════════════════════════════════════════════════════
# DPA WRITE — create / update / delete down payment assistance programs
# ══════════════════════════════════════════════════════════════════════════════

class AgentDpaWrite(BaseModel):
    program_name:          str
    state:                 str = "MD"
    dpa_type:              str                   # grant|forgivable|deferred|repayable|second_lien
    county:                Optional[str] = None  # null = statewide
    city:                  Optional[str] = None
    administering_agency:  Optional[str] = None
    assistance_amount:     Optional[str] = None  # "Up to $25,000" or "5% of price"
    assistance_amount_max: Optional[float] = None
    target_buyer:          Optional[str] = None  # "First-time buyers", "Repeat OK"
    income_limit_notes:    Optional[str] = None
    credit_score_min:      Optional[int] = None
    eligible_loan_types:   Optional[str] = None  # "FHA, Conventional, VA"
    repayment_notes:       Optional[str] = None
    education_required:    bool = False
    other_requirements:    Optional[str] = None
    program_url:           Optional[str] = None
    is_active:             bool = True
    is_featured:           bool = False
    last_verified:         Optional[str] = None  # YYYY-MM-DD
    notes:                 Optional[str] = None


class AgentDpaUpdate(BaseModel):
    program_name:          Optional[str] = None
    state:                 Optional[str] = None
    dpa_type:              Optional[str] = None
    county:                Optional[str] = None
    assistance_amount:     Optional[str] = None
    assistance_amount_max: Optional[float] = None
    target_buyer:          Optional[str] = None
    income_limit_notes:    Optional[str] = None
    credit_score_min:      Optional[int] = None
    eligible_loan_types:   Optional[str] = None
    repayment_notes:       Optional[str] = None
    education_required:    Optional[bool] = None
    other_requirements:    Optional[str] = None
    program_url:           Optional[str] = None
    is_active:             Optional[bool] = None
    is_featured:           Optional[bool] = None
    last_verified:         Optional[str] = None
    notes:                 Optional[str] = None
    administering_agency:  Optional[str] = None


def _dpa_dict(p: DpaProgram) -> dict:
    return {
        "id": p.id, "program_name": p.program_name,
        "state": p.state, "county": p.county, "city": p.city,
        "dpa_type": p.dpa_type, "assistance_amount": p.assistance_amount,
        "assistance_amount_max": p.assistance_amount_max,
        "target_buyer": p.target_buyer, "credit_score_min": p.credit_score_min,
        "eligible_loan_types": p.eligible_loan_types,
        "education_required": p.education_required,
        "is_active": p.is_active, "is_featured": p.is_featured,
        "program_url": p.program_url, "last_verified": p.last_verified,
        "notes": p.notes,
    }


@router.post("/write/dpa", status_code=201)
async def agent_create_dpa(data: AgentDpaWrite, db: AsyncSession = Depends(get_db)):
    """Add a new Down Payment Assistance program to the hub."""
    try:
        dpa_type = DpaType(data.dpa_type)
    except ValueError:
        raise HTTPException(400, f"Invalid dpa_type '{data.dpa_type}'. Valid: grant|forgivable|deferred|repayable|second_lien")

    program = DpaProgram(**{k: v for k, v in data.model_dump().items() if k != "dpa_type"},
                         dpa_type=dpa_type)
    db.add(program)
    await db.commit()
    await db.refresh(program)
    await log_event(db, "agent.dpa.created", actor_type="agent",
                    resource_type="dpa_program", resource_id=program.id,
                    details={"name": data.program_name, "state": data.state})
    return _dpa_dict(program)


@router.patch("/write/dpa/{program_id}")
async def agent_update_dpa(program_id: str, data: AgentDpaUpdate, db: AsyncSession = Depends(get_db)):
    """Update any field on a DPA program — amount, eligibility, URL, active status, etc."""
    result = await db.execute(select(DpaProgram).where(DpaProgram.id == program_id))
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(404, f"DPA program {program_id} not found")

    for field, val in data.model_dump(exclude_none=True).items():
        if field == "dpa_type":
            try:
                val = DpaType(val)
            except ValueError:
                raise HTTPException(400, f"Invalid dpa_type '{val}'")
        setattr(program, field, val)

    await db.commit()
    await log_event(db, "agent.dpa.updated", actor_type="agent",
                    resource_type="dpa_program", resource_id=program_id,
                    details=data.model_dump(exclude_none=True))
    return _dpa_dict(program)


@router.delete("/write/dpa/{program_id}", status_code=200)
async def agent_delete_dpa(program_id: str, db: AsyncSession = Depends(get_db)):
    """Permanently remove a DPA program. Use is_active=false to hide without deleting."""
    result = await db.execute(select(DpaProgram).where(DpaProgram.id == program_id))
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(404, f"DPA program {program_id} not found")

    await log_event(db, "agent.dpa.deleted", actor_type="agent",
                    resource_type="dpa_program", resource_id=program_id,
                    details={"name": program.program_name})
    await db.delete(program)
    await db.commit()
    return {"deleted": True, "id": program_id, "program_name": program.program_name}


# ══════════════════════════════════════════════════════════════════════════════
# RATE ALERTS — read + full CRUD through the agent
# ══════════════════════════════════════════════════════════════════════════════

def _alert_dict(a: RateAlert) -> dict:
    return {
        "id": a.id, "name": a.name,
        "rate_field": a.rate_field, "threshold": a.threshold, "direction": a.direction,
        "action": a.action, "message": a.message, "is_active": a.is_active,
        "last_triggered_at": a.last_triggered_at.isoformat() if a.last_triggered_at else None,
        "last_triggered_rate": a.last_triggered_rate,
    }


@router.get("/read/rates/alerts")
async def agent_list_rate_alerts(db: AsyncSession = Depends(get_db)):
    """List all rate alerts with their current status and last trigger info."""
    result = await db.execute(select(RateAlert).order_by(RateAlert.created_at.desc()))
    return [_alert_dict(a) for a in result.scalars().all()]


class AgentRateAlertWrite(BaseModel):
    name:       str
    rate_field: str      # rate_conventional_30 | rate_fha_30 | rate_va_30 | rate_usda_30 | rate_conventional_15 | rate_dscr | rate_heloc_prime_plus | rate_jumbo_30
    threshold:  float
    direction:  str      # below | above
    action:     str = "log"   # log | queue_outreach
    message:    Optional[str] = None
    is_active:  bool = True


class AgentRateAlertUpdate(BaseModel):
    name:       Optional[str] = None
    threshold:  Optional[float] = None
    direction:  Optional[str] = None
    action:     Optional[str] = None
    message:    Optional[str] = None
    is_active:  Optional[bool] = None


VALID_ALERT_FIELDS = {
    "rate_conventional_30", "rate_conventional_15", "rate_fha_30",
    "rate_va_30", "rate_usda_30", "rate_dscr", "rate_heloc_prime_plus", "rate_jumbo_30",
}


@router.post("/write/rates/alert", status_code=201)
async def agent_create_rate_alert(data: AgentRateAlertWrite, db: AsyncSession = Depends(get_db)):
    """Create a rate alert. Fires when the named rate crosses the threshold."""
    if data.rate_field not in VALID_ALERT_FIELDS:
        raise HTTPException(400, f"Invalid rate_field. Valid: {', '.join(sorted(VALID_ALERT_FIELDS))}")
    if data.direction not in ("below", "above"):
        raise HTTPException(400, "direction must be 'below' or 'above'")

    alert = RateAlert(**data.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    await log_event(db, "agent.rate_alert.created", actor_type="agent",
                    resource_type="rate_alert", resource_id=alert.id,
                    details={"name": data.name, "field": data.rate_field, "threshold": data.threshold})
    return _alert_dict(alert)


@router.patch("/write/rates/alert/{alert_id}")
async def agent_update_rate_alert(alert_id: str, data: AgentRateAlertUpdate, db: AsyncSession = Depends(get_db)):
    """Update a rate alert — change threshold, toggle active, adjust action."""
    result = await db.execute(select(RateAlert).where(RateAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, f"Rate alert {alert_id} not found")

    for field, val in data.model_dump(exclude_none=True).items():
        setattr(alert, field, val)

    await db.commit()
    return _alert_dict(alert)


@router.delete("/write/rates/alert/{alert_id}", status_code=200)
async def agent_delete_rate_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a rate alert permanently."""
    result = await db.execute(select(RateAlert).where(RateAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, f"Rate alert {alert_id} not found")

    await log_event(db, "agent.rate_alert.deleted", actor_type="agent",
                    resource_type="rate_alert", resource_id=alert_id,
                    details={"name": alert.name})
    await db.delete(alert)
    await db.commit()
    return {"deleted": True, "id": alert_id}
