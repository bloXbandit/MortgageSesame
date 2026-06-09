"""
Public hub models: rate snapshots, property listings, DPA programs, product education pages.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Float, Integer, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.database import Base
import enum


# ── Rate Snapshots ──────────────────────────────────────────────────────────

class RateSnapshot(Base):
    """Daily mortgage rate entry. Admin sets override; FRED auto-fills as fallback."""
    __tablename__ = "rate_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_date: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # YYYY-MM-DD
    # Rates stored as strings to allow "mid-6s" style display if desired
    rate_fha_30: Mapped[Optional[float]] = mapped_column(Float)
    rate_conventional_30: Mapped[Optional[float]] = mapped_column(Float)
    rate_conventional_15: Mapped[Optional[float]] = mapped_column(Float)
    rate_va_30: Mapped[Optional[float]] = mapped_column(Float)
    rate_usda_30: Mapped[Optional[float]] = mapped_column(Float)
    rate_dscr: Mapped[Optional[float]] = mapped_column(Float)
    rate_heloc_prime_plus: Mapped[Optional[float]] = mapped_column(Float)
    rate_jumbo_30: Mapped[Optional[float]] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(50), default="manual")  # manual | fred
    notes: Mapped[Optional[str]] = mapped_column(String(500))
    is_admin_override: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Property Listings ───────────────────────────────────────────────────────

class ListingStatus(str, enum.Enum):
    ACTIVE = "active"
    UNDER_CONTRACT = "under_contract"
    SOLD = "sold"
    COMING_SOON = "coming_soon"


class Listing(Base):
    """Property listing used to generate mock closing cost scenarios on the public hub."""
    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(50), default="MD")
    county: Mapped[Optional[str]] = mapped_column(String(100))
    zip_code: Mapped[Optional[str]] = mapped_column(String(20))
    list_price: Mapped[float] = mapped_column(Float, nullable=False)
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer)
    bathrooms: Mapped[Optional[float]] = mapped_column(Float)
    sqft: Mapped[Optional[int]] = mapped_column(Integer)
    property_type: Mapped[Optional[str]] = mapped_column(String(100))  # single family, condo, townhouse
    photo_url: Mapped[Optional[str]] = mapped_column(String(1000))
    zillow_url: Mapped[Optional[str]] = mapped_column(String(1000))
    zillow_id: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[ListingStatus] = mapped_column(SAEnum(ListingStatus), default=ListingStatus.ACTIVE)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=True)
    hoa_monthly: Mapped[Optional[float]] = mapped_column(Float)
    annual_taxes: Mapped[Optional[float]] = mapped_column(Float)
    annual_insurance: Mapped[Optional[float]] = mapped_column(Float)
    # Listing agent (optional — link to a Contacts realtor record or freeform entry)
    listing_agent_contact_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("contacts.id"), nullable=True)
    listing_agent_name: Mapped[Optional[str]] = mapped_column(String(255))
    listing_agent_phone: Mapped[Optional[str]] = mapped_column(String(30))
    listing_agent_email: Mapped[Optional[str]] = mapped_column(String(255))
    # Calculator overrides (optional — auto-calculated if not set)
    override_down_pct_conventional: Mapped[Optional[float]] = mapped_column(Float)
    override_down_pct_fha: Mapped[Optional[float]] = mapped_column(Float)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    created_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── DPA Programs ────────────────────────────────────────────────────────────

class DpaType(str, enum.Enum):
    GRANT = "grant"
    FORGIVABLE = "forgivable"
    DEFERRED = "deferred"
    REPAYABLE = "repayable"
    SECOND_LIEN = "second_lien"


class DpaProgram(Base):
    """Down payment assistance programs — MD/DC seeded, designed to scale to any state."""
    __tablename__ = "dpa_programs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    administering_agency: Mapped[Optional[str]] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(10), index=True)
    county: Mapped[Optional[str]] = mapped_column(String(100), index=True)  # null = statewide
    city: Mapped[Optional[str]] = mapped_column(String(100))
    dpa_type: Mapped[DpaType] = mapped_column(SAEnum(DpaType))
    assistance_amount: Mapped[Optional[str]] = mapped_column(String(255))  # "up to $25,000" or "5% of purchase price"
    assistance_amount_max: Mapped[Optional[float]] = mapped_column(Float)  # numeric for sorting
    target_buyer: Mapped[Optional[str]] = mapped_column(String(255))  # "First-time buyers", "Repeat OK"
    income_limit_notes: Mapped[Optional[str]] = mapped_column(Text)
    credit_score_min: Mapped[Optional[int]] = mapped_column(Integer)
    property_location_notes: Mapped[Optional[str]] = mapped_column(Text)
    property_type_notes: Mapped[Optional[str]] = mapped_column(String(500))
    eligible_loan_types: Mapped[Optional[str]] = mapped_column(String(255))  # FHA, Conventional, VA, USDA
    repayment_notes: Mapped[Optional[str]] = mapped_column(Text)
    education_required: Mapped[bool] = mapped_column(Boolean, default=False)
    other_requirements: Mapped[Optional[str]] = mapped_column(Text)
    program_url: Mapped[Optional[str]] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    last_verified: Mapped[Optional[str]] = mapped_column(String(20))  # YYYY-MM-DD
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Rate Alerts ─────────────────────────────────────────────────────────────

class RateAlert(Base):
    """
    Threshold-based alert: fires when a rate field crosses above/below a target value.
    action = "log"            — write to audit log only
    action = "queue_outreach" — flag warm/hot leads in the call queue
    """
    __tablename__ = "rate_alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rate_field: Mapped[str] = mapped_column(String(50))        # e.g. "rate_conventional_30"
    threshold: Mapped[float] = mapped_column(Float)
    direction: Mapped[str] = mapped_column(String(10))         # "below" | "above"
    action: Mapped[str] = mapped_column(String(50), default="log")  # "log" | "queue_outreach"
    message: Mapped[Optional[str]] = mapped_column(Text)       # context note for outreach
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_triggered_rate: Mapped[Optional[float]] = mapped_column(Float)
    created_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
