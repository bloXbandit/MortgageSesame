import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Enum as SAEnum, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class CampaignType(str, enum.Enum):
    REALTOR_PARTNERSHIP = "realtor_partnership"
    TITLE_REFI = "title_refi"
    DPA_BUYER = "dpa_buyer"
    DSCR_INVESTOR = "dscr_investor"
    HELOC_HOMEOWNER = "heloc_homeowner"
    OPEN_HOUSE_QR = "open_house_qr"
    SOCIAL_CONTENT = "social_content"
    PAST_LEAD_NURTURE = "past_lead_nurture"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignGoal(str, enum.Enum):
    BOOK_CALL = "book_call"
    DRIVE_AI_INTAKE = "drive_ai_intake"
    PROMOTE_DPA = "promote_dpa"
    PROMOTE_DSCR = "promote_dscr"
    PROMOTE_HELOC = "promote_heloc"
    PROMOTE_REFI = "promote_refi"
    RECRUIT_REALTOR = "recruit_realtor"
    OPEN_HOUSE_TOOL = "open_house_tool"


class Channel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    GOOGLE_BUSINESS = "google_business"
    MANUAL = "manual"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_type: Mapped[CampaignType] = mapped_column(SAEnum(CampaignType), nullable=False)
    goal: Mapped[CampaignGoal] = mapped_column(SAEnum(CampaignGoal), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(SAEnum(CampaignStatus), default=CampaignStatus.DRAFT)
    target_segment: Mapped[str | None] = mapped_column(String(100))
    product_id: Mapped[str | None] = mapped_column(String, ForeignKey("products.id"))
    voice_tone: Mapped[str | None] = mapped_column(String(100))
    channel: Mapped[Channel] = mapped_column(SAEnum(Channel), default=Channel.EMAIL)
    sequence_length: Mapped[int] = mapped_column(Integer, default=3)
    follow_up_days: Mapped[int] = mapped_column(Integer, default=3)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    compliance_notes: Mapped[str | None] = mapped_column(Text)
    contact_ids: Mapped[list | None] = mapped_column(JSON, default=list)
    created_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    steps: Mapped[list["CampaignStep"]] = relationship("CampaignStep", back_populates="campaign", order_by="CampaignStep.step_order", cascade="all, delete-orphan")


class CampaignStep(Base):
    __tablename__ = "campaign_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = mapped_column(String, ForeignKey("campaigns.id"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    channel: Mapped[Channel] = mapped_column(SAEnum(Channel))
    template_id: Mapped[str | None] = mapped_column(String, ForeignKey("message_templates.id"))
    delay_days: Mapped[int] = mapped_column(Integer, default=0)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="steps")


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[Channel] = mapped_column(SAEnum(Channel))
    subject: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)
    cta: Mapped[str | None] = mapped_column(String(500))
    opt_out_language: Mapped[str | None] = mapped_column(Text)
    compliance_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str | None] = mapped_column(String, ForeignKey("campaigns.id"))
    contact_id: Mapped[str | None] = mapped_column(String, ForeignKey("contacts.id"))
    template_id: Mapped[str | None] = mapped_column(String, ForeignKey("message_templates.id"))
    channel: Mapped[Channel] = mapped_column(SAEnum(Channel))
    subject: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(255))
    sender_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
