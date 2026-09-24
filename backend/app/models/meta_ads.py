"""
Meta Ads publish state — tracks campaigns pushed to Meta Marketing API.

One row per publish attempt against a CampaignPage. Stores the targeting
snapshot used plus the Meta object IDs so status can be synced later.
New table — no changes to existing tables.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from typing import Optional


class MetaAdPublish(Base):
    __tablename__ = "meta_ad_publishes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Source campaign
    campaign_page_slug: Mapped[str] = mapped_column(String(255), index=True)
    run_id: Mapped[Optional[str]] = mapped_column(String(255))
    template_id: Mapped[Optional[str]] = mapped_column(String(100))
    ad_angle_index: Mapped[int] = mapped_column(default=0)

    # Snapshot of what was sent to Meta
    facebook_setup: Mapped[Optional[dict]] = mapped_column(JSON)   # targeting/budget block used
    ad_unit: Mapped[Optional[dict]] = mapped_column(JSON)          # the ad copy unit used

    # Meta object IDs returned by the Marketing API
    meta_campaign_id: Mapped[Optional[str]] = mapped_column(String(100))
    meta_adset_id: Mapped[Optional[str]] = mapped_column(String(100))
    meta_creative_id: Mapped[Optional[str]] = mapped_column(String(100))
    meta_ad_id: Mapped[Optional[str]] = mapped_column(String(100))

    # State
    status: Mapped[str] = mapped_column(String(50), default="paused")  # paused | active | failed | dry_run
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
