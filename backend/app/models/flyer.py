"""
Flyer / Avatar Generation — DB models.

GeneratedFlyer  — one row per generated marketing asset (avatar + composited flyer).
ReferencePhoto  — stores the banker's reference face photo path (one per system).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from app.database import Base


class ReferencePhoto(Base):
    """The banker's reference face photo used for AI avatar generation."""
    __tablename__ = "reference_photos"

    id          = Column(Integer, primary_key=True)
    file_path   = Column(String)           # local path: media/avatar/reference.jpg
    file_url    = Column(String)           # public URL served by /media/...
    uploaded_by = Column(String)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GeneratedFlyer(Base):
    """One generated marketing asset — avatar image + composited branded flyer."""
    __tablename__ = "generated_flyers"

    id               = Column(Integer, primary_key=True)

    # What was requested
    use_case         = Column(String)      # purchase | dpa | refi | realtor | generic
    flyer_format     = Column(String)      # social_square | facebook_banner | story | wide_banner
    avatar_style     = Column(Text)        # full style prompt sent to AI
    headline         = Column(String)
    subheadline      = Column(String, nullable=True)
    cta_text         = Column(String, nullable=True)

    # Generation pipeline
    provider         = Column(String)      # fal | replicate | passthrough (no AI, direct photo)
    avatar_image_path = Column(String, nullable=True)   # AI-generated avatar (local path)
    avatar_image_url  = Column(String, nullable=True)   # public URL
    flyer_image_path  = Column(String, nullable=True)   # final composited flyer (local path)
    flyer_image_url   = Column(String, nullable=True)   # public URL

    # State
    status           = Column(String, default="pending")  # pending | avatar_ready | complete | failed
    error            = Column(Text, nullable=True)

    # Meta
    created_by       = Column(String, default="admin")
    created_at       = Column(DateTime, default=datetime.utcnow)
