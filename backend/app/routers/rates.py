"""
Mortgage rate endpoints.
- GET /rates/current  — today's snapshot (admin override → most recent override → FRED live)
- GET /rates/ticker   — formatted list for the scrolling strip
- POST /rates/admin/update  — admin sets today's rates (requires auth)
- POST /rates/admin/sync-fred — pull FRED into DB as non-override (requires auth)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.config import settings as _s
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.hub import RateSnapshot, RateAlert
from app.middleware.auth import get_current_user
from app.middleware.audit import log_event
from app.models.user import User
from app.services.fred_service import fetch_fred_snapshot, fetch_fred_two_weeks

router = APIRouter(prefix="/rates", tags=["rates"])

# Ordered for display priority in ticker
TICKER_FIELDS = [
    ("rate_conventional_30", "Conv 30yr"),
    ("rate_fha_30",           "FHA 30yr"),
    ("rate_conventional_15",  "Conv 15yr"),
    ("rate_va_30",            "VA 30yr"),
    ("rate_usda_30",          "USDA 30yr"),
    ("rate_dscr",             "DSCR"),
    ("rate_jumbo_30",         "Jumbo 30yr"),
    ("rate_heloc_prime_plus", "HELOC"),
]


RATE_FIELDS = [
    "rate_conventional_30", "rate_conventional_15", "rate_fha_30",
    "rate_va_30", "rate_usda_30", "rate_dscr", "rate_heloc_prime_plus", "rate_jumbo_30",
]


async def _get_filled_rates(db: AsyncSession) -> dict:
    """
    Returns a fully-filled rate dict by merging (in priority order):
      1. Today's snapshot (manual override or FRED sync for today)
      2. Per-field fill-forward from recent history (fills any nulls product-by-product)
      3. Live FRED pull (for any fields still null after history scan)

    This means a partial manual entry — e.g. only Conv 30yr entered today —
    still shows correct FHA / VA / HELOC / etc. values from the most recent
    available data for each product rather than returning null.
    """
    today = date.today().isoformat()

    # Step 1 — today's record (admin override or FRED sync)
    result = await db.execute(
        select(RateSnapshot).where(RateSnapshot.snapshot_date == today)
    )
    today_snap = result.scalar_one_or_none()

    if today_snap:
        base = _snapshot_to_dict(today_snap)
    else:
        # No today record — use most recent snapshot as starting point
        result = await db.execute(
            select(RateSnapshot).order_by(desc(RateSnapshot.snapshot_date)).limit(1)
        )
        recent = result.scalar_one_or_none()
        if recent:
            base = _snapshot_to_dict(recent)
            base["snapshot_date"] = today   # surface as "today" even if data is from last week
        else:
            base = {
                "snapshot_date": today,
                "source": None,
                "is_admin_override": False,
                "notes": None,
                **{f: None for f in RATE_FIELDS},
            }

    # Step 2 — per-field fill-forward from history for any null fields
    # Only relevant if we have today's record but it is partially filled (manual entry)
    null_fields = [f for f in RATE_FIELDS if base.get(f) is None]
    if null_fields and today_snap:
        result = await db.execute(
            select(RateSnapshot)
            .where(RateSnapshot.snapshot_date < today)
            .order_by(desc(RateSnapshot.snapshot_date))
            .limit(10)
        )
        for snap in result.scalars().all():
            if not null_fields:
                break
            still_null = []
            for field in null_fields:
                val = getattr(snap, field, None)
                if val is not None:
                    base[field] = val
                else:
                    still_null.append(field)
            null_fields = still_null

    # Step 3 — live FRED fallback for any fields still null after history scan
    if any(base.get(f) is None for f in RATE_FIELDS):
        try:
            fred = await fetch_fred_snapshot()
            for field in RATE_FIELDS:
                if base.get(field) is None:
                    base[field] = fred.get(field)
            if not base.get("source"):
                base["source"] = "fred_live"
                base["notes"] = "Auto-pulled from FRED — no admin rates set yet."
        except Exception:
            pass

    if not base.get("source"):
        base["source"] = "none"

    return base


def _snapshot_to_dict(snapshot: RateSnapshot) -> dict:
    return {
        "snapshot_date": snapshot.snapshot_date,
        "source": snapshot.source,
        "is_admin_override": snapshot.is_admin_override,
        "notes": snapshot.notes,
        "rate_conventional_30": snapshot.rate_conventional_30,
        "rate_conventional_15": snapshot.rate_conventional_15,
        "rate_fha_30": snapshot.rate_fha_30,
        "rate_va_30": snapshot.rate_va_30,
        "rate_usda_30": snapshot.rate_usda_30,
        "rate_dscr": snapshot.rate_dscr,
        "rate_heloc_prime_plus": snapshot.rate_heloc_prime_plus,
        "rate_jumbo_30": snapshot.rate_jumbo_30,
    }


@router.get("/current")
async def get_current_rates(db: AsyncSession = Depends(get_db)):
    try:
        return await _get_filled_rates(db)
    except Exception:
        raise HTTPException(status_code=503, detail="Rate data temporarily unavailable")


@router.get("/ticker")
async def get_ticker(db: AsyncSession = Depends(get_db)):
    """
    Returns formatted ticker items for the scrolling rate strip on the public site.

    Change direction compares to the PREVIOUS available snapshot (not yesterday),
    because FRED data is weekly (Thursdays). If the only data we have is weekly
    FRED snapshots, change = this week vs last week. If admin enters rates daily,
    change = today vs yesterday. Either way the arrows are correct.
    """
    rates = await get_current_rates(db)

    # Pull the two most recent ACTUAL snapshots from the DB for trend comparison.
    # We do NOT use rates["snapshot_date"] here — that value is artificially set to
    # today's date even when the underlying data comes from last week's FRED snapshot,
    # which would make the "previous" query find the same snapshot as "current".
    curr_snapshot = None
    prev_snapshot = None
    try:
        result = await db.execute(
            select(RateSnapshot)
            .order_by(desc(RateSnapshot.snapshot_date))
            .limit(2)
        )
        rows = result.scalars().all()
        if rows:
            curr_snapshot = rows[0]
        if len(rows) > 1:
            prev_snapshot = rows[1]
    except Exception:
        pass

    today = curr_snapshot.snapshot_date if curr_snapshot else rates["snapshot_date"]

    prev_rates = _snapshot_to_dict(prev_snapshot) if prev_snapshot else {}

    # Determine change period label for the UI
    change_period = "day"
    if prev_snapshot and today and prev_snapshot.snapshot_date:
        try:
            today_dt = datetime.strptime(today, "%Y-%m-%d").date()
            prev_dt  = datetime.strptime(prev_snapshot.snapshot_date, "%Y-%m-%d").date()
            gap_days = (today_dt - prev_dt).days
            if gap_days >= 6:
                change_period = "week"
            elif gap_days > 1:
                change_period = f"{gap_days}d"
        except Exception:
            pass

    items = []
    for field, label in TICKER_FIELDS:
        val      = rates.get(field)
        prev_val = prev_rates.get(field) if prev_rates else None

        change = "flat"
        delta  = 0.0
        if val is not None and prev_val is not None:
            delta = round(val - prev_val, 3)
            if delta > 0.001:
                change = "up"
            elif delta < -0.001:
                change = "down"

        items.append({
            "label":  label,
            "rate":   val,
            "change": change,
            "delta":  delta,
            "display": f"{label}  {val:.2f}%" if val is not None else label,
        })

    return {
        "items":         items,
        "as_of":         today,
        "source":        rates["source"],
        "change_period": change_period,   # "day" | "week" | "Nd" — for ticker label
        "disclaimer": (
            f"Example rates for educational purposes only. Not a rate lock or commitment to lend. "
            f"Rates change based on market conditions, credit profile, and loan details. "
            f"Contact us for your personalized rate quote. NMLS #{_s.banker_nmls}."
        ),
    }


# ── Admin: manual rate entry ──────────────────────────────────────────────────

class RateUpdateRequest(BaseModel):
    rate_conventional_30: Optional[float] = None
    rate_conventional_15: Optional[float] = None
    rate_fha_30: Optional[float] = None
    rate_va_30: Optional[float] = None
    rate_usda_30: Optional[float] = None
    rate_dscr: Optional[float] = None
    rate_heloc_prime_plus: Optional[float] = None
    rate_jumbo_30: Optional[float] = None
    notes: Optional[str] = None
    snapshot_date: Optional[str] = None  # defaults to today


@router.post("/admin/update")
async def admin_update_rates(
    data: RateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set or update today's rate snapshot (admin override). Upserts by date."""
    target_date = data.snapshot_date or date.today().isoformat()

    result = await db.execute(
        select(RateSnapshot).where(RateSnapshot.snapshot_date == target_date)
    )
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        snapshot = RateSnapshot(snapshot_date=target_date)
        db.add(snapshot)

    fields = [
        "rate_conventional_30", "rate_conventional_15", "rate_fha_30",
        "rate_va_30", "rate_usda_30", "rate_dscr", "rate_heloc_prime_plus", "rate_jumbo_30",
    ]
    for field in fields:
        val = getattr(data, field)
        if val is not None:
            setattr(snapshot, field, val)

    snapshot.source = "manual"
    snapshot.is_admin_override = True
    snapshot.notes = data.notes
    snapshot.created_by = current_user.id

    await db.commit()
    await db.refresh(snapshot)

    # Check rate alerts against newly saved rates
    saved_rates = {f: getattr(snapshot, f) for f in [
        "rate_conventional_30", "rate_conventional_15", "rate_fha_30",
        "rate_va_30", "rate_usda_30", "rate_dscr", "rate_heloc_prime_plus", "rate_jumbo_30",
    ] if getattr(snapshot, f) is not None}
    if saved_rates:
        await _check_alerts(db, saved_rates)
        await db.commit()

    return {"success": True, "snapshot_date": snapshot.snapshot_date}


@router.post("/admin/sync-fred")
async def sync_fred(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pull the latest TWO weeks of PMMS data from FRED and upsert as dated snapshots.

    Acts as a FULL RESET — any manual override saved for today is deleted so that
    _get_filled_rates falls back to the freshly-written FRED snapshots.

    Subsequent partial manual saves will still fill in only the fields you changed;
    everything else continues to come from the last FRED snapshot.
    Click Pull FRED Data again at any time to reset back to pure FRED values.
    """
    fred_data = await fetch_fred_two_weeks()

    # No key or bad key
    if not fred_data["has_key"] or fred_data["error"]:
        return {
            "success": False,
            "needs_key": not fred_data["has_key"],
            "message": fred_data["error"] or "FRED fetch failed — check your API key.",
        }

    rate_fields = [
        "rate_conventional_30", "rate_conventional_15", "rate_fha_30",
        "rate_va_30", "rate_usda_30", "rate_dscr", "rate_heloc_prime_plus", "rate_jumbo_30",
    ]

    # ── Full reset: delete today's manual snapshot so FRED data takes over ───
    today = date.today().isoformat()
    result = await db.execute(
        select(RateSnapshot).where(
            RateSnapshot.snapshot_date == today,
            RateSnapshot.is_admin_override == True,
        )
    )
    todays_manual = result.scalar_one_or_none()
    if todays_manual:
        await db.delete(todays_manual)

    # ── Save the two FRED weeks ───────────────────────────────────────────────
    saved = []
    for week_key in ("current", "previous"):
        week = fred_data.get(week_key)
        if not week:
            continue

        snap_date = week["date"]
        result = await db.execute(
            select(RateSnapshot).where(RateSnapshot.snapshot_date == snap_date)
        )
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            snapshot = RateSnapshot(snapshot_date=snap_date)
            db.add(snapshot)

        for field in rate_fields:
            val = week.get(field)
            if val is not None:
                setattr(snapshot, field, val)

        snapshot.source = "fred"
        snapshot.is_admin_override = False
        snapshot.created_by = current_user.id
        saved.append({"date": snap_date, "status": "saved"})

    await db.commit()

    current_week = fred_data.get("current") or {}
    return {
        "success": True,
        "message": f"FRED data synced — {len(saved)} snapshot(s) saved. Manual overrides cleared.",
        "saved": saved,
        "reset": todays_manual is not None,   # tells UI whether a manual entry was wiped
        "current_date": current_week.get("date"),
        "current_rates": {k: current_week[k] for k in rate_fields if current_week.get(k)},
    }


@router.get("/history")
async def rate_history(
    limit: int = Query(30, le=90),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RateSnapshot)
        .order_by(desc(RateSnapshot.snapshot_date))
        .limit(limit)
    )
    snapshots = result.scalars().all()
    return [_snapshot_to_dict(s) for s in snapshots]


# ── Rate Alerts ───────────────────────────────────────────────────────────────

VALID_RATE_FIELDS = {
    "rate_conventional_30", "rate_conventional_15", "rate_fha_30",
    "rate_va_30", "rate_usda_30", "rate_dscr", "rate_heloc_prime_plus", "rate_jumbo_30",
}


class RateAlertCreate(BaseModel):
    name: str
    rate_field: str
    threshold: float
    direction: str          # "below" | "above"
    action: str = "log"     # "log" | "queue_outreach"
    message: Optional[str] = None
    is_active: bool = True


class RateAlertUpdate(BaseModel):
    name: Optional[str] = None
    threshold: Optional[float] = None
    direction: Optional[str] = None
    action: Optional[str] = None
    message: Optional[str] = None
    is_active: Optional[bool] = None


def _serialize_alert(a: RateAlert) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "rate_field": a.rate_field,
        "threshold": a.threshold,
        "direction": a.direction,
        "action": a.action,
        "message": a.message,
        "is_active": a.is_active,
        "last_triggered_at": a.last_triggered_at.isoformat() if a.last_triggered_at else None,
        "last_triggered_rate": a.last_triggered_rate,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


async def _fire_alert(db: AsyncSession, alert: RateAlert, current_rate: float):
    """Mark the alert as triggered and perform the configured action."""
    alert.last_triggered_at = datetime.utcnow()
    alert.last_triggered_rate = current_rate

    if alert.action == "queue_outreach":
        # Create a flagged agent task for follow-up
        from app.models.agent import Task
        task = Task(
            title=f"Rate alert fired: {alert.name}",
            description=(
                f"{alert.rate_field} is now {current_rate:.2f}% "
                f"({alert.direction} threshold {alert.threshold:.2f}%). "
                f"{alert.message or 'Review warm leads and queue outreach.'}"
            ),
            task_type="outreach",
            priority="high",
        )
        db.add(task)

    await log_event(
        db, "rate.alert_triggered",
        actor_type="system", resource_type="rate_alert", resource_id=alert.id,
        details={"rate_field": alert.rate_field, "current_rate": current_rate, "threshold": alert.threshold},
    )


async def _check_alerts(db: AsyncSession, new_rates: dict):
    """Called after any rate update — check all active alerts."""
    result = await db.execute(select(RateAlert).where(RateAlert.is_active == True))
    alerts = result.scalars().all()
    for alert in alerts:
        current = new_rates.get(alert.rate_field)
        if current is None:
            continue
        triggered = (
            (alert.direction == "below" and current < alert.threshold) or
            (alert.direction == "above" and current > alert.threshold)
        )
        if triggered:
            await _fire_alert(db, alert, current)


@router.get("/alerts")
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(RateAlert).order_by(RateAlert.created_at.desc()))
    return [_serialize_alert(a) for a in result.scalars().all()]


@router.post("/alerts", status_code=201)
async def create_alert(
    data: RateAlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.rate_field not in VALID_RATE_FIELDS:
        raise HTTPException(400, f"Invalid rate_field. Must be one of: {', '.join(sorted(VALID_RATE_FIELDS))}")
    if data.direction not in ("below", "above"):
        raise HTTPException(400, "direction must be 'below' or 'above'")

    alert = RateAlert(**data.model_dump(), created_by=current_user.id)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return _serialize_alert(alert)


@router.patch("/alerts/{alert_id}")
async def update_alert(
    alert_id: str,
    data: RateAlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(RateAlert).where(RateAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(alert, field, val)
    await db.commit()
    return _serialize_alert(alert)


@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(RateAlert).where(RateAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    await db.delete(alert)
    await db.commit()
