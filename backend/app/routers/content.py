from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.content import SocialPost, ContentPlatform, ContentCategory, ApprovalStatus
from app.models.user import User
from app.middleware.auth import get_current_user
from app.middleware.audit import log_event
from app.services import ai_service
from app.services.compliance import check_content

router = APIRouter(prefix="/content", tags=["content"])


class ContentGenerateRequest(BaseModel):
    platform: ContentPlatform
    category: ContentCategory
    product_id: Optional[str] = None
    custom_context: Optional[str] = None


class ApprovalAction(BaseModel):
    action: str  # approve | reject | needs_edit
    rejection_reason: Optional[str] = None
    scheduled_date: Optional[datetime] = None


@router.get("/posts")
async def list_posts(
    platform: Optional[ContentPlatform] = None,
    status: Optional[ApprovalStatus] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(SocialPost).order_by(SocialPost.created_at.desc()).limit(limit)
    if platform:
        q = q.where(SocialPost.platform == platform)
    if status:
        q = q.where(SocialPost.approval_status == status)
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

    banker_voice = current_user.brand_voice or ""
    content = await ai_service.generate_content(data.platform, data.category, product_context, banker_voice)
    compliance = check_content(
        (content.get("caption") or "") + " " + (content.get("script") or ""),
        is_ad=True,
    )

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
        compliance_notes=content.get("compliance_notes"),
        is_fictional_example=content.get("is_fictional_example", False),
        approval_status=ApprovalStatus.PENDING,
        generated_by="user",
        created_by=current_user.id,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    return {
        "post": _serialize(post),
        "compliance": {"passed": compliance.passed, "flags": compliance.flags},
    }


@router.patch("/{post_id}/approve")
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

    await db.commit()
    await log_event(db, f"content.{data.action}", actor_type="user", actor_id=current_user.id,
                    resource_type="social_post", resource_id=post_id)
    await db.commit()
    return _serialize(post)


def _serialize(p: SocialPost) -> dict:
    return {
        "id": p.id,
        "platform": p.platform,
        "category": p.category,
        "hook": p.hook,
        "script": p.script,
        "caption": p.caption,
        "cta": p.cta,
        "visual_concept": p.visual_concept,
        "image_prompt": p.image_prompt,
        "voiceover_script": p.voiceover_script,
        "compliance_notes": p.compliance_notes,
        "is_fictional_example": p.is_fictional_example,
        "approval_status": p.approval_status,
        "scheduled_date": p.scheduled_date.isoformat() if p.scheduled_date else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
