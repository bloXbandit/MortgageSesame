from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.compliance import AuditLog
from typing import Optional


async def log_event(
    db: AsyncSession,
    action: str,
    actor_type: str = "system",
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    channel: Optional[str] = None,
    status: Optional[str] = "success",
):
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        channel=channel,
        status=status,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    await db.flush()
