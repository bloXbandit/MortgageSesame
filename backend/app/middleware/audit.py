from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.compliance import AuditLog


async def log_event(
    db: AsyncSession,
    action: str,
    actor_type: str = "system",
    actor_id: str | None = None,
    actor_name: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    channel: str | None = None,
    status: str | None = "success",
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
