"""
Partner (realtor/title/builder) records — reusable co-marketing identities.

Routes:
  GET    /partners              List partners (search= filters name/brokerage)
  POST   /partners              Create
  GET    /partners/{id}         Get one
  PATCH  /partners/{id}         Update
  DELETE /partners/{id}         Remove

Auth: require_agent_key — accepts admin JWT or agent API key. The agent reads
this table to resolve "flyer with Donna" → full co-marketing contact block.
"""

from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_agent_key
from app.middleware.audit import log_event
from app.models.partner import Partner

log = structlog.get_logger()
router = APIRouter(prefix="/partners", tags=["partners"],
                   dependencies=[Depends(require_agent_key)])


class PartnerUpsert(BaseModel):
    name: str
    partner_type: Optional[str] = "realtor"
    brokerage: Optional[str] = None
    license_number: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    headshot_url: Optional[str] = None
    logo_asset_id: Optional[str] = None
    brand_color: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = True


def _partner_dict(p: Partner) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "partner_type": p.partner_type,
        "brokerage": p.brokerage,
        "license_number": p.license_number,
        "phone": p.phone,
        "email": p.email,
        "website": p.website,
        "headshot_url": p.headshot_url,
        "logo_asset_id": p.logo_asset_id,
        "brand_color": p.brand_color,
        "notes": p.notes,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("/")
async def list_partners(
    search: Optional[str] = Query(None),
    partner_type: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """List partners. ?search=donna matches name or brokerage (case-insensitive)."""
    q = select(Partner).order_by(Partner.name)
    if not include_inactive:
        q = q.where(Partner.is_active == True)
    if partner_type:
        q = q.where(Partner.partner_type == partner_type)
    if search:
        like = f"%{search}%"
        q = q.where(or_(Partner.name.ilike(like), Partner.brokerage.ilike(like)))
    rows = (await db.execute(q)).scalars().all()
    return [_partner_dict(p) for p in rows]


@router.post("/", status_code=201)
async def create_partner(body: PartnerUpsert, db: AsyncSession = Depends(get_db)):
    p = Partner(**body.model_dump(exclude_none=True))
    db.add(p)
    await db.commit()
    await db.refresh(p)
    await log_event(db, "partner.created", actor_type="user",
                    resource_type="partner", resource_id=p.id,
                    details={"name": p.name, "type": p.partner_type})
    await db.commit()
    log.info("partner.created", id=p.id, name=p.name)
    return _partner_dict(p)


@router.get("/{partner_id}")
async def get_partner(partner_id: str, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(Partner).where(Partner.id == partner_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Partner not found")
    return _partner_dict(p)


@router.patch("/{partner_id}")
async def update_partner(partner_id: str, body: PartnerUpsert,
                         db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(Partner).where(Partner.id == partner_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Partner not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(p, field, val)
    p.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(p)
    return _partner_dict(p)


@router.delete("/{partner_id}", status_code=204)
async def delete_partner(partner_id: str, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(Partner).where(Partner.id == partner_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Partner not found")
    await db.delete(p)
    await db.commit()
    log.info("partner.deleted", id=partner_id)
