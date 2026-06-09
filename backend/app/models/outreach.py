"""
Campaign outreach engine models.

Extends the base Campaign model with:
  - ProspectList / Prospect    — imported property/contact lists
  - RefiScore                  — per-prospect scoring result
  - CampaignOutreach           — individual generated outbound piece (mail/email/sms/call)
  - QRLink / QREvent           — per-piece tracking links and scan events
  - CallTask                   — warm-lead call tasks triggered by responses
  - SuppressionEntry           — email/phone opt-out suppression list
  - ProviderConfig             — which provider to use per channel (env-override supported)
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Float, Integer, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum
from typing import Optional


# ── Enums ─────────────────────────────────────────────────────────────────────

class ProspectSource(str, enum.Enum):
    CSV_UPLOAD    = "csv_upload"
    MANUAL        = "manual"
    CONTACT_LIST  = "contact_list"
    ATTOM         = "attom"
    PROPSTREAM    = "propstream"
    BATCHDATA     = "batchdata"
    LISTSERVICE   = "listservice"

class ProspectType(str, enum.Enum):
    HOMEOWNER         = "homeowner"
    INVESTOR          = "investor"
    REALTOR           = "realtor"
    TITLE_AGENT       = "title_agent"
    PAST_CLIENT       = "past_client"
    RENTER            = "renter"
    UNKNOWN           = "unknown"

class ScoreGrade(str, enum.Enum):
    A_TARGET  = "A_TARGET"   # 80+
    B_TARGET  = "B_TARGET"   # 60–79
    NURTURE   = "NURTURE"    # 40–59
    SKIP      = "SKIP"       # <40
    BLOCKED   = "BLOCKED"    # DNC / compliance block

class OutreachChannel(str, enum.Enum):
    EMAIL        = "email"
    SMS          = "sms"
    DIRECT_MAIL  = "direct_mail"
    CALL_TASK    = "call_task"

class OutreachStatus(str, enum.Enum):
    DRAFT               = "draft"
    PENDING_COMPLIANCE  = "pending_compliance"
    COMPLIANCE_PASSED   = "compliance_passed"
    COMPLIANCE_BLOCKED  = "compliance_blocked"
    PENDING_APPROVAL    = "pending_approval"
    APPROVED            = "approved"
    REJECTED            = "rejected"
    QUEUED              = "queued"
    SENT                = "sent"
    DELIVERED           = "delivered"
    OPENED              = "opened"
    CLICKED             = "clicked"
    REPLIED             = "replied"
    BOUNCED             = "bounced"
    OPTED_OUT           = "opted_out"
    FAILED              = "failed"
    # Direct mail specific
    IN_PRODUCTION       = "in_production"
    MAILED              = "mailed"
    QR_SCANNED          = "qr_scanned"
    CONVERTED           = "converted"

class CallTaskStatus(str, enum.Enum):
    PENDING            = "pending"
    COMPLETED          = "completed"
    NO_ANSWER          = "no_answer"
    VOICEMAIL_LEFT     = "voicemail_left"
    CALLBACK_SCHEDULED = "callback_scheduled"
    NOT_INTERESTED     = "not_interested"
    CONVERTED          = "converted"
    ARCHIVED           = "archived"

class MailTemplate(str, enum.Enum):
    EQUITY_VOUCHER          = "equity_voucher"
    REFI_CERTIFICATE        = "refi_certificate"
    PAYMENT_REVIEW_NOTICE   = "payment_review_notice"
    HELOC_INVITE            = "heloc_invite"
    FHA_STREAMLINE_NOTICE   = "fha_streamline_notice"
    DSCR_INVESTOR_NOTICE    = "dscr_investor_notice"
    REALTOR_INVITE          = "realtor_invite"


# ── ProspectList ──────────────────────────────────────────────────────────────

class ProspectList(Base):
    """
    A named batch of imported prospects — uploaded CSV, pulled from a property data source,
    or built from existing contacts.
    """
    __tablename__ = "prospect_lists"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[ProspectSource] = mapped_column(SAEnum(ProspectSource), default=ProspectSource.CSV_UPLOAD)
    source_file_name: Mapped[Optional[str]] = mapped_column(String(500))
    prospect_type: Mapped[ProspectType] = mapped_column(SAEnum(ProspectType), default=ProspectType.HOMEOWNER)
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    scored_count: Mapped[int] = mapped_column(Integer, default=0)
    a_target_count: Mapped[int] = mapped_column(Integer, default=0)
    b_target_count: Mapped[int] = mapped_column(Integer, default=0)
    suppressed_count: Mapped[int] = mapped_column(Integer, default=0)
    # Geographic focus
    state: Mapped[Optional[str]] = mapped_column(String(10))
    county: Mapped[Optional[str]] = mapped_column(String(100))
    zip_codes: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    created_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prospects: Mapped[list["Prospect"]] = relationship("Prospect", back_populates="prospect_list", cascade="all, delete-orphan")


# ── Prospect ──────────────────────────────────────────────────────────────────

class Prospect(Base):
    """
    A single prospect record — may have property/mortgage data beyond what Contact holds.
    Can be linked to an existing Contact or be a standalone record until converted.
    """
    __tablename__ = "prospects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prospect_list_id: Mapped[str] = mapped_column(String, ForeignKey("prospect_lists.id"), nullable=False)
    contact_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("contacts.id"))  # linked if matched

    # Identity
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    mailing_address: Mapped[Optional[str]] = mapped_column(String(500))
    mailing_city: Mapped[Optional[str]] = mapped_column(String(100))
    mailing_state: Mapped[Optional[str]] = mapped_column(String(10))
    mailing_zip: Mapped[Optional[str]] = mapped_column(String(20))
    prospect_type: Mapped[ProspectType] = mapped_column(SAEnum(ProspectType), default=ProspectType.HOMEOWNER)

    # Property data
    property_address: Mapped[Optional[str]] = mapped_column(String(500))
    property_city: Mapped[Optional[str]] = mapped_column(String(100))
    property_state: Mapped[Optional[str]] = mapped_column(String(10))
    property_zip: Mapped[Optional[str]] = mapped_column(String(20))
    property_county: Mapped[Optional[str]] = mapped_column(String(100))
    property_type: Mapped[Optional[str]] = mapped_column(String(100))    # SFR, condo, multi, etc.
    is_owner_occupied: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_investment_property: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Mortgage / financial data (from public records or data provider)
    purchase_price: Mapped[Optional[float]] = mapped_column(Float)
    purchase_date: Mapped[Optional[str]] = mapped_column(String(20))      # YYYY-MM-DD
    estimated_current_value: Mapped[Optional[float]] = mapped_column(Float)
    estimated_equity_pct: Mapped[Optional[float]] = mapped_column(Float)  # e.g. 35.5 = 35.5%
    estimated_equity_dollars: Mapped[Optional[float]] = mapped_column(Float)
    current_loan_amount: Mapped[Optional[float]] = mapped_column(Float)
    current_rate_estimate: Mapped[Optional[float]] = mapped_column(Float) # e.g. 7.25
    loan_type: Mapped[Optional[str]] = mapped_column(String(50))          # FHA, conventional, VA, etc.
    origination_date: Mapped[Optional[str]] = mapped_column(String(20))   # YYYY-MM-DD
    last_refi_date: Mapped[Optional[str]] = mapped_column(String(20))
    lender_name: Mapped[Optional[str]] = mapped_column(String(255))
    # For realtor/title targets
    company_name: Mapped[Optional[str]] = mapped_column(String(255))
    license_number: Mapped[Optional[str]] = mapped_column(String(100))
    recent_transactions: Mapped[Optional[int]] = mapped_column(Integer)   # closings in last 12mo

    # Compliance / suppression
    is_do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    is_suppressed: Mapped[bool] = mapped_column(Boolean, default=False)
    suppression_reason: Mapped[Optional[str]] = mapped_column(String(255))

    # Raw import row
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    prospect_list: Mapped["ProspectList"] = relationship("ProspectList", back_populates="prospects")
    scores: Mapped[list["RefiScore"]] = relationship("RefiScore", back_populates="prospect", cascade="all, delete-orphan")
    outreach_items: Mapped[list["CampaignOutreach"]] = relationship("CampaignOutreach", back_populates="prospect")


# ── RefiScore ─────────────────────────────────────────────────────────────────

class RefiScore(Base):
    """Scoring result for a prospect relative to a campaign type."""
    __tablename__ = "refi_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prospect_id: Mapped[str] = mapped_column(String, ForeignKey("prospects.id"), nullable=False)
    campaign_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("campaigns.id"))

    score: Mapped[int] = mapped_column(Integer, default=0)
    grade: Mapped[ScoreGrade] = mapped_column(SAEnum(ScoreGrade), default=ScoreGrade.SKIP)
    reason_codes: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    recommended_channel: Mapped[Optional[str]] = mapped_column(String(50))   # email / direct_mail / sms
    recommended_template: Mapped[Optional[str]] = mapped_column(String(100))
    score_details: Mapped[Optional[dict]] = mapped_column(JSON)  # breakdown of each scoring component

    scored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="scores")


# ── CampaignOutreach ──────────────────────────────────────────────────────────

class CampaignOutreach(Base):
    """
    A single generated outbound piece — the unit of work.
    One per prospect per channel per campaign step.
    """
    __tablename__ = "campaign_outreach"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("campaigns.id"))
    prospect_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("prospects.id"))
    contact_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("contacts.id"))
    channel: Mapped[OutreachChannel] = mapped_column(SAEnum(OutreachChannel))

    # Template reference
    template_key: Mapped[Optional[str]] = mapped_column(String(100))  # e.g. "equity_voucher"
    template_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Generated content
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    body_text: Mapped[Optional[str]] = mapped_column(Text)
    body_html: Mapped[Optional[str]] = mapped_column(Text)
    rendered_pdf_url: Mapped[Optional[str]] = mapped_column(String(1000))
    call_script: Mapped[Optional[str]] = mapped_column(Text)
    merge_data: Mapped[Optional[dict]] = mapped_column(JSON)   # values used in merge render

    # Tracking
    qr_code: Mapped[Optional[str]] = mapped_column(String(100))  # FK to QRLink.code
    tracking_url: Mapped[Optional[str]] = mapped_column(String(1000))

    # Workflow status
    status: Mapped[OutreachStatus] = mapped_column(SAEnum(OutreachStatus), default=OutreachStatus.DRAFT)
    compliance_status: Mapped[Optional[str]] = mapped_column(String(50))   # pass / warning / blocked
    compliance_flags: Mapped[Optional[list]] = mapped_column(JSON)
    approval_status: Mapped[Optional[str]] = mapped_column(String(50))     # pending / approved / rejected
    approved_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Provider tracking
    provider: Mapped[Optional[str]] = mapped_column(String(100))           # mock / lob / sendgrid / etc.
    provider_job_id: Mapped[Optional[str]] = mapped_column(String(255))
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Delivery timeline
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    bounced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    unsubscribed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    qr_scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    failed_reason: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prospect: Mapped["Optional[Prospect]"] = relationship("Prospect", back_populates="outreach_items")
    qr_events: Mapped[list["QREvent"]] = relationship("QREvent", back_populates="outreach_item", cascade="all, delete-orphan")


# ── QRLink / QREvent ──────────────────────────────────────────────────────────

class QRLink(Base):
    """
    Unique tracking link generated per outreach piece.
    Redirects to a landing page/intake and records the scan.
    """
    __tablename__ = "qr_links"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    outreach_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("campaign_outreach.id"))
    campaign_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("campaigns.id"))
    prospect_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("prospects.id"))
    destination_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255))   # human-readable e.g. "Equity Review"
    scan_count: Mapped[int] = mapped_column(Integer, default=0)
    click_count: Mapped[int] = mapped_column(Integer, default=0)
    last_scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    events: Mapped[list["QREvent"]] = relationship("QREvent", back_populates="qr_link", cascade="all, delete-orphan")


class QREvent(Base):
    """A single scan/click event on a QR or tracking link."""
    __tablename__ = "qr_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    qr_link_id: Mapped[str] = mapped_column(String, ForeignKey("qr_links.id"), nullable=False)
    outreach_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("campaign_outreach.id"))
    event_type: Mapped[str] = mapped_column(String(50))    # scan / click / form_fill / call
    ip_address: Mapped[Optional[str]] = mapped_column(String(60))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    referrer: Mapped[Optional[str]] = mapped_column(String(500))
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    qr_link: Mapped["QRLink"] = relationship("QRLink", back_populates="events")
    outreach_item: Mapped["Optional[CampaignOutreach]"] = relationship("CampaignOutreach", back_populates="qr_events")


# ── CallTask ──────────────────────────────────────────────────────────────────

class CallTask(Base):
    """
    A warm-lead call task — created when a QR is scanned, form filled, email replied, etc.
    NOT an auto-dialer. This is a task queue for the banker to work.
    """
    __tablename__ = "call_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("campaigns.id"))
    outreach_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("campaign_outreach.id"))
    prospect_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("prospects.id"))
    contact_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("contacts.id"))

    # Who to call
    prospect_name: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    property_address: Mapped[Optional[str]] = mapped_column(String(500))

    # Why they're hot
    trigger: Mapped[Optional[str]] = mapped_column(String(100))  # qr_scan / form_fill / email_reply / high_score
    trigger_detail: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=5)   # 1=highest, 10=lowest
    score: Mapped[Optional[int]] = mapped_column(Integer)

    # Generated call prep
    call_script: Mapped[Optional[str]] = mapped_column(Text)
    talking_points: Mapped[Optional[list]] = mapped_column(JSON)
    campaign_context: Mapped[Optional[str]] = mapped_column(Text)  # what piece they responded to

    status: Mapped[CallTaskStatus] = mapped_column(SAEnum(CallTaskStatus), default=CallTaskStatus.PENDING)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    outcome_detail: Mapped[Optional[str]] = mapped_column(Text)
    callback_scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    assigned_to: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── SuppressionEntry ──────────────────────────────────────────────────────────

class SuppressionEntry(Base):
    """Global opt-out / suppression list. Checked before every outbound send."""
    __tablename__ = "suppression_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    value: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    value_type: Mapped[str] = mapped_column(String(20))   # email / phone / address
    reason: Mapped[str] = mapped_column(String(100))      # opt_out / bounce / complaint / manual / dnc
    source: Mapped[Optional[str]] = mapped_column(String(100))  # provider webhook / user entry / import
    notes: Mapped[Optional[str]] = mapped_column(Text)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── ProviderConfig ────────────────────────────────────────────────────────────

class ProviderConfig(Base):
    """
    Configured provider per channel. One active config per channel at a time.
    Env vars override DB values — DB is the UI-editable layer.
    """
    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    channel: Mapped[str] = mapped_column(String(50), unique=True)  # direct_mail / email / sms / voice / address_verify
    provider_name: Mapped[str] = mapped_column(String(100))        # mock / lob / sendgrid / resend / signalwire / etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[Optional[dict]] = mapped_column(JSON)         # non-secret config (webhook URL, from address, etc.)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    test_status: Mapped[Optional[str]] = mapped_column(String(50))   # ok / failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
