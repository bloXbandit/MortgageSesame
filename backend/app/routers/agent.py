"""
Agent Tool API — 13 endpoints for Clawdbot/OpenClaw/Hermes or any OpenAI-function-calling agent.

Auth: Bearer token = AGENT_API_KEY from .env
Every action is logged. No external sends without explicit approval.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
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
import json

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
@router.post("/generate-outreach")
async def generate_outreach(data: GenerateOutreachRequest, db: AsyncSession = Depends(get_db)):
    contact_q = await db.execute(select(Contact).where(Contact.id == data.contact_id))
    contact = contact_q.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")
    if contact.is_dnc or contact.is_opted_out:
        raise HTTPException(403, "Contact is DNC or opted out.")

    product_data = {}
    if data.product_id:
        p_q = await db.execute(select(Product).where(Product.id == data.product_id))
        prod = p_q.scalar_one_or_none()
        if prod:
            product_data = {"name": prod.name, "benefits": prod.benefits, "cta": prod.cta_language}

    contact_data = {
        "name": f"{contact.first_name or ''} {contact.last_name or ''}".strip(),
        "company": contact.company, "role": contact.role_title,
        "type": contact.contact_type, "city": contact.city, "state": contact.state,
    }

    draft = await ai_service.generate_outreach(contact_data, product_data, data.goal, data.channel)
    compliance = check_content(draft.get("body", ""), channel=data.channel)

    await log_event(db, "agent.generate_outreach", actor_type="agent",
                    resource_type="contact", resource_id=data.contact_id,
                    details={"channel": data.channel, "goal": data.goal, "compliance_passed": compliance.passed})
    await db.commit()

    return {
        "draft": draft,
        "compliance": {"passed": compliance.passed, "flags": compliance.flags},
        "requires_approval": True,
        "note": "Queue this via /agent/queue-action before any send.",
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
