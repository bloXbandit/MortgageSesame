import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class ContactType(str, enum.Enum):
    CONSUMER = "consumer"
    REALTOR = "realtor"
    TITLE_AGENT = "title_agent"
    INVESTOR = "investor"
    BUSINESS_OWNER = "business_owner"
    HOMEOWNER = "homeowner"
    PAST_CLIENT = "past_client"
    REFERRAL_PARTNER = "referral_partner"


class LeadScore(str, enum.Enum):
    HOT = "hot"
    WARM = "warm"
    LONG_TERM = "long_term"
    BAD_FIT = "bad_fit"
    COMPLIANCE_RISK = "compliance_risk"
    UNSCORED = "unscored"


class ConsentStatus(str, enum.Enum):
    PENDING = "pending"
    OPTED_IN = "opted_in"
    OPTED_OUT = "opted_out"
    DNC = "dnc"
    UNKNOWN = "unknown"


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    company: Mapped[str | None] = mapped_column(String(255))
    role_title: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(50))
    county: Mapped[str | None] = mapped_column(String(100))
    zip_code: Mapped[str | None] = mapped_column(String(20))
    contact_type: Mapped[ContactType] = mapped_column(SAEnum(ContactType), default=ContactType.CONSUMER)
    source: Mapped[str | None] = mapped_column(String(255))
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    consent_status: Mapped[ConsentStatus] = mapped_column(SAEnum(ConsentStatus), default=ConsentStatus.UNKNOWN)
    consent_email: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_sms: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_call: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dnc: Mapped[bool] = mapped_column(Boolean, default=False)
    is_opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    lead_score: Mapped[LeadScore] = mapped_column(SAEnum(LeadScore), default=LeadScore.UNSCORED)
    lead_score_notes: Mapped[str | None] = mapped_column(Text)
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))

    sources: Mapped[list["ContactSource"]] = relationship("ContactSource", back_populates="contact", cascade="all, delete-orphan")
    consent_records: Mapped[list["ConsentRecord"]] = relationship("ConsentRecord", back_populates="contact", cascade="all, delete-orphan")


class ContactSource(Base):
    __tablename__ = "contact_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id: Mapped[str] = mapped_column(String, ForeignKey("contacts.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100))
    source_detail: Mapped[str | None] = mapped_column(String(500))
    uploaded_filename: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    contact: Mapped["Contact"] = relationship("Contact", back_populates="sources")


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id: Mapped[str] = mapped_column(String, ForeignKey("contacts.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(500))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    contact: Mapped["Contact"] = relationship("Contact", back_populates="consent_records")


class OptOut(Base):
    __tablename__ = "opt_outs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contact_id: Mapped[str | None] = mapped_column(String, ForeignKey("contacts.id"))
    channel: Mapped[str] = mapped_column(String(50))
    identifier: Mapped[str] = mapped_column(String(255), index=True)
    reason: Mapped[str | None] = mapped_column(String(500))
    opted_out_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
