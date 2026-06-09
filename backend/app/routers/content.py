"""
Content Studio router.

Routes:
  GET  /content/posts              — list posts (filterable)
  POST /content/generate           — generate new post via AI
  PATCH /content/posts/{id}        — edit any field (inline editing)
  PATCH /content/posts/{id}/approve — approve / reject / schedule

  GET  /content/script-templates        — list editable script templates
  POST /content/script-templates        — create a new template
  PATCH /content/script-templates/{id}  — update a template
  DELETE /content/script-templates/{id} — delete a template

  POST /content/posts/{id}/generate-voice  — ElevenLabs voiceover → MediaAsset
  POST /content/posts/{id}/generate-video  — HeyGen avatar video → MediaAsset
  GET  /content/posts/{id}/video-status    — poll HeyGen render status
  POST /content/posts/{id}/pipeline        — run full voice+video+queue pipeline
  POST /content/posts/{id}/publish         — push final video to platform
"""

import os
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.audit import log_event
from app.models.content import SocialPost, MediaAsset, ContentPlatform, ContentCategory, ApprovalStatus
from app.models.script_template import ScriptTemplate
from app.models.user import User
from app.services import ai_service
from app.services.compliance import check_content

log = structlog.get_logger()
router = APIRouter(prefix="/content", tags=["content"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ContentGenerateRequest(BaseModel):
    platform: ContentPlatform
    category: ContentCategory
    product_id: Optional[str] = None
    custom_context: Optional[str] = None

class PostUpdate(BaseModel):
    hook: Optional[str] = None
    script: Optional[str] = None
    voiceover_script: Optional[str] = None
    caption: Optional[str] = None
    cta: Optional[str] = None
    visual_concept: Optional[str] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    broll_instructions: Optional[str] = None
    compliance_notes: Optional[str] = None
    pipeline_stage: Optional[str] = None

class ApprovalAction(BaseModel):
    action: str  # approve | reject | needs_edit | schedule
    rejection_reason: Optional[str] = None
    scheduled_date: Optional[datetime] = None

class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    platform: Optional[str] = None
    category: Optional[str] = None
    template_type: str = "style_guide"   # hook|cta|style_guide|full_script|objection|tone_guide
    content: str
    variables: Optional[list] = None
    is_active: bool = True
    priority: int = 0

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    platform: Optional[str] = None
    category: Optional[str] = None
    template_type: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[list] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None

class PipelineRequest(BaseModel):
    generate_voice: bool = True
    generate_video: bool = False
    auto_queue: bool = True

class PublishRequest(BaseModel):
    platform: Optional[str] = None   # override post.platform if needed
    caption_override: Optional[str] = None
    hashtags: Optional[list] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _serialize(p: SocialPost) -> dict:
    return {
        "id": p.id,
        "platform": p.platform,
        "category": p.category,
        "hook": p.hook,
        "script": p.script,
        "voiceover_script": p.voiceover_script,
        "caption": p.caption,
        "cta": p.cta,
        "visual_concept": p.visual_concept,
        "image_prompt": p.image_prompt,
        "video_prompt": p.video_prompt,
        "broll_instructions": p.broll_instructions,
        "compliance_notes": p.compliance_notes,
        "is_fictional_example": p.is_fictional_example,
        "approval_status": p.approval_status,
        "pipeline_stage": p.pipeline_stage,
        "scheduled_date": p.scheduled_date.isoformat() if p.scheduled_date else None,
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "external_post_id": p.external_post_id,
        "media_asset_ids": p.media_asset_ids or [],
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


async def _load_template_context(
    db: AsyncSession, platform: str, category: str
) -> str:
    """
    Pull active ScriptTemplates relevant to this platform+category
    and format them for injection into the AI prompt.
    """
    from sqlalchemy import or_

    stmt = (
        select(ScriptTemplate)
        .where(ScriptTemplate.is_active == True)
        .where(
            or_(
                ScriptTemplate.platform == None,
                ScriptTemplate.platform == platform,
            )
        )
        .where(
            or_(
                ScriptTemplate.category == None,
                ScriptTemplate.category == category,
            )
        )
        .order_by(ScriptTemplate.priority.desc())
    )
    result = await db.execute(stmt)
    templates = result.scalars().all()

    if not templates:
        return ""

    lines = []
    for t in templates:
        lines.append(f"[{t.template_type.upper()} — {t.name}]\n{t.content}")

    return "\n\n".join(lines)


# ── Post endpoints ─────────────────────────────────────────────────────────────

@router.get("/posts")
async def list_posts(
    platform: Optional[ContentPlatform] = None,
    status: Optional[ApprovalStatus] = None,
    pipeline_stage: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(SocialPost).order_by(SocialPost.created_at.desc()).limit(limit)
    if platform:
        q = q.where(SocialPost.platform == platform)
    if status:
        q = q.where(SocialPost.approval_status == status)
    if pipeline_stage:
        q = q.where(SocialPost.pipeline_stage == pipeline_stage)
    result = await db.execute(q)
    return [_serialize(p) for p in result.scalars().all()]


@router.post("/generate", status_code=201)
async def generate_post(
    data: ContentGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product_context = data.custom_context or ""
    if data.product_id:
        from app.models.product import Product
        p_q = await db.execute(select(Product).where(Product.id == data.product_id))
        prod = p_q.scalar_one_or_none()
        if prod:
            product_context = f"{prod.name}: {prod.benefits or ''}"

    # Inject script templates for this platform + category
    template_context = await _load_template_context(
        db, data.platform.value, data.category.value
    )

    banker_voice = getattr(current_user, "brand_voice", "") or ""
    content = await ai_service.generate_content(
        data.platform.value,
        data.category.value,
        product_context,
        banker_voice,
        template_context=template_context,
    )

    compliance = check_content(
        (content.get("caption") or "") + " " + (content.get("script") or ""),
        is_ad=True,
    )

    post = SocialPost(
        platform=data.platform,
        category=data.category,
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
        generated_by="user",
        created_by=current_user.id,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    return {
        "post": _serialize(post),
        "compliance": {"passed": compliance.passed, "flags": compliance.flags},
        "templates_used": bool(template_context),
    }


@router.patch("/posts/{post_id}")
async def update_post(
    post_id: str,
    data: PostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Inline field editing — any field can be updated. Resets to PENDING if content changes."""
    q = await db.execute(select(SocialPost).where(SocialPost.id == post_id))
    post = q.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")

    content_fields = {"hook", "script", "voiceover_script", "caption", "cta"}
    changed_content = False

    for field, val in data.model_dump(exclude_none=True).items():
        setattr(post, field, val)
        if field in content_fields:
            changed_content = True

    # If content was edited, run compliance again and reset status
    if changed_content:
        text = (post.caption or "") + " " + (post.script or "")
        compliance = check_content(text, is_ad=True)
        post.compliance_notes = post.compliance_notes or ""
        if not compliance.passed:
            post.compliance_notes += f"\n[Re-check flags: {', '.join(compliance.flags)}]"
        post.approval_status = ApprovalStatus.PENDING

    post.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(post)
    return _serialize(post)


@router.patch("/posts/{post_id}/approve")
async def approve_post(
    post_id: str,
    data: ApprovalAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(SocialPost).where(SocialPost.id == post_id))
    post = q.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")

    if data.action == "approve":
        post.approval_status = ApprovalStatus.APPROVED
        post.approved_by = current_user.id
        post.approved_at = datetime.utcnow()
        if data.scheduled_date:
            post.scheduled_date = data.scheduled_date
            post.approval_status = ApprovalStatus.SCHEDULED
    elif data.action == "reject":
        post.approval_status = ApprovalStatus.REJECTED
        post.rejection_reason = data.rejection_reason
    elif data.action == "needs_edit":
        post.approval_status = ApprovalStatus.NEEDS_EDIT
        post.rejection_reason = data.rejection_reason
    elif data.action == "schedule":
        post.approval_status = ApprovalStatus.SCHEDULED
        post.scheduled_date = data.scheduled_date

    await db.commit()
    await log_event(db, f"content.{data.action}", actor_type="user",
                    actor_id=current_user.id, resource_type="social_post", resource_id=post_id)
    await db.commit()
    return _serialize(post)


# ── Script templates ──────────────────────────────────────────────────────────

@router.get("/script-templates")
async def list_templates(
    platform: Optional[str] = None,
    category: Optional[str] = None,
    template_type: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ScriptTemplate).order_by(
        ScriptTemplate.priority.desc(), ScriptTemplate.created_at.desc()
    )
    if active_only:
        stmt = stmt.where(ScriptTemplate.is_active == True)
    if platform:
        stmt = stmt.where(ScriptTemplate.platform == platform)
    if category:
        stmt = stmt.where(ScriptTemplate.category == category)
    if template_type:
        stmt = stmt.where(ScriptTemplate.template_type == template_type)

    result = await db.execute(stmt)
    templates = result.scalars().all()
    return [_serialize_template(t) for t in templates]


@router.post("/script-templates", status_code=201)
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t = ScriptTemplate(
        name=data.name,
        description=data.description,
        platform=data.platform,
        category=data.category,
        template_type=data.template_type,
        content=data.content,
        variables=data.variables or [],
        is_active=data.is_active,
        priority=data.priority,
        created_by=current_user.id,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    log.info("script_template.created", id=t.id, name=t.name, type=t.template_type)
    return _serialize_template(t)


@router.patch("/script-templates/{template_id}")
async def update_template(
    template_id: str,
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == template_id))
    t = q.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Template not found")

    for field, val in data.model_dump(exclude_none=True).items():
        setattr(t, field, val)
    t.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(t)
    return _serialize_template(t)


@router.delete("/script-templates/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == template_id))
    t = q.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Template not found")
    await db.delete(t)
    await db.commit()


def _serialize_template(t: ScriptTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "platform": t.platform,
        "category": t.category,
        "template_type": t.template_type,
        "content": t.content,
        "variables": t.variables or [],
        "is_active": t.is_active,
        "priority": t.priority,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


# ── Voice generation ──────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/generate-voice", status_code=201)
async def generate_voice(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate ElevenLabs voiceover and save as MediaAsset."""
    q = await db.execute(select(SocialPost).where(SocialPost.id == post_id))
    post = q.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")
    if not post.voiceover_script:
        raise HTTPException(400, "Post has no voiceover_script — edit it first")

    from app.services.integrations.elevenlabs import generate_audio
    audio_bytes = await generate_audio(post.voiceover_script)

    media_dir = os.getenv("MEDIA_STORAGE_PATH", "./media")
    os.makedirs(media_dir, exist_ok=True)

    asset = MediaAsset(
        name=f"voice_{post_id[:8]}.mp3",
        asset_type="audio",
        mime_type="audio/mpeg",
        file_size=len(audio_bytes),
        tags=["voiceover", "elevenlabs", post.platform.value if post.platform else ""],
    )
    db.add(asset)
    await db.flush()

    file_path = f"{media_dir}/{asset.id}.mp3"
    with open(file_path, "wb") as f:
        f.write(audio_bytes)

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    asset.file_path = file_path
    asset.file_url  = f"{backend_url}/media/{asset.id}.mp3"

    media_ids = list(post.media_asset_ids or [])
    media_ids = [m for m in media_ids if m.get("type") != "audio"]   # replace old audio
    media_ids.append({"id": asset.id, "type": "audio", "url": asset.file_url})
    post.media_asset_ids = media_ids
    post.pipeline_stage  = "voice_ready"

    await db.commit()
    log.info("voice.generated", post_id=post_id, asset_id=asset.id, size=len(audio_bytes))
    return {"asset_id": asset.id, "url": asset.file_url, "size_bytes": len(audio_bytes)}


# ── Video generation ──────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/generate-video", status_code=201)
async def generate_video(
    post_id: str,
    test_mode: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit to HeyGen. Returns immediately with provider_id for polling."""
    q = await db.execute(select(SocialPost).where(SocialPost.id == post_id))
    post = q.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")
    if not post.voiceover_script:
        raise HTTPException(400, "Post has no voiceover_script")

    from app.services.providers.video import get_video_provider
    provider = get_video_provider()

    aspect = "9:16" if post.platform and post.platform.value in ("tiktok", "instagram_reel") else "16:9"
    vr = await provider.generate_video({
        "script":       post.voiceover_script,
        "aspect_ratio": aspect,
        "test_mode":    test_mode,
    })

    if not vr.success:
        raise HTTPException(500, f"Video generation failed: {vr.error}")

    asset = MediaAsset(
        name=f"video_raw_{post_id[:8]}",
        asset_type="video_raw",
        mime_type="video/mp4",
        file_url=vr.video_url,
        tags=["heygen", "raw", f"provider_id:{vr.provider_id}"],
    )
    db.add(asset)
    await db.flush()

    media_ids = list(post.media_asset_ids or [])
    media_ids.append({"id": asset.id, "type": "video_raw", "url": vr.video_url or "", "provider_id": vr.provider_id, "status": vr.status})
    post.media_asset_ids = media_ids
    post.pipeline_stage  = "video_processing" if vr.status == "processing" else "video_ready"

    await db.commit()
    return {
        "asset_id":    asset.id,
        "provider_id": vr.provider_id,
        "status":      vr.status,
        "video_url":   vr.video_url,
    }


@router.get("/posts/{post_id}/video-status")
async def get_video_status(
    post_id: str,
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll HeyGen video render status."""
    from app.services.providers.video import get_video_provider
    provider = get_video_provider()
    vr = await provider.poll_status(provider_id)

    if vr.status == "completed":
        # Update the asset with the final URL
        q = await db.execute(select(SocialPost).where(SocialPost.id == post_id))
        post = q.scalar_one_or_none()
        if post and vr.video_url:
            media_ids = list(post.media_asset_ids or [])
            for m in media_ids:
                if m.get("provider_id") == provider_id:
                    m["url"] = vr.video_url
                    m["status"] = "completed"
            post.media_asset_ids = media_ids
            post.pipeline_stage  = "video_ready"
            await db.commit()

    return {
        "provider_id":      provider_id,
        "status":           vr.status,
        "video_url":        vr.video_url,
        "thumbnail_url":    vr.thumbnail_url,
        "duration_seconds": vr.duration_seconds,
        "error":            vr.error,
    }


# ── Full pipeline ─────────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/pipeline")
async def run_pipeline(
    post_id: str,
    data: PipelineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Voice + video + queue in one call."""
    from app.services.content_agent import run_content_pipeline
    result = await run_content_pipeline(
        db, post_id,
        generate_voice=data.generate_voice,
        generate_video=data.generate_video,
        auto_queue=data.auto_queue,
    )
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


# ── Publish ───────────────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/publish")
async def publish_post(
    post_id: str,
    data: PublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Push the final assembled video to the target platform.

    The post must have a video_final or video_raw MediaAsset with a public URL.
    If the video is still at a provider CDN (e.g., HeyGen), use that URL directly.
    """
    q = await db.execute(select(SocialPost).where(SocialPost.id == post_id))
    post = q.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")

    if post.approval_status not in (ApprovalStatus.APPROVED, ApprovalStatus.SCHEDULED):
        raise HTTPException(400, f"Post must be approved before publishing (current: {post.approval_status})")

    # Find best video URL
    media_ids = post.media_asset_ids or []
    video_url = None
    for m in reversed(media_ids):   # prefer most recent
        if m.get("type") in ("video_final", "video_raw") and m.get("url"):
            video_url = m["url"]
            break

    if not video_url:
        raise HTTPException(400, "No video asset found — generate a video first")

    target_platform = data.platform or (post.platform.value if post.platform else None)
    if not target_platform:
        raise HTTPException(400, "No platform specified")

    from app.services.publishers.registry import get_publisher
    publisher = get_publisher(target_platform)

    from app.services.publishers.base import PublishPayload
    payload = PublishPayload(
        video_url=video_url,
        caption=data.caption_override or post.caption or "",
        platform=target_platform,
        hashtags=data.hashtags,
        post_id=post_id,
    )

    result = await publisher.publish(payload)

    if result.success:
        post.approval_status  = ApprovalStatus.PUBLISHED
        post.published_at     = datetime.utcnow()
        post.external_post_id = result.external_post_id
        await db.commit()
        await log_event(db, "content.published", actor_type="user", actor_id=current_user.id,
                        resource_type="social_post", resource_id=post_id,
                        details={"platform": target_platform, "external_id": result.external_post_id})
        await db.commit()
        log.info("content.published", post_id=post_id, platform=target_platform, external_id=result.external_post_id)
    else:
        log.error("content.publish_failed", post_id=post_id, platform=target_platform, error=result.error)

    return {
        "success":          result.success,
        "platform":         target_platform,
        "external_post_id": result.external_post_id,
        "platform_url":     result.platform_url,
        "status":           result.status,
        "error":            result.error,
    }


# ── Creatomate Assembly ───────────────────────────────────────────────────────

@router.post("/posts/{post_id}/assemble")
async def assemble_post(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Layer the raw HeyGen video through Creatomate for branded final output
    (lower thirds, captions, CTA overlay, logo).

    Requires:
      - A video MediaAsset on the post (run /generate-video first)
      - CREATOMATE_API_KEY + template ID for the post's platform
    """
    q = await db.execute(select(SocialPost).where(SocialPost.id == post_id))
    post = q.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Post not found")

    # Find the raw video asset
    video_url = None
    asset_ids = post.media_asset_ids or []
    for aid in reversed(asset_ids):
        aq = await db.execute(
            select(MediaAsset).where(MediaAsset.id == aid, MediaAsset.asset_type.in_(["video", "video_raw"]))
        )
        asset = aq.scalar_one_or_none()
        if asset and asset.file_url:
            video_url = asset.file_url
            break

    if not video_url:
        raise HTTPException(400, "No video asset found on this post. Run /generate-video first.")

    from app.services.providers.creatomate import CreatomateProvider
    provider = CreatomateProvider()

    template_id = provider.get_template_id(post.platform or "tiktok")
    if not template_id:
        raise HTTPException(400, f"No Creatomate template configured for platform '{post.platform}'. "
                                  "Set CREATOMATE_TEMPLATE_ID_* in .env")

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    logo_url = os.getenv("BRAND_LOGO_URL", "")

    result = await provider.render(
        template_id=template_id,
        video_url=video_url,
        caption_text=post.caption or "",
        hook_text=post.hook or "",
        cta_text=post.cta or "",
        logo_url=logo_url,
    )

    if not result.success:
        raise HTTPException(500, f"Creatomate render failed: {result.error}")

    # Save assembled asset record (output_url may still be None if still rendering)
    assembled = MediaAsset(
        name=f"assembled_{post.platform}_{post_id[:8]}",
        asset_type="video_assembled",
        file_url=result.output_url,
        mime_type="video/mp4",
        tags=["assembled", "creatomate", result.render_id or ""],
    )
    db.add(assembled)
    await db.flush()

    post.media_asset_ids = list(asset_ids) + [assembled.id]
    post.pipeline_stage = "assembled"
    await db.commit()

    return {
        "render_id":       result.render_id,
        "status":          result.status,
        "asset_id":        assembled.id,
        "output_url":      result.output_url,
        "pipeline_stage":  "assembled",
        "note": (
            "Render submitted to Creatomate. If status is 'queued' or 'rendering', "
            f"poll GET /content/posts/{post_id}/assemble-status?render_id={result.render_id}"
        ),
    }


@router.get("/posts/{post_id}/assemble-status")
async def assemble_status(
    post_id: str,
    render_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll Creatomate render status. When status = 'succeeded', output_url is ready."""
    from app.services.providers.creatomate import CreatomateProvider
    provider = CreatomateProvider()
    result = await provider.poll_status(render_id)

    if result.status == "succeeded" and result.output_url:
        # Update the assembled MediaAsset with the final URL
        aq = await db.execute(
            select(MediaAsset).where(
                MediaAsset.asset_type == "video_assembled",
                MediaAsset.tags.contains([render_id]),
            )
        )
        asset = aq.scalar_one_or_none()
        if asset:
            asset.file_url = result.output_url
            await db.commit()

    return {
        "render_id":  result.render_id,
        "status":     result.status,
        "output_url": result.output_url,
        "error":      result.error,
    }


# ── Token Refresh (admin convenience) ────────────────────────────────────────

class TokenRefreshRequest(BaseModel):
    platform: str       # "linkedin" | "tiktok"
    refresh_token: str


@router.post("/admin/refresh-token")
async def refresh_platform_token(
    data: TokenRefreshRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Manually refresh an expiring OAuth token for LinkedIn or TikTok.
    After calling this endpoint, update the corresponding ENV var and restart.
    """
    from app.services.token_refresh import refresh_linkedin_token, refresh_tiktok_token

    if data.platform == "linkedin":
        return await refresh_linkedin_token(data.refresh_token)
    elif data.platform == "tiktok":
        return await refresh_tiktok_token(data.refresh_token)
    else:
        raise HTTPException(400, "platform must be 'linkedin' or 'tiktok'")


# ── POST /content/build-campaign ──────────────────────────────────────────────
# JWT-authenticated version of /agent/build-campaign.
# Called by the Content Studio UI (admin app). Clawdbot uses /agent/build-campaign.
# Both call the same underlying ad_campaign_builder service.

class ContentBuildCampaignRequest(BaseModel):
    avatar: str
    product: str
    proof: Optional[str] = None
    market: str = "MD"
    budget_hint: str = "low"
    flyer_id: Optional[int] = None   # attach a generated flyer as the campaign's visual creative


@router.post("/build-campaign")
async def build_campaign_admin(
    data: ContentBuildCampaignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Admin-triggered ad campaign build. Uses JWT auth (not agent key).
    Runs the same 9-step advertising skill chain as /agent/build-campaign.
    Called by the Content Studio → Ad Campaigns tab.

    Pass flyer_id to attach a previously generated flyer as the visual creative.
    The AI will write copy that complements the image, and the flyer will be
    embedded as the hero image in the email sequence.
    """
    from app.services.ad_campaign_builder import build_ad_campaign
    from app.models.flyer import GeneratedFlyer

    # Resolve flyer URL if a flyer_id was provided
    flyer_image_url = None
    if data.flyer_id:
        flyer = (await db.execute(
            select(GeneratedFlyer).where(
                GeneratedFlyer.id == data.flyer_id,
                GeneratedFlyer.status == "complete",
            )
        )).scalar_one_or_none()
        if flyer:
            flyer_image_url = flyer.flyer_image_url
        else:
            raise HTTPException(400, f"Flyer {data.flyer_id} not found or not complete yet.")

    result = await build_ad_campaign(
        db=db,
        avatar=data.avatar,
        product=data.product,
        proof=data.proof,
        market=data.market,
        budget_hint=data.budget_hint,
        flyer_image_url=flyer_image_url,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    await log_event(db, "content.build_campaign", actor_type="user",
                    actor_id=current_user.id, resource_type="campaign",
                    details={"avatar": data.avatar, "product": data.product,
                             "market": data.market, "slug": result.get("campaign_page_slug")})
    await db.commit()
    return result
