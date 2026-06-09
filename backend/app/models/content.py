import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum
from typing import Optional


class ContentPlatform(str, enum.Enum):
    TIKTOK = "tiktok"
    INSTAGRAM_REEL = "instagram_reel"
    INSTAGRAM_CAROUSEL = "instagram_carousel"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    GOOGLE_BUSINESS = "google_business"
    EMAIL_SNIPPET = "email_snippet"


class ContentCategory(str, enum.Enum):
    DPA_MYTHS = "dpa_myths"
    FHA_EDUCATION = "fha_education"
    HELOC_STRATEGY = "heloc_strategy"
    DSCR_INVESTOR = "dscr_investor"
    REFI_TRIGGERS = "refi_triggers"
    UNDERWRITING_MISTAKES = "underwriting_mistakes"
    CREDIT_READINESS = "credit_readiness"
    REALTOR_EDUCATION = "realtor_education"
    OPEN_HOUSE = "open_house"
    MARKET_UPDATE = "market_update"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_EDIT = "needs_edit"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


class SocialPost(Base):
    __tablename__ = "social_posts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    platform: Mapped[ContentPlatform] = mapped_column(SAEnum(ContentPlatform), nullable=False)
    category: Mapped[Optional[ContentCategory]] = mapped_column(SAEnum(ContentCategory))
    hook: Mapped[Optional[str]] = mapped_column(Text)
    script: Mapped[Optional[str]] = mapped_column(Text)
    caption: Mapped[Optional[str]] = mapped_column(Text)
    cta: Mapped[Optional[str]] = mapped_column(String(500))
    visual_concept: Mapped[Optional[str]] = mapped_column(Text)
    image_prompt: Mapped[Optional[str]] = mapped_column(Text)
    video_prompt: Mapped[Optional[str]] = mapped_column(Text)
    voiceover_script: Mapped[Optional[str]] = mapped_column(Text)
    broll_instructions: Mapped[Optional[str]] = mapped_column(Text)
    compliance_notes: Mapped[Optional[str]] = mapped_column(Text)
    is_fictional_example: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_status: Mapped[ApprovalStatus] = mapped_column(SAEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    approved_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    scheduled_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    external_post_id: Mapped[Optional[str]] = mapped_column(String(255))
    media_asset_ids: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    # Pipeline stage tracking
    # script_only → voice_ready → video_processing → video_ready → assembled → published
    pipeline_stage: Mapped[Optional[str]] = mapped_column(String(50), default="script_only")
    generated_by: Mapped[str] = mapped_column(String(50), default="ai")
    created_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50))
    file_path: Mapped[Optional[str]] = mapped_column(String(1000))
    file_url: Mapped[Optional[str]] = mapped_column(String(1000))
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    file_size: Mapped[Optional[int]] = mapped_column()
    is_brand_asset: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
