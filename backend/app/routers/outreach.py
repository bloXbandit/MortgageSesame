"""
Campaign outreach engine — API routes.

Prospect lists → scoring → content generation → compliance → approval → send.

Routes:
  POST   /outreach/prospect-lists                  Create a prospect list
  GET    /outreach/prospect-lists                  List all prospect lists
  GET    /outreach/prospect-lists/{id}             Get list details + prospect summary
  DELETE /outreach/prospect-lists/{id}             Delete list (and all prospects)

  POST   /outreach/prospect-lists/{id}/prospects  Bulk import prospects (JSON or CSV row)
  GET    /outreach/prospect-lists/{id}/prospects  Get prospects in a list (paginated + filtered)
  DELETE /outreach/prospects/{id}                  Delete single prospect

  POST   /outreach/prospect-lists/{id}/score       Run scoring engine on all prospects in list
  GET    /outreach/prospect-lists/{id}/score-summary  Score distribution for a list

  POST   /outreach/generate                        Generate content for one prospect
  POST   /outreach/prospect-lists/{id}/generate-batch  Generate batch for a list (A+B grades)
  GET    /outreach/items                            All outreach items (filterable)
  GET    /outreach/items/{id}                       Single outreach item
  PATCH  /outreach/items/{id}                       Update content / status
  DELETE /outreach/items/{id}                       Delete

  POST   /outreach/items/{id}/approve              Approve an item for send
  POST   /outreach/items/{id}/reject               Reject an item
  POST   /outreach/items/{id}/send                 Send a single item via provider

  GET    /outreach/call-tasks                      Warm-lead call queue
  PATCH  /outreach/call-tasks/{id}                 Update task status/notes

  GET    /outreach/suppression                     List suppressed entries
  POST   /outreach/suppression                     Add to suppression
  DELETE /outreach/suppression/{id}                Remove from suppression

  POST   /outreach/webhooks/{provider}             Inbound provider webhooks (delivery/events)
"""

import csv
import io
import uuid
from datetime import datetime
from typing import Optional, List

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, UploadFile, File, Body
from pydantic import BaseModel, field_validator
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.outreach import (
    ProspectList, Prospect, RefiScore, CampaignOutreach,
    QRLink, QREvent, CallTask, SuppressionEntry,
    ProspectSource, ProspectType, ScoreGrade,
    OutreachChannel, OutreachStatus, CallTaskStatus,
)
from app.services.scoring_service import score_prospect_from_dict
from app.services.campaign_writer import get_writer
from app.services.mail_templates import render_mail_template
from app.services.providers.registry import get_provider
from app.routers.auth import get_current_user

log = structlog.get_logger()
router = APIRouter(prefix="/outreach", tags=["outreach"])

from app.config import settings as _s
BOOKING_URL = _s.calcom_link

# ── In-process job tracker (CSV imports + batch scoring) ─────────────────────
# Keyed by job_id → {status, progress, total, errors, result}
# Simple dict is fine for a single-server deployment.
# Swap for Redis if running multiple workers.
_JOBS: dict = {}

def _job_update(job_id: str, **kwargs):
    if job_id in _JOBS:
        _JOBS[job_id].update(kwargs)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ProspectListCreate(BaseModel):
    name: str
    description: Optional[str] = None
    source: str = "csv_upload"
    prospect_type: str = "homeowner"
    state: Optional[str] = None
    county: Optional[str] = None
    zip_codes: Optional[list] = None


class ProspectCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mailing_address: Optional[str] = None
    mailing_city: Optional[str] = None
    mailing_state: Optional[str] = None
    mailing_zip: Optional[str] = None
    prospect_type: Optional[str] = "homeowner"
    property_address: Optional[str] = None
    property_city: Optional[str] = None
    property_state: Optional[str] = None
    property_zip: Optional[str] = None
    property_county: Optional[str] = None
    property_type: Optional[str] = None
    is_owner_occupied: Optional[bool] = None
    is_investment_property: Optional[bool] = None
    purchase_price: Optional[float] = None
    purchase_date: Optional[str] = None
    estimated_current_value: Optional[float] = None
    estimated_equity_pct: Optional[float] = None
    estimated_equity_dollars: Optional[float] = None
    current_loan_amount: Optional[float] = None
    current_rate_estimate: Optional[float] = None
    loan_type: Optional[str] = None
    origination_date: Optional[str] = None
    last_refi_date: Optional[str] = None
    lender_name: Optional[str] = None
    company_name: Optional[str] = None
    license_number: Optional[str] = None
    recent_transactions: Optional[int] = None
    is_do_not_contact: bool = False
    raw_data: Optional[dict] = None


class GenerateRequest(BaseModel):
    prospect_id: str
    channel: str = "email"                  # email / direct_mail / sms / call_task
    campaign_type: str = "refi_rate_reduction"
    template_key: Optional[str] = None     # direct mail template override
    step: int = 1
    campaign_id: Optional[str] = None


class OutreachUpdate(BaseModel):
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    call_script: Optional[str] = None
    status: Optional[str] = None
    rejection_reason: Optional[str] = None


class CallTaskUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    outcome_detail: Optional[str] = None
    callback_scheduled_at: Optional[datetime] = None


class SuppressionCreate(BaseModel):
    value: str                              # email address, phone, or mailing address
    value_type: str                         # email / phone / address
    reason: str = "manual"                  # opt_out / bounce / complaint / manual / dnc
    source: Optional[str] = None
    notes: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prospect_to_score_dict(p: Prospect) -> dict:
    return {
        "current_rate_estimate": p.current_rate_estimate,
        "origination_date": p.origination_date,
        "purchase_date": p.purchase_date,
        "estimated_equity_pct": p.estimated_equity_pct,
        "current_loan_amount": p.current_loan_amount,
        "loan_type": p.loan_type,
        "last_refi_date": p.last_refi_date,
        "is_owner_occupied": p.is_owner_occupied,
        "is_investment_property": p.is_investment_property,
        "prospect_type": p.prospect_type.value if p.prospect_type else "homeowner",
        "is_do_not_contact": p.is_do_not_contact,
        "is_suppressed": p.is_suppressed,
    }


async def _check_suppression(db: AsyncSession, prospect: Prospect) -> bool:
    """Check if prospect matches any suppression entry. Updates prospect.is_suppressed."""
    checks = []
    if prospect.email:
        checks.append(prospect.email.lower())
    if prospect.phone:
        checks.append(prospect.phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", ""))
    if not checks:
        return False

    stmt = select(SuppressionEntry).where(SuppressionEntry.value.in_(checks))
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry:
        prospect.is_suppressed = True
        await db.commit()
        return True
    return False


async def _generate_qr(db: AsyncSession, outreach: CampaignOutreach, destination: str) -> QRLink:
    """Create a QRLink record for an outreach piece."""
    code = uuid.uuid4().hex[:10].upper()
    import os
    base = os.getenv("BACKEND_URL", "http://localhost:8000")
    qr_link = QRLink(
        code=code,
        outreach_id=outreach.id,
        campaign_id=outreach.campaign_id,
        prospect_id=outreach.prospect_id,
        destination_url=destination,
        label=outreach.template_name or outreach.template_key,
    )
    db.add(qr_link)
    outreach.qr_code = code
    outreach.tracking_url = f"{base}/api/v1/r/{code}"
    await db.commit()
    return qr_link


# ── Prospect Lists ────────────────────────────────────────────────────────────

@router.post("/prospect-lists", status_code=201)
async def create_prospect_list(
    body: ProspectListCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pl = ProspectList(
        name=body.name,
        description=body.description,
        source=ProspectSource(body.source) if body.source else ProspectSource.CSV_UPLOAD,
        prospect_type=ProspectType(body.prospect_type) if body.prospect_type else ProspectType.HOMEOWNER,
        state=body.state,
        county=body.county,
        zip_codes=body.zip_codes or [],
        created_by=current_user.id,
    )
    db.add(pl)
    await db.commit()
    await db.refresh(pl)
    log.info("prospect_list.created", id=pl.id, name=pl.name)
    return {"id": pl.id, "name": pl.name, "created_at": pl.created_at}


@router.get("/prospect-lists")
async def list_prospect_lists(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(ProspectList).order_by(ProspectList.created_at.desc())
    )
    lists = result.scalars().all()
    return [
        {
            "id": pl.id,
            "name": pl.name,
            "description": pl.description,
            "source": pl.source,
            "prospect_type": pl.prospect_type,
            "total_records": pl.total_records,
            "scored_count": pl.scored_count,
            "a_target_count": pl.a_target_count,
            "b_target_count": pl.b_target_count,
            "state": pl.state,
            "county": pl.county,
            "created_at": pl.created_at,
        }
        for pl in lists
    ]


@router.get("/prospect-lists/{list_id}")
async def get_prospect_list(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(ProspectList).where(ProspectList.id == list_id))
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(404, "Prospect list not found")

    # Score distribution
    grade_counts = {}
    for grade in ScoreGrade:
        cnt = await db.execute(
            select(func.count(RefiScore.id))
            .join(Prospect, Prospect.id == RefiScore.prospect_id)
            .where(Prospect.prospect_list_id == list_id)
            .where(RefiScore.grade == grade)
        )
        grade_counts[grade.value] = cnt.scalar() or 0

    return {
        "id": pl.id,
        "name": pl.name,
        "description": pl.description,
        "source": pl.source,
        "prospect_type": pl.prospect_type,
        "state": pl.state,
        "county": pl.county,
        "zip_codes": pl.zip_codes,
        "total_records": pl.total_records,
        "scored_count": pl.scored_count,
        "a_target_count": pl.a_target_count,
        "b_target_count": pl.b_target_count,
        "suppressed_count": pl.suppressed_count,
        "grade_distribution": grade_counts,
        "created_at": pl.created_at,
        "updated_at": pl.updated_at,
    }


@router.delete("/prospect-lists/{list_id}", status_code=204)
async def delete_prospect_list(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(ProspectList).where(ProspectList.id == list_id))
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(404, "Prospect list not found")
    await db.delete(pl)
    await db.commit()


# ── Prospects ─────────────────────────────────────────────────────────────────

@router.post("/prospect-lists/{list_id}/prospects", status_code=201)
async def import_prospects(
    list_id: str,
    prospects: List[ProspectCreate],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(ProspectList).where(ProspectList.id == list_id))
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(404, "Prospect list not found")

    added = 0
    suppressed = 0

    for row in prospects:
        p = Prospect(
            prospect_list_id=list_id,
            prospect_type=ProspectType(row.prospect_type) if row.prospect_type else ProspectType.HOMEOWNER,
            **{k: v for k, v in row.model_dump().items() if k != "prospect_type" and v is not None},
        )
        db.add(p)
        added += 1

    pl.total_records = (pl.total_records or 0) + added
    await db.commit()
    log.info("prospects.imported", list_id=list_id, count=added)
    return {"imported": added, "total_in_list": pl.total_records}


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user=Depends(get_current_user),
):
    """Poll import / batch job status."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/prospect-lists/{list_id}/upload-csv", status_code=202)
async def upload_csv_prospects(
    list_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Upload a CSV file of prospects. Maps common column headers automatically.

    Supported column names (case-insensitive, underscores or spaces):
      first_name, last_name, full_name, email, phone,
      mailing_address/address, city/mailing_city, state/mailing_state, zip/mailing_zip,
      property_address, property_city, property_state, property_zip,
      current_rate / rate, current_loan_amount / loan_balance / loan_amount,
      estimated_equity_pct / equity_pct, estimated_equity_dollars / equity_dollars,
      origination_date / orig_date, loan_type, lender_name / lender,
      is_owner_occupied, is_investment, purchase_date, purchase_price,
      do_not_contact / dnc
    """
    result = await db.execute(select(ProspectList).where(ProspectList.id == list_id))
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(404, "Prospect list not found")

    content = await file.read()
    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = {
        "job_id": job_id, "status": "processing", "progress": 0,
        "total": 0, "imported": 0, "errors": [], "list_id": list_id,
        "filename": file.filename,
    }
    background_tasks.add_task(_process_csv_upload, job_id, list_id, content, file.filename or "upload.csv")
    return {"job_id": job_id, "status": "processing", "poll": f"/api/v1/outreach/jobs/{job_id}"}


async def _process_csv_upload(job_id: str, list_id: str, content: bytes, filename: str):
    """Background task: parse CSV and insert prospects."""
    from app.database import AsyncSessionLocal

    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    all_rows = list(reader)
    _job_update(job_id, total=len(all_rows))

    async with AsyncSessionLocal() as db:
        pl_result = await db.execute(select(ProspectList).where(ProspectList.id == list_id))
        pl = pl_result.scalar_one_or_none()
        if not pl:
            _job_update(job_id, status="failed", error="List not found")
            return

        # Inline the alias map (same as synchronous version)
        ALIASES = {
            "first_name": ["first_name", "first name", "firstname"],
            "last_name":  ["last_name", "last name", "lastname"],
            "full_name":  ["full_name", "full name", "name", "owner_name", "owner name"],
            "email":      ["email", "email_address", "email address"],
            "phone":      ["phone", "phone_number", "mobile", "cell"],
            "mailing_address": ["mailing_address", "mailing address", "address", "mail_address"],
            "mailing_city":    ["mailing_city", "city", "mail_city"],
            "mailing_state":   ["mailing_state", "state", "mail_state"],
            "mailing_zip":     ["mailing_zip", "zip", "postal_code", "zip_code"],
            "property_address":  ["property_address", "prop_address", "situs_address", "situs address"],
            "property_city":     ["property_city", "prop_city", "situs_city"],
            "property_state":    ["property_state", "prop_state", "situs_state"],
            "property_zip":      ["property_zip", "prop_zip", "situs_zip"],
            "property_county":   ["property_county", "county"],
            "current_rate_estimate": ["current_rate", "rate", "interest_rate", "rate_estimate", "current_rate_estimate"],
            "current_loan_amount":   ["current_loan_amount", "loan_amount", "loan_balance", "balance", "mortgage_balance"],
            "estimated_equity_pct":  ["estimated_equity_pct", "equity_pct", "equity_%", "equity_percent"],
            "estimated_equity_dollars": ["estimated_equity_dollars", "equity_dollars", "equity_amount", "equity"],
            "estimated_current_value": ["estimated_current_value", "avm", "estimated_value", "home_value", "property_value"],
            "origination_date":  ["origination_date", "orig_date", "loan_date", "open_date"],
            "loan_type":         ["loan_type", "mortgage_type", "loan_program"],
            "lender_name":       ["lender_name", "lender", "current_lender"],
            "purchase_date":     ["purchase_date", "close_date", "closing_date"],
            "purchase_price":    ["purchase_price", "sale_price", "original_price"],
            "is_owner_occupied": ["is_owner_occupied", "owner_occupied", "owner occupied"],
            "is_investment_property": ["is_investment", "investment_property", "investment"],
            "is_do_not_contact": ["do_not_contact", "dnc", "is_do_not_contact"],
            "last_refi_date":    ["last_refi_date", "refi_date", "last_refi"],
            "company_name":      ["company_name", "company", "brokerage", "agency"],
            "license_number":    ["license_number", "license", "realtor_license"],
        }

        def _map_row(row: dict) -> dict:
            norm = {k.lower().replace(" ", "_"): v for k, v in row.items()}
            mapped = {}
            for field, aliases in ALIASES.items():
                for alias in aliases:
                    val = norm.get(alias.replace(" ", "_"))
                    if val is not None and str(val).strip():
                        mapped[field] = str(val).strip()
                        break
            for float_field in ["current_rate_estimate", "current_loan_amount", "estimated_equity_pct",
                                "estimated_equity_dollars", "estimated_current_value", "purchase_price"]:
                if float_field in mapped:
                    try:
                        mapped[float_field] = float(str(mapped[float_field]).replace("$", "").replace(",", "").replace("%", ""))
                    except ValueError:
                        del mapped[float_field]
            for bool_field in ["is_owner_occupied", "is_investment_property", "is_do_not_contact"]:
                if bool_field in mapped:
                    mapped[bool_field] = str(mapped[bool_field]).lower() in ("true", "yes", "1", "y")
            return mapped

        added = 0
        errors = []
        BATCH = 100

        for i, raw_row in enumerate(all_rows):
            try:
                mapped = _map_row(raw_row)
                ptype_str = mapped.pop("prospect_type", None) or pl.prospect_type.value
                p = Prospect(
                    prospect_list_id=list_id,
                    prospect_type=ProspectType(ptype_str) if ptype_str else ProspectType.HOMEOWNER,
                    raw_data=dict(raw_row),
                    **{k: v for k, v in mapped.items()},
                )
                db.add(p)
                added += 1
            except Exception as e:
                errors.append({"row": i + 2, "error": str(e)})

            # Flush every BATCH rows to avoid huge memory usage
            if (i + 1) % BATCH == 0:
                await db.flush()
                _job_update(job_id, progress=i + 1, imported=added)

        pl.total_records = (pl.total_records or 0) + added
        pl.source_file_name = filename
        await db.commit()

    _job_update(job_id,
                status="complete",
                progress=len(all_rows),
                imported=added,
                errors=errors[:20],
                total=len(all_rows))
    log.info("csv_bg.complete", job_id=job_id, list_id=list_id, added=added, errors=len(errors))




@router.get("/prospect-lists/{list_id}/prospects")
async def get_prospects(
    list_id: str,
    grade: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stmt = (
        select(Prospect)
        .where(Prospect.prospect_list_id == list_id)
        .order_by(Prospect.created_at.desc())
        .offset(skip).limit(limit)
    )
    result = await db.execute(stmt)
    prospects = result.scalars().all()

    # Attach latest score to each
    out = []
    for p in prospects:
        score_result = await db.execute(
            select(RefiScore)
            .where(RefiScore.prospect_id == p.id)
            .order_by(RefiScore.scored_at.desc())
            .limit(1)
        )
        score = score_result.scalar_one_or_none()

        row = {
            "id": p.id,
            "full_name": p.full_name or f"{p.first_name or ''} {p.last_name or ''}".strip(),
            "email": p.email,
            "phone": p.phone,
            "property_address": p.property_address,
            "prospect_type": p.prospect_type,
            "current_rate_estimate": p.current_rate_estimate,
            "estimated_equity_pct": p.estimated_equity_pct,
            "loan_type": p.loan_type,
            "is_do_not_contact": p.is_do_not_contact,
            "is_suppressed": p.is_suppressed,
            "score": score.score if score else None,
            "grade": score.grade if score else None,
            "recommended_channel": score.recommended_channel if score else None,
            "recommended_template": score.recommended_template if score else None,
        }
        if grade is None or (score and score.grade.value == grade):
            out.append(row)

    return out


@router.delete("/prospects/{prospect_id}", status_code=204)
async def delete_prospect(
    prospect_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Prospect not found")
    await db.delete(p)
    await db.commit()


# ── Scoring ───────────────────────────────────────────────────────────────────

@router.post("/prospect-lists/{list_id}/score")
async def score_list(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Run scoring engine on all unscored prospects in a list."""
    result = await db.execute(select(ProspectList).where(ProspectList.id == list_id))
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(404, "Prospect list not found")

    all_prospects = await db.execute(
        select(Prospect).where(Prospect.prospect_list_id == list_id)
    )
    prospects = all_prospects.scalars().all()

    scored = 0
    a_count = 0
    b_count = 0
    suppressed = 0

    for p in prospects:
        # Check suppression
        await _check_suppression(db, p)

        data = _prospect_to_score_dict(p)
        sr = score_prospect_from_dict(data)

        # Upsert score (replace most recent for this prospect)
        existing = await db.execute(
            select(RefiScore)
            .where(RefiScore.prospect_id == p.id)
            .order_by(RefiScore.scored_at.desc())
            .limit(1)
        )
        existing_score = existing.scalar_one_or_none()
        if existing_score:
            existing_score.score = sr.score
            existing_score.grade = sr.grade
            existing_score.reason_codes = sr.reason_codes
            existing_score.recommended_channel = sr.recommended_channel
            existing_score.recommended_template = sr.recommended_template
            existing_score.score_details = sr.score_details
            existing_score.scored_at = datetime.utcnow()
        else:
            score_rec = RefiScore(
                prospect_id=p.id,
                score=sr.score,
                grade=sr.grade,
                reason_codes=sr.reason_codes,
                recommended_channel=sr.recommended_channel,
                recommended_template=sr.recommended_template,
                score_details=sr.score_details,
            )
            db.add(score_rec)

        scored += 1
        if sr.grade == ScoreGrade.A_TARGET:
            a_count += 1
        elif sr.grade == ScoreGrade.B_TARGET:
            b_count += 1
        if p.is_suppressed:
            suppressed += 1

    pl.scored_count = scored
    pl.a_target_count = a_count
    pl.b_target_count = b_count
    pl.suppressed_count = suppressed
    await db.commit()

    log.info("score_list.complete", list_id=list_id, scored=scored, a=a_count, b=b_count)
    return {
        "scored": scored,
        "a_target": a_count,
        "b_target": b_count,
        "nurture": scored - a_count - b_count - suppressed,
        "suppressed": suppressed,
    }


@router.get("/prospect-lists/{list_id}/score-summary")
async def score_summary(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(ProspectList).where(ProspectList.id == list_id))
    pl = result.scalar_one_or_none()
    if not pl:
        raise HTTPException(404, "Prospect list not found")

    grade_dist = {}
    for grade in ScoreGrade:
        cnt = await db.execute(
            select(func.count(RefiScore.id))
            .join(Prospect, Prospect.id == RefiScore.prospect_id)
            .where(Prospect.prospect_list_id == list_id)
            .where(RefiScore.grade == grade)
        )
        grade_dist[grade.value] = cnt.scalar() or 0

    channel_dist = {}
    for ch in ["email", "direct_mail", "sms", "call_task"]:
        cnt = await db.execute(
            select(func.count(RefiScore.id))
            .join(Prospect, Prospect.id == RefiScore.prospect_id)
            .where(Prospect.prospect_list_id == list_id)
            .where(RefiScore.recommended_channel == ch)
        )
        channel_dist[ch] = cnt.scalar() or 0

    return {
        "list_id": list_id,
        "total_records": pl.total_records,
        "scored_count": pl.scored_count,
        "grade_distribution": grade_dist,
        "channel_distribution": channel_dist,
    }


# ── Content Generation ────────────────────────────────────────────────────────

@router.post("/generate", status_code=201)
async def generate_outreach(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate a single outreach piece for one prospect."""
    # Fetch prospect
    result = await db.execute(select(Prospect).where(Prospect.id == body.prospect_id))
    prospect = result.scalar_one_or_none()
    if not prospect:
        raise HTTPException(404, "Prospect not found")

    if prospect.is_do_not_contact or prospect.is_suppressed:
        raise HTTPException(400, "Prospect is on DNC/suppression list")

    writer = get_writer()
    channel = OutreachChannel(body.channel)

    # Determine template key
    score_result = await db.execute(
        select(RefiScore).where(RefiScore.prospect_id == prospect.id)
        .order_by(RefiScore.scored_at.desc()).limit(1)
    )
    score = score_result.scalar_one_or_none()
    template_key = body.template_key or (score.recommended_template if score else "refi_certificate")

    outreach = CampaignOutreach(
        campaign_id=body.campaign_id,
        prospect_id=prospect.id,
        channel=channel,
        template_key=template_key,
        status=OutreachStatus.DRAFT,
    )

    if channel == OutreachChannel.EMAIL:
        draft = await writer.generate_email(
            prospect, campaign_type=body.campaign_type, step=body.step
        )
        outreach.subject = draft.subject
        outreach.body_html = draft.body_html
        outreach.body_text = draft.body_text
        outreach.merge_data = draft.merge_data
        outreach.template_name = f"{body.campaign_type} email step {body.step}"

    elif channel == OutreachChannel.DIRECT_MAIL:
        merge_data = await writer.generate_mail_merge_data(prospect, template_key=template_key)
        html = render_mail_template(template_key, merge_data)
        outreach.body_html = html
        outreach.merge_data = merge_data
        outreach.template_name = template_key

    elif channel == OutreachChannel.SMS:
        draft = await writer.generate_sms(
            prospect, campaign_type=body.campaign_type, step=body.step
        )
        outreach.body_text = draft.body
        outreach.template_name = f"{body.campaign_type} sms step {body.step}"

    elif channel == OutreachChannel.CALL_TASK:
        script = await writer.generate_call_script(
            prospect, campaign_type=body.campaign_type
        )
        outreach.call_script = script.pitch
        outreach.merge_data = {
            "opener": script.opener,
            "pitch": script.pitch,
            "talking_points": script.talking_points,
            "objection_handlers": script.objection_handlers,
            "close": script.close,
            "voicemail": script.voicemail,
        }
        outreach.template_name = f"{body.campaign_type} call script"

    db.add(outreach)
    await db.flush()

    # Generate QR link for direct mail and email
    if channel in (OutreachChannel.DIRECT_MAIL, OutreachChannel.EMAIL):
        await _generate_qr(db, outreach, BOOKING_URL)

    await db.commit()
    await db.refresh(outreach)

    log.info("outreach.generated", id=outreach.id, channel=channel, prospect=prospect.id)
    return {
        "id": outreach.id,
        "channel": outreach.channel,
        "template_key": outreach.template_key,
        "subject": outreach.subject,
        "body_text": outreach.body_text,
        "body_html": outreach.body_html,
        "call_script": outreach.call_script,
        "merge_data": outreach.merge_data,
        "qr_code": outreach.qr_code,
        "tracking_url": outreach.tracking_url,
        "status": outreach.status,
    }


@router.post("/prospect-lists/{list_id}/generate-batch", status_code=201)
async def generate_batch(
    list_id: str,
    campaign_type: str = Body("refi_rate_reduction"),
    channel: str = Body("email"),
    step: int = Body(1),
    grades: list = Body(["A_TARGET", "B_TARGET"]),
    max_items: int = Body(100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate outreach for all prospects in a list matching the given grade filter."""
    # Get prospects with matching scores
    grade_enums = [ScoreGrade(g) for g in grades]
    stmt = (
        select(Prospect)
        .join(RefiScore, RefiScore.prospect_id == Prospect.id)
        .where(Prospect.prospect_list_id == list_id)
        .where(RefiScore.grade.in_(grade_enums))
        .where(Prospect.is_do_not_contact == False)
        .where(Prospect.is_suppressed == False)
        .limit(max_items)
    )
    result = await db.execute(stmt)
    prospects = result.scalars().all()

    if not prospects:
        return {"generated": 0, "message": "No prospects found matching grade filter"}

    writer = get_writer()
    generated = 0
    errors = []

    for p in prospects:
        try:
            req = GenerateRequest(
                prospect_id=p.id,
                channel=channel,
                campaign_type=campaign_type,
                step=step,
            )
            # Inline generation (reuse logic from generate_outreach)
            ch = OutreachChannel(channel)
            outreach = CampaignOutreach(
                prospect_id=p.id,
                channel=ch,
                template_key="refi_certificate",
                status=OutreachStatus.DRAFT,
            )

            if ch == OutreachChannel.EMAIL:
                draft = await writer.generate_email(p, campaign_type=campaign_type, step=step)
                outreach.subject = draft.subject
                outreach.body_html = draft.body_html
                outreach.body_text = draft.body_text
                outreach.merge_data = draft.merge_data
            elif ch == OutreachChannel.DIRECT_MAIL:
                score_r = await db.execute(
                    select(RefiScore).where(RefiScore.prospect_id == p.id)
                    .order_by(RefiScore.scored_at.desc()).limit(1)
                )
                score_rec = score_r.scalar_one_or_none()
                tkey = (score_rec.recommended_template if score_rec else None) or "equity_voucher"
                merge = await writer.generate_mail_merge_data(p, template_key=tkey)
                outreach.body_html = render_mail_template(tkey, merge)
                outreach.merge_data = merge
                outreach.template_key = tkey
            elif ch == OutreachChannel.SMS:
                sms = await writer.generate_sms(p, campaign_type=campaign_type, step=step)
                outreach.body_text = sms.body
            elif ch == OutreachChannel.CALL_TASK:
                script = await writer.generate_call_script(p, campaign_type=campaign_type)
                outreach.call_script = script.pitch
                outreach.merge_data = {
                    "talking_points": script.talking_points,
                    "opener": script.opener,
                    "close": script.close,
                    "voicemail": script.voicemail,
                }

            db.add(outreach)
            await db.flush()
            if ch in (OutreachChannel.DIRECT_MAIL, OutreachChannel.EMAIL):
                await _generate_qr(db, outreach, BOOKING_URL)
            generated += 1
        except Exception as e:
            errors.append({"prospect_id": p.id, "error": str(e)})

    await db.commit()
    log.info("batch.generated", list_id=list_id, generated=generated, errors=len(errors))
    return {"generated": generated, "errors": errors[:20]}


# ── Outreach Items ────────────────────────────────────────────────────────────

@router.get("/items")
async def list_outreach_items(
    status: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    campaign_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stmt = select(CampaignOutreach).order_by(CampaignOutreach.created_at.desc())
    if status:
        stmt = stmt.where(CampaignOutreach.status == OutreachStatus(status))
    if channel:
        stmt = stmt.where(CampaignOutreach.channel == OutreachChannel(channel))
    if campaign_id:
        stmt = stmt.where(CampaignOutreach.campaign_id == campaign_id)
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        {
            "id": item.id,
            "channel": item.channel,
            "template_key": item.template_key,
            "template_name": item.template_name,
            "subject": item.subject,
            "status": item.status,
            "prospect_id": item.prospect_id,
            "qr_code": item.qr_code,
            "provider": item.provider,
            "provider_job_id": item.provider_job_id,
            "sent_at": item.sent_at,
            "opened_at": item.opened_at,
            "clicked_at": item.clicked_at,
            "qr_scanned_at": item.qr_scanned_at,
            "created_at": item.created_at,
        }
        for item in items
    ]


@router.get("/items/{item_id}")
async def get_outreach_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(CampaignOutreach).where(CampaignOutreach.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Outreach item not found")
    return {
        "id": item.id,
        "channel": item.channel,
        "campaign_id": item.campaign_id,
        "prospect_id": item.prospect_id,
        "template_key": item.template_key,
        "template_name": item.template_name,
        "subject": item.subject,
        "body_text": item.body_text,
        "body_html": item.body_html,
        "call_script": item.call_script,
        "merge_data": item.merge_data,
        "qr_code": item.qr_code,
        "tracking_url": item.tracking_url,
        "status": item.status,
        "compliance_status": item.compliance_status,
        "compliance_flags": item.compliance_flags,
        "approval_status": item.approval_status,
        "provider": item.provider,
        "provider_job_id": item.provider_job_id,
        "sent_at": item.sent_at,
        "delivered_at": item.delivered_at,
        "opened_at": item.opened_at,
        "clicked_at": item.clicked_at,
        "qr_scanned_at": item.qr_scanned_at,
        "created_at": item.created_at,
    }


@router.patch("/items/{item_id}")
async def update_outreach_item(
    item_id: str,
    body: OutreachUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(CampaignOutreach).where(CampaignOutreach.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Outreach item not found")

    for field, val in body.model_dump(exclude_none=True).items():
        if field == "status":
            setattr(item, field, OutreachStatus(val))
        else:
            setattr(item, field, val)

    await db.commit()
    return {"id": item.id, "status": item.status}


@router.delete("/items/{item_id}", status_code=204)
async def delete_outreach_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(CampaignOutreach).where(CampaignOutreach.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Outreach item not found")
    await db.delete(item)
    await db.commit()


# ── Approval Workflow ─────────────────────────────────────────────────────────

@router.post("/items/{item_id}/approve")
async def approve_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(CampaignOutreach).where(CampaignOutreach.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Outreach item not found")

    item.approval_status = "approved"
    item.approved_by = current_user.id
    item.approved_at = datetime.utcnow()
    item.status = OutreachStatus.APPROVED
    await db.commit()
    log.info("outreach.approved", id=item_id, by=current_user.id)
    return {"id": item.id, "status": item.status, "approved_at": item.approved_at}


@router.post("/items/{item_id}/reject")
async def reject_item(
    item_id: str,
    reason: str = Body(""),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(CampaignOutreach).where(CampaignOutreach.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Outreach item not found")

    item.approval_status = "rejected"
    item.rejection_reason = reason
    item.status = OutreachStatus.REJECTED
    await db.commit()
    return {"id": item.id, "status": item.status}


@router.post("/items/{item_id}/send")
async def send_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Send an approved outreach item via the configured provider."""
    result = await db.execute(select(CampaignOutreach).where(CampaignOutreach.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Outreach item not found")

    if item.status not in (OutreachStatus.APPROVED, OutreachStatus.DRAFT):
        raise HTTPException(400, f"Item status is {item.status} — must be approved or draft to send")

    # Fetch prospect for addressing
    prospect = None
    if item.prospect_id:
        p_result = await db.execute(select(Prospect).where(Prospect.id == item.prospect_id))
        prospect = p_result.scalar_one_or_none()

    if prospect and (prospect.is_do_not_contact or prospect.is_suppressed):
        item.status = OutreachStatus.COMPLIANCE_BLOCKED
        await db.commit()
        raise HTTPException(400, "Prospect is on DNC/suppression list — send blocked")

    try:
        if item.channel == OutreachChannel.EMAIL:
            provider = get_provider("email")
            payload = {
                "to_email": prospect.email if prospect else None,
                "to_name": prospect.full_name if prospect else None,
                "from_email": _s.campaign_from_email or _s.smtp_user or None,
                "from_name": _s.campaign_from_name or _s.banker_name or None,
                "subject": item.subject,
                "html_body": item.body_html,
                "text_body": item.body_text,
                "tags": {"campaign_id": item.campaign_id, "outreach_id": item.id},
            }
            send_result = await provider.send_email(payload)

        elif item.channel == OutreachChannel.DIRECT_MAIL:
            provider = get_provider("direct_mail")
            merge = item.merge_data or {}
            payload = {
                "to_name": merge.get("recipient_name") or (prospect.full_name if prospect else "Homeowner"),
                "to_address": {
                    "line1": merge.get("property_address") or (prospect.mailing_address if prospect else ""),
                    "city": prospect.mailing_city if prospect else "",
                    "state": prospect.mailing_state if prospect else "",
                    "zip": prospect.mailing_zip if prospect else "",
                },
                "from_name": f"{_s.banker_name} | MortgageSesame",
                "from_address": {"line1": "Send Address Here", "city": "City", "state": _s.service_states.split(',')[0].strip()[:2] if _s.service_states else "MD", "zip": "00000"},
                "html_front": item.body_html,
                "mail_type": "postcard",
                "metadata": {"outreach_id": item.id},
                "description": f"MortgageSesame campaign — {item.template_key}",
            }
            send_result = await provider.create_mail_piece(payload)

        elif item.channel == OutreachChannel.SMS:
            provider = get_provider("sms")
            payload = {
                "to_phone": prospect.phone if prospect else None,
                "body": item.body_text,
            }
            send_result = await provider.send_sms(payload)

        elif item.channel == OutreachChannel.CALL_TASK:
            # Call task — create a task record instead of sending
            call_task = CallTask(
                outreach_id=item.id,
                prospect_id=item.prospect_id,
                prospect_name=prospect.full_name if prospect else None,
                phone=prospect.phone if prospect else None,
                property_address=prospect.property_address if prospect else None,
                trigger="manual",
                trigger_detail="Manually queued via send action",
                call_script=item.call_script,
                talking_points=(item.merge_data or {}).get("talking_points", []),
                campaign_context=item.template_name,
                priority=5,
                score=None,
            )
            db.add(call_task)
            item.status = OutreachStatus.QUEUED
            item.sent_at = datetime.utcnow()
            await db.commit()
            return {"id": item.id, "status": item.status, "call_task_id": call_task.id}

        else:
            raise HTTPException(400, f"Unknown channel: {item.channel}")

        # Update item with send result
        item.provider = send_result.provider_id or "mock" if hasattr(send_result, 'provider_id') else "mock"
        item.provider_job_id = getattr(send_result, 'provider_id', None)
        item.status = OutreachStatus.SENT
        item.sent_at = datetime.utcnow()

        if not getattr(send_result, 'success', True):
            item.status = OutreachStatus.FAILED
            item.failed_reason = getattr(send_result, 'error', 'Unknown error')

        await db.commit()
        log.info("outreach.sent", id=item.id, channel=item.channel, provider=item.provider)
        return {
            "id": item.id,
            "status": item.status,
            "provider": item.provider,
            "provider_job_id": item.provider_job_id,
            "sent_at": item.sent_at,
        }

    except Exception as e:
        item.status = OutreachStatus.FAILED
        item.failed_reason = str(e)
        await db.commit()
        log.error("outreach.send_failed", id=item.id, error=str(e))
        raise HTTPException(500, f"Send failed: {str(e)}")


# ── Call Tasks ────────────────────────────────────────────────────────────────

@router.get("/call-tasks")
async def list_call_tasks(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stmt = select(CallTask).order_by(CallTask.priority, CallTask.created_at)
    if status:
        stmt = stmt.where(CallTask.status == CallTaskStatus(status))
    else:
        stmt = stmt.where(CallTask.status == CallTaskStatus.PENDING)
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return [
        {
            "id": t.id,
            "prospect_name": t.prospect_name,
            "phone": t.phone,
            "property_address": t.property_address,
            "trigger": t.trigger,
            "trigger_detail": t.trigger_detail,
            "priority": t.priority,
            "score": t.score,
            "talking_points": t.talking_points,
            "call_script": t.call_script,
            "campaign_context": t.campaign_context,
            "status": t.status,
            "notes": t.notes,
            "callback_scheduled_at": t.callback_scheduled_at,
            "created_at": t.created_at,
        }
        for t in tasks
    ]


@router.patch("/call-tasks/{task_id}")
async def update_call_task(
    task_id: str,
    body: CallTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(CallTask).where(CallTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Call task not found")

    if body.status:
        task.status = CallTaskStatus(body.status)
        if body.status == CallTaskStatus.COMPLETED.value:
            task.completed_at = datetime.utcnow()
    if body.notes:
        task.notes = body.notes
    if body.outcome_detail:
        task.outcome_detail = body.outcome_detail
    if body.callback_scheduled_at:
        task.callback_scheduled_at = body.callback_scheduled_at

    await db.commit()
    return {"id": task.id, "status": task.status}


# ── Suppression ───────────────────────────────────────────────────────────────

@router.get("/suppression")
async def list_suppression(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(SuppressionEntry)
        .order_by(SuppressionEntry.added_at.desc())
        .offset(skip).limit(limit)
    )
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "value": e.value,
            "value_type": e.value_type,
            "reason": e.reason,
            "source": e.source,
            "added_at": e.added_at,
        }
        for e in entries
    ]


@router.post("/suppression", status_code=201)
async def add_suppression(
    body: SuppressionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Check if already exists
    existing = await db.execute(
        select(SuppressionEntry).where(SuppressionEntry.value == body.value.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Already in suppression list")

    entry = SuppressionEntry(
        value=body.value.lower(),
        value_type=body.value_type,
        reason=body.reason,
        source=body.source or "manual",
        notes=body.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"id": entry.id, "value": entry.value, "added_at": entry.added_at}


@router.delete("/suppression/{entry_id}", status_code=204)
async def remove_suppression(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(SuppressionEntry).where(SuppressionEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Suppression entry not found")
    await db.delete(entry)
    await db.commit()


# ── Analytics / Resource Spend ───────────────────────────────────────────────

@router.get("/analytics")
async def campaign_analytics(
    list_id: Optional[str] = Query(None, description="Filter to a single prospect list"),
    days: int = Query(90, ge=1, le=365, description="Lookback window in days"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Campaign performance + resource spend dashboard data.

    Returns:
      - funnel: drafted → sent → delivered → opened → qr_scanned → called → converted
      - by_channel: per-channel counts + estimated cost
      - call_outcomes: call task status breakdown
      - by_list: per-prospect-list breakdown
      - totals: spend estimate, pipeline estimate, ROI ratio
      - cost_assumptions: the $/piece defaults used (overridable via env vars)
    """
    import os
    from datetime import timedelta
    from collections import defaultdict

    # Cost defaults — override via .env
    COST_EMAIL  = float(os.getenv("COST_PER_EMAIL",        "0.003"))
    COST_MAIL   = float(os.getenv("COST_PER_DIRECT_MAIL",  "1.50"))
    COST_SMS    = float(os.getenv("COST_PER_SMS",          "0.015"))
    COMMISSION  = float(os.getenv("COMMISSION_ESTIMATE",   "8000"))
    cost_map    = {
        "email":       COST_EMAIL,
        "direct_mail": COST_MAIL,
        "sms":         COST_SMS,
        "call_task":   0.0,
    }

    since = datetime.utcnow() - timedelta(days=days)

    # ── All outreach items in window ──────────────────────────────────────────
    stmt = select(CampaignOutreach).where(CampaignOutreach.created_at >= since)
    if list_id:
        stmt = (
            stmt.join(Prospect, Prospect.id == CampaignOutreach.prospect_id)
                .where(Prospect.prospect_list_id == list_id)
        )
    result = await db.execute(stmt)
    items = result.scalars().all()

    # ── Call tasks in window ──────────────────────────────────────────────────
    ct_result = await db.execute(
        select(CallTask).where(CallTask.created_at >= since)
    )
    tasks = ct_result.scalars().all()

    # ── Prospect lists (for by-list breakdown) ────────────────────────────────
    lists_result = await db.execute(
        select(ProspectList).order_by(ProspectList.created_at.desc())
    )
    all_lists = lists_result.scalars().all()

    # Build prospect_id → list_id map
    if items:
        pids = list({i.prospect_id for i in items if i.prospect_id})
        if pids:
            p_rows = await db.execute(
                select(Prospect.id, Prospect.prospect_list_id).where(Prospect.id.in_(pids))
            )
            prospect_list_map = {r[0]: r[1] for r in p_rows.all()}
        else:
            prospect_list_map = {}
    else:
        prospect_list_map = {}

    # ── Funnel ────────────────────────────────────────────────────────────────
    sent_items = [i for i in items if i.sent_at]
    funnel = {
        "drafted":    len(items),
        "sent":       len(sent_items),
        "delivered":  len([i for i in items if i.delivered_at]),
        "opened":     len([i for i in items if i.opened_at]),
        "qr_scanned": len([i for i in items if i.qr_scanned_at]),
        "called":     len([t for t in tasks if t.status != CallTaskStatus.PENDING]),
        "converted":  len([t for t in tasks if t.status == CallTaskStatus.CONVERTED]),
    }

    # ── By channel ────────────────────────────────────────────────────────────
    by_channel: dict = {}
    for ch in ["email", "direct_mail", "sms", "call_task"]:
        ch_items = [i for i in items if i.channel and i.channel.value == ch]
        ch_sent  = [i for i in ch_items if i.sent_at]
        by_channel[ch] = {
            "drafted":      len(ch_items),
            "sent":         len(ch_sent),
            "delivered":    len([i for i in ch_items if i.delivered_at]),
            "opened":       len([i for i in ch_items if i.opened_at]),
            "qr_scanned":   len([i for i in ch_items if i.qr_scanned_at]),
            "cost_per_piece": cost_map[ch],
            "cost_estimate":  round(len(ch_sent) * cost_map[ch], 2),
        }
    # Enrich call_task channel with live task stats
    by_channel["call_task"].update({
        "total_tasks":         len(tasks),
        "pending":             len([t for t in tasks if t.status == CallTaskStatus.PENDING]),
        "completed":           len([t for t in tasks if t.status == CallTaskStatus.COMPLETED]),
        "voicemail_left":      len([t for t in tasks if t.status == CallTaskStatus.VOICEMAIL_LEFT]),
        "no_answer":           len([t for t in tasks if t.status == CallTaskStatus.NO_ANSWER]),
        "not_interested":      len([t for t in tasks if t.status == CallTaskStatus.NOT_INTERESTED]),
        "converted":           len([t for t in tasks if t.status == CallTaskStatus.CONVERTED]),
        "callback_scheduled":  len([t for t in tasks if t.status == CallTaskStatus.CALLBACK_SCHEDULED]),
    })

    # ── Call outcomes (top-level shortcut) ────────────────────────────────────
    call_outcomes = {
        "pending":            by_channel["call_task"]["pending"],
        "completed":          by_channel["call_task"]["completed"],
        "voicemail_left":     by_channel["call_task"]["voicemail_left"],
        "no_answer":          by_channel["call_task"]["no_answer"],
        "not_interested":     by_channel["call_task"]["not_interested"],
        "converted":          by_channel["call_task"]["converted"],
        "callback_scheduled": by_channel["call_task"]["callback_scheduled"],
    }

    # ── Per-list breakdown ────────────────────────────────────────────────────
    list_items_map: dict = defaultdict(list)
    for item in items:
        lid = prospect_list_map.get(item.prospect_id) if item.prospect_id else None
        if lid:
            list_items_map[lid].append(item)

    by_list = []
    for pl in all_lists:
        pl_items  = list_items_map.get(pl.id, [])
        pl_sent   = [i for i in pl_items if i.sent_at]
        pl_spend  = sum(cost_map.get(i.channel.value if i.channel else "", 0) for i in pl_sent)
        if not pl_items and pl.total_records == 0:
            continue  # Skip empty lists that have no activity
        by_list.append({
            "list_id":       pl.id,
            "list_name":     pl.name,
            "total_records": pl.total_records or 0,
            "a_targets":     pl.a_target_count or 0,
            "b_targets":     pl.b_target_count or 0,
            "drafted":       len(pl_items),
            "sent":          len(pl_sent),
            "opened":        len([i for i in pl_items if i.opened_at]),
            "qr_scanned":    len([i for i in pl_items if i.qr_scanned_at]),
            "spend_estimate": round(pl_spend, 2),
        })

    # ── Totals ────────────────────────────────────────────────────────────────
    total_spend    = round(sum(ch["cost_estimate"] for ch in by_channel.values()), 2)
    pipeline_value = round(funnel["converted"] * COMMISSION, 2)
    roi_ratio      = round(pipeline_value / total_spend, 1) if total_spend > 0 else 0
    open_rate      = round(funnel["opened"]     / funnel["sent"]       * 100, 1) if funnel["sent"]       > 0 else 0
    scan_rate      = round(funnel["qr_scanned"] / funnel["sent"]       * 100, 1) if funnel["sent"]       > 0 else 0
    conv_rate      = round(funnel["converted"]  / funnel["qr_scanned"] * 100, 1) if funnel["qr_scanned"] > 0 else 0

    return {
        "period_days":       days,
        "since":             since.isoformat(),
        "funnel":            funnel,
        "by_channel":        by_channel,
        "call_outcomes":     call_outcomes,
        "by_list":           by_list,
        "totals": {
            "spend_estimate":   total_spend,
            "pipeline_estimate": pipeline_value,
            "roi_ratio":        roi_ratio,
            "open_rate_pct":    open_rate,
            "scan_rate_pct":    scan_rate,
            "scan_to_conv_pct": conv_rate,
        },
        "cost_assumptions": {
            "email":       COST_EMAIL,
            "direct_mail": COST_MAIL,
            "sms":         COST_SMS,
            "commission":  COMMISSION,
        },
    }


# ── Provider Webhooks ─────────────────────────────────────────────────────────

@router.post("/webhooks/{provider_name}", include_in_schema=False)
async def provider_webhook(
    provider_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Inbound webhook receiver for provider delivery events.
    Accepts JSON from SendGrid, Resend, Lob, PostGrid, SignalWire, Twilio.
    Updates outreach status and creates opt-out suppression entries.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    log.info("webhook.received", provider=provider_name, payload_keys=list(payload.keys()) if isinstance(payload, dict) else "list")

    # Normalize event based on provider
    events = payload if isinstance(payload, list) else [payload]
    for event in events:
        event_type = (
            event.get("event")                    # SendGrid
            or event.get("type")                  # Resend
            or event.get("event_type", "").split(".")[-1]  # Lob
            or event.get("SmsStatus")             # SignalWire/Twilio
            or "unknown"
        )
        msg_id = (
            event.get("sg_message_id")           # SendGrid
            or event.get("data", {}).get("email_id")  # Resend
            or event.get("body", {}).get("id")   # Lob
            or event.get("MessageSid")            # SignalWire
        )

        if msg_id:
            result = await db.execute(
                select(CampaignOutreach).where(CampaignOutreach.provider_message_id == msg_id)
            )
            outreach = result.scalar_one_or_none()
            if outreach:
                now = datetime.utcnow()
                if event_type in ("delivered", "mailed", "delivered"):
                    outreach.delivered_at = now
                    outreach.status = OutreachStatus.DELIVERED
                elif event_type in ("open", "opened"):
                    outreach.opened_at = now
                    outreach.status = OutreachStatus.OPENED
                elif event_type in ("click", "clicked"):
                    outreach.clicked_at = now
                    outreach.status = OutreachStatus.CLICKED
                elif event_type in ("bounce", "bounced", "failed"):
                    outreach.bounced_at = now
                    outreach.status = OutreachStatus.BOUNCED
                elif event_type in ("unsubscribe", "spamreport", "opted_out", "opt_out"):
                    outreach.unsubscribed_at = now
                    outreach.status = OutreachStatus.OPTED_OUT
                    # Add to suppression
                    email_addr = event.get("email") or event.get("data", {}).get("to", [None])[0]
                    if email_addr:
                        existing = await db.execute(
                            select(SuppressionEntry).where(SuppressionEntry.value == email_addr.lower())
                        )
                        if not existing.scalar_one_or_none():
                            db.add(SuppressionEntry(
                                value=email_addr.lower(),
                                value_type="email",
                                reason="opt_out",
                                source=provider_name,
                            ))

        await db.commit()

    return {"received": True, "events_processed": len(events)}
