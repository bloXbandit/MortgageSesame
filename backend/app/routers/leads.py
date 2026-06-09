from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.database import get_db
from app.models.lead import LeadIntake, LeadScore as LeadScoreModel, LoanInterestType, Timeline, CreditScoreRange, IncomeRange, PropertyGoal, PipelineStatus
from app.models.contact import Contact, ConsentRecord, ConsentStatus, ContactType
from app.models.user import User
from app.services import ai_service
from app.middleware.audit import log_event
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/leads", tags=["leads"])


class IntakeSubmit(BaseModel):
    # Basic contact — micro-intake sends full_name; full form sends first/last separately
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None
    loan_interest_type: Optional[LoanInterestType] = None
    timeline: Optional[Timeline] = None
    credit_score_range: Optional[CreditScoreRange] = None
    income_range: Optional[IncomeRange] = None
    current_rent_mortgage: Optional[str] = None
    cash_available: Optional[str] = None
    property_goal: Optional[PropertyGoal] = None
    consent_email: bool = False
    consent_sms: bool = False
    consent_call: bool = False
    utm_source: Optional[str] = None
    utm_campaign: Optional[str] = None
    # Micro-intake extras
    source: Optional[str] = None   # maps to utm_source if utm_source not set
    notes: Optional[str] = None    # stored in utm_campaign field as context


@router.post("/intake", status_code=201)
async def submit_intake(data: IntakeSubmit, request: Request, db: AsyncSession = Depends(get_db)):
    """Public endpoint — no auth required. Called from the public lead site or micro-intake."""
    # Resolve full_name → first/last if not provided separately
    first = data.first_name
    last = data.last_name
    if data.full_name and not (first or last):
        parts = data.full_name.strip().split(None, 1)
        first = parts[0] if parts else None
        last = parts[1] if len(parts) > 1 else None

    # Resolve source → utm_source, notes → utm_campaign
    utm_src = data.utm_source or data.source
    utm_cam = data.utm_campaign or data.notes

    # Only pass known LeadIntake fields
    known_fields = {
        "first_name": first, "last_name": last,
        "email": str(data.email) if data.email else None,
        "phone": data.phone, "state": data.state, "county": data.county,
        "city": data.city, "loan_interest_type": data.loan_interest_type,
        "timeline": data.timeline, "credit_score_range": data.credit_score_range,
        "income_range": data.income_range,
        "current_rent_mortgage": data.current_rent_mortgage,
        "cash_available": data.cash_available, "property_goal": data.property_goal,
        "consent_email": data.consent_email, "consent_sms": data.consent_sms,
        "consent_call": data.consent_call,
        "utm_source": utm_src, "utm_campaign": utm_cam,
    }
    intake = LeadIntake(
        **{k: v for k, v in known_fields.items() if v is not None},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        source_url=request.headers.get("referer"),
    )
    db.add(intake)
    await db.flush()

    # Create or link contact
    contact = None
    if data.email:
        existing = await db.execute(select(Contact).where(Contact.email == data.email))
        contact = existing.scalar_one_or_none()

    if not contact:
        contact = Contact(
            first_name=first,
            last_name=last,
            email=str(data.email) if data.email else None,
            phone=data.phone,
            city=data.city,
            state=data.state,
            county=data.county,
            contact_type=ContactType.CONSUMER,
            source="public_intake",
            consent_email=data.consent_email,
            consent_sms=data.consent_sms,
            consent_call=data.consent_call,
            consent_status=ConsentStatus.OPTED_IN if (data.consent_email or data.consent_sms or data.consent_call) else ConsentStatus.UNKNOWN,
        )
        db.add(contact)
        await db.flush()

    intake.contact_id = contact.id

    # Record consent
    for channel, granted in [("email", data.consent_email), ("sms", data.consent_sms), ("call", data.consent_call)]:
        if granted:
            cr = ConsentRecord(
                contact_id=contact.id,
                channel=channel,
                status="opted_in",
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                source_url=request.headers.get("referer"),
            )
            db.add(cr)

    await db.flush()

    # AI scoring (non-blocking — if it fails, intake still saves)
    score_data = None
    try:
        intake_dict = data.model_dump()
        score_data = await ai_service.score_lead(intake_dict)
        score = LeadScoreModel(
            intake_id=intake.id,
            score_value=score_data.get("score_value"),
            score_label=score_data.get("score_label"),
            recommended_product=score_data.get("recommended_product"),
            readiness_score=score_data.get("readiness_score"),
            summary=score_data.get("summary"),
            questions_for_call=score_data.get("questions_for_call"),
            recommended_cta=score_data.get("recommended_cta"),
            compliance_response=score_data.get("compliance_response"),
        )
        db.add(score)
    except Exception:
        pass

    await db.commit()
    await log_event(db, "lead.intake_submit", actor_type="public", resource_type="lead_intake", resource_id=intake.id,
                    ip_address=request.client.host)
    await db.commit()

    return {
        "intake_id": intake.id,
        "message": score_data.get("compliance_response", "Thank you! We'll be in touch shortly.") if score_data else "Thank you! We'll be in touch shortly.",
        "recommended_cta": score_data.get("recommended_cta") if score_data else None,
    }


@router.get("/{intake_id}")
async def get_lead_detail(intake_id: str, db: AsyncSession = Depends(get_db)):
    """Full lead profile — all intake fields, complete score data, notes."""
    result = await db.execute(select(LeadIntake).where(LeadIntake.id == intake_id))
    intake = result.scalar_one_or_none()
    if not intake:
        raise HTTPException(404, "Lead not found")
    score_q = await db.execute(select(LeadScoreModel).where(LeadScoreModel.intake_id == intake_id))
    score = score_q.scalar_one_or_none()
    notes = (intake.raw_answers or {}).get("_notes", "") if intake.raw_answers else ""
    return {
        "id": intake.id,
        "name": f"{intake.first_name or ''} {intake.last_name or ''}".strip(),
        "first_name": intake.first_name,
        "last_name": intake.last_name,
        "email": intake.email,
        "phone": intake.phone,
        "state": intake.state,
        "county": intake.county,
        "city": intake.city,
        "loan_interest_type": intake.loan_interest_type,
        "timeline": intake.timeline,
        "credit_score_range": intake.credit_score_range,
        "income_range": intake.income_range,
        "current_rent_mortgage": intake.current_rent_mortgage,
        "cash_available": intake.cash_available,
        "property_goal": intake.property_goal,
        "consent_email": intake.consent_email,
        "consent_sms": intake.consent_sms,
        "consent_call": intake.consent_call,
        "utm_source": intake.utm_source,
        "contact_id": intake.contact_id,
        "pipeline_status": intake.pipeline_status or "new",
        "notes": notes,
        "created_at": intake.created_at.isoformat() if intake.created_at else None,
        "score": {
            "label": score.score_label,
            "value": score.score_value,
            "readiness_score": score.readiness_score,
            "recommended_product": score.recommended_product,
            "summary": score.summary,
            "questions_for_call": score.questions_for_call or [],
            "recommended_cta": score.recommended_cta,
            "compliance_response": score.compliance_response,
        } if score else None,
    }


class NotesUpdate(BaseModel):
    notes: str


@router.patch("/{intake_id}/notes")
async def update_lead_notes(intake_id: str, data: NotesUpdate, db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    result = await db.execute(select(LeadIntake).where(LeadIntake.id == intake_id))
    intake = result.scalar_one_or_none()
    if not intake:
        raise HTTPException(404, "Lead not found")
    existing = dict(intake.raw_answers or {})
    existing["_notes"] = data.notes
    intake.raw_answers = existing
    await db.commit()
    return {"success": True}


class StatusUpdate(BaseModel):
    pipeline_status: PipelineStatus


@router.patch("/{intake_id}/status")
async def update_lead_status(intake_id: str, data: StatusUpdate, db: AsyncSession = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    result = await db.execute(select(LeadIntake).where(LeadIntake.id == intake_id))
    intake = result.scalar_one_or_none()
    if not intake:
        raise HTTPException(404, "Lead not found")
    intake.pipeline_status = data.pipeline_status.value
    await db.commit()
    await log_event(db, "lead.status_update", actor_type="user", actor_id=current_user.id,
                    resource_type="lead_intake", resource_id=intake_id,
                    details={"pipeline_status": data.pipeline_status.value})
    await db.commit()
    return {"id": intake_id, "pipeline_status": intake.pipeline_status}


@router.post("/cal-booking", status_code=200, include_in_schema=False)
async def cal_booking_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Cal.com webhook — fired on BOOKING_CREATED.
    Payload shape: { triggerEvent: "BOOKING_CREATED", payload: { attendees: [{name, email}], startTime, title } }
    Finds the lead by email and marks pipeline_status = appointment_set.
    If no lead exists, creates a minimal one.
    Cal.com webhook secret validation is optional — add CALCOM_SECRET to .env and
    check the cal-signature header if you want to lock this down.
    """
    try:
        body = await request.json()
    except Exception:
        return {"received": True, "error": "invalid json"}

    # Cal.com sends { triggerEvent, payload: {...} } or just the payload directly
    booking = body.get("payload", body)
    attendees = booking.get("attendees", [])
    email = next((a.get("email") for a in attendees if a.get("email")), None)
    name  = next((a.get("name")  for a in attendees if a.get("name")),  None)
    start_time = booking.get("startTime") or booking.get("startTimeUtc") or ""
    title = booking.get("title") or booking.get("eventTitle") or "Consultation"

    if not email:
        return {"received": True, "matched": False, "reason": "no_email_in_payload"}

    # Find most recent lead by email
    result = await db.execute(
        select(LeadIntake).where(LeadIntake.email == email)
        .order_by(LeadIntake.created_at.desc()).limit(1)
    )
    intake = result.scalar_one_or_none()

    if intake:
        intake.pipeline_status = PipelineStatus.APPOINTMENT_SET.value
        existing = dict(intake.raw_answers or {})
        existing["_booking"] = f"Booked: {title} at {start_time}"
        intake.raw_answers = existing
        matched = True
    else:
        # No existing lead — create one from the booking
        parts = (name or "").strip().split(None, 1)
        intake = LeadIntake(
            first_name=parts[0] if parts else None,
            last_name=parts[1] if len(parts) > 1 else None,
            email=email,
            pipeline_status=PipelineStatus.APPOINTMENT_SET.value,
            utm_source="cal_booking",
            consent_call=True,
            raw_answers={"_booking": f"Booked: {title} at {start_time}"},
        )
        db.add(intake)
        matched = False

    await db.commit()
    await log_event(db, "lead.cal_booking", actor_type="public", resource_type="lead_intake",
                    resource_id=intake.id, ip_address=request.client.host if request.client else None,
                    details={"email": email, "title": title, "start_time": start_time, "created_new": not matched})
    await db.commit()
    return {"received": True, "matched": matched, "intake_id": intake.id}


@router.get("/")
async def list_intakes(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(LeadIntake).order_by(LeadIntake.created_at.desc()).limit(limit)
    )
    intakes = result.scalars().all()
    out = []
    for i in intakes:
        score_q = await db.execute(select(LeadScoreModel).where(LeadScoreModel.intake_id == i.id))
        score = score_q.scalar_one_or_none()
        out.append({
            "id": i.id,
            "name": f"{i.first_name or ''} {i.last_name or ''}".strip(),
            "email": i.email,
            "phone": i.phone,
            "loan_interest_type": i.loan_interest_type,
            "timeline": i.timeline,
            "state": i.state,
            "pipeline_status": i.pipeline_status or "new",
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "score": {
                "label": score.score_label,
                "value": score.score_value,
                "recommended_product": score.recommended_product,
                "summary": score.summary,
            } if score else None,
        })
    return out
