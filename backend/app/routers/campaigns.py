from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.campaign import Campaign, CampaignType, CampaignStatus, CampaignGoal, Channel
from app.models.user import User
from app.middleware.auth import get_current_user
from app.middleware.audit import log_event

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
