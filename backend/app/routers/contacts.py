import io
import csv
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.contact import Contact, ContactSource, ConsentRecord, OptOut, ContactType, ConsentStatus
from app.models.user import User
from app.middleware.auth import get_current_user
from app.middleware.audit import log_event

router = APIRouter(prefix="/contacts", tags=["contacts"])


class ContactCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    role_title: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    zip_code: Optional[str] = None
    contact_type: ContactType = ContactType.CONSUMER
    source: Optional[str] = None
    tags: list[str] = []
    notes: Optional[str] = None
    consent_email: bool = False
    consent_sms: bool = False
    consent_call: bool = False


@router.get("/")
async def list_contacts(
    contact_type: Optional[ContactType] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Contact).where(Contact.is_dnc == False, Contact.is_opted_out == False)
    if contact_type:
        q = q.where(Contact.contact_type == contact_type)
    if search:
        q = q.where(or_(
            Contact.first_name.ilike(f"%{search}%"),
            Contact.last_name.ilike(f"%{search}%"),
            Contact.email.ilike(f"%{search}%"),
            Contact.company.ilike(f"%{search}%"),
        ))
    q = q.order_by(Contact.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return [_serialize(c) for c in result.scalars().all()]


@router.get("/{contact_id}")
async def get_contact(contact_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Contact not found")
    return _serialize(c)


@router.post("/", status_code=201)
async def create_contact(data: ContactCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    c = Contact(**data.model_dump(), created_by=current_user.id)
    if data.consent_email or data.consent_sms or data.consent_call:
        c.consent_status = ConsentStatus.OPTED_IN
    db.add(c)
    await db.flush()

    src = ContactSource(contact_id=c.id, source_type="manual", source_detail="admin dashboard")
    db.add(src)
    await db.commit()
    await db.refresh(c)
    return _serialize(c)


@router.patch("/{contact_id}/dnc")
async def mark_dnc(contact_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Contact not found")
    c.is_dnc = True
    c.consent_status = ConsentStatus.DNC
    opt = OptOut(contact_id=c.id, channel="all", identifier=c.email or c.phone or contact_id, reason="manually marked DNC")
    db.add(opt)
    await db.commit()
    await log_event(db, "contact.dnc", actor_type="user", actor_id=current_user.id,
                    resource_type="contact", resource_id=contact_id)
    await db.commit()
    return {"status": "marked_dnc"}


@router.post("/import/csv")
async def import_csv(
    file: UploadFile = File(...),
    source_name: str = "csv_import",
    contact_type: ContactType = ContactType.CONSUMER,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    FIELD_MAP = {
        "first name": "first_name", "firstname": "first_name", "first": "first_name",
        "last name": "last_name", "lastname": "last_name", "last": "last_name",
        "email": "email", "email address": "email",
        "phone": "phone", "phone number": "phone", "cell": "phone", "mobile": "phone",
        "company": "company", "business": "company",
        "city": "city", "state": "state", "county": "county", "zip": "zip_code",
        "address": "address", "notes": "notes", "tags": "tags",
    }

    created = 0
    skipped = 0
    for row in rows:
        normalized = {FIELD_MAP.get(k.strip().lower(), k.strip().lower()): v.strip() for k, v in row.items() if v}
        email = normalized.get("email")

        # deduplicate by email
        if email:
            existing = await db.execute(select(Contact).where(Contact.email == email))
            if existing.scalar_one_or_none():
                skipped += 1
                continue

        c = Contact(
            first_name=normalized.get("first_name"),
            last_name=normalized.get("last_name"),
            email=email,
            phone=normalized.get("phone"),
            company=normalized.get("company"),
            city=normalized.get("city"),
            state=normalized.get("state"),
            county=normalized.get("county"),
            zip_code=normalized.get("zip_code"),
            notes=normalized.get("notes"),
            contact_type=contact_type,
            source=source_name,
            created_by=current_user.id,
        )
        db.add(c)
        await db.flush()
        src = ContactSource(contact_id=c.id, source_type="csv", source_detail=source_name, uploaded_filename=file.filename)
        db.add(src)
        created += 1

    await db.commit()
    await log_event(db, "contact.csv_import", actor_type="user", actor_id=current_user.id,
                    details={"created": created, "skipped": skipped, "filename": file.filename})
    await db.commit()
    return {"created": created, "skipped": skipped, "total_rows": len(rows)}


def _serialize(c: Contact) -> dict:
    return {
        "id": c.id,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "full_name": f"{c.first_name or ''} {c.last_name or ''}".strip(),
        "email": c.email,
        "phone": c.phone,
        "company": c.company,
        "role_title": c.role_title,
        "city": c.city,
        "state": c.state,
        "county": c.county,
        "contact_type": c.contact_type,
        "source": c.source,
        "tags": c.tags or [],
        "lead_score": c.lead_score,
        "consent_status": c.consent_status,
        "consent_email": c.consent_email,
        "consent_sms": c.consent_sms,
        "is_dnc": c.is_dnc,
        "is_opted_out": c.is_opted_out,
        "last_contacted_at": c.last_contacted_at.isoformat() if c.last_contacted_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
