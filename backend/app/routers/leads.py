from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.database import get_db
from app.models.lead import LeadIntake, LeadScore as LeadScoreModel, LoanInterestType, Timeline, CreditScoreRange, IncomeRange, PropertyGoal
from app.models.contact import Contact, ConsentRecord, ConsentStatus, ContactType
from app.services import ai_service
from app.middleware.audit import log_event

router = APIRouter(prefix="/leads", tags=["leads"])


class IntakeSubmit(BaseModel):
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


@router.post("/intake", status_code=201)
async def submit_intake(data: IntakeSubmit, request: Request, db: AsyncSession = Depends(get_db)):
    """Public endpoint — no auth required. Called from the public lead site."""
    intake = LeadIntake(
        **{k: v for k, v in data.model_dump().items() if v is not None},
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
            first_name=data.first_name,
            last_name=data.last_name,
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


@router.get("/")
async def list_intakes(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    from app.middleware.auth import get_current_user
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
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "score": {
                "label": score.score_label,
                "value": score.score_value,
                "recommended_product": score.recommended_product,
                "summary": score.summary,
            } if score else None,
        })
    return out
