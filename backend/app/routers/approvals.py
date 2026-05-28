from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.agent import ApprovalQueue
from app.models.user import User
from app.middleware.auth import get_current_user
from app.middleware.audit import log_event

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ReviewAction(BaseModel):
    action: str  # approve | reject | edit
    rejection_reason: Optional[str] = None


@router.get("/")
async def list_approvals(
    status: str = "pending",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(ApprovalQueue).order_by(
        ApprovalQueue.priority.desc(), ApprovalQueue.created_at.asc()
    )
    if status != "all":
        q = q.where(ApprovalQueue.status == status)
    result = await db.execute(q)
    items = result.scalars().all()
    return [
        {
            "id": i.id,
            "item_type": i.item_type,
            "item_id": i.item_id,
            "title": i.title,
            "preview": i.preview,
            "status": i.status,
            "priority": i.priority,
            "created_by": i.created_by,
            "created_at": i.created_at.isoformat(),
        }
        for i in items
    ]


@router.post("/{approval_id}/review")
async def review_approval(
    approval_id: str,
    data: ReviewAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(ApprovalQueue).where(ApprovalQueue.id == approval_id))
    item = q.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Approval item not found")

    item.status = data.action
    item.reviewed_by = current_user.id
    item.reviewed_at = datetime.utcnow()
    item.rejection_reason = data.rejection_reason

    await db.commit()
    await log_event(db, f"approval.{data.action}", actor_type="user", actor_id=current_user.id,
                    resource_type=item.item_type, resource_id=item.item_id)
    await db.commit()
    return {"id": item.id, "status": item.status}
