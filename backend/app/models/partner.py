"""
Referral partner records — realtors, title agents, builders.

Reusable co-marketing identities: when a flyer/campaign says "with Donna",
the agent resolves the Partner record and drops her name, brokerage, headshot,
and logo into the layout — no re-typing, consistent branding, and partner-level
attribution on scans/replies via outreach linkage.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from typing import Optional


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_type: Mapped[str] = mapped_column(String(50), default="realtor")  # realtor | title_agent | builder | other
    brokerage: Mapped[Optional[str]] = mapped_column(String(255))
    license_number: Mapped[Optional[str]] = mapped_column(String(100))

    # Contact
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    website: Mapped[Optional[str]] = mapped_column(String(500))

    # Co-marketing assets
    headshot_url: Mapped[Optional[str]] = mapped_column(String(1000))   # /media/... or external
    logo_asset_id: Mapped[Optional[str]] = mapped_column(String)        # FK to brand_assets.id
    brand_color: Mapped[Optional[str]] = mapped_column(String(20))      # hex accent for co-branded pieces

    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
