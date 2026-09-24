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
    layout           = Column(String, default="promo")   # promo | listing | open_house | program | comparison | lifestyle | rate_update | testimonial | just_funded | steps
    layout_data      = Column(JSON, nullable=True)       # structured content for data-rich layouts (enables revisions)
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


class BrandAsset(Base):
    """
    Brand asset library — logos, partner marks, screenshots, any image the
    operator uploads with a simple name so the agent can find and use it.
    e.g. name="uwm logo" → agent composites it onto flyers on request.
    """
    __tablename__ = "brand_assets"

    id         = Column(Integer, primary_key=True)
    name       = Column(String)                    # simple label: "uwm logo", "team photo"
    kind       = Column(String, default="logo")    # logo | image | screenshot
    image_path = Column(String)
    image_url  = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class SavedAvatar(Base):
    """
    Avatar library — best renders saved for reuse.

    A saved avatar can come from any source (openai render, heygen avatar image,
    direct upload, or the raw reference photo). The agent picks from this library
    when building flyers instead of regenerating, so a look the operator likes
    is reproducible forever.
    """
    __tablename__ = "saved_avatars"

    id           = Column(Integer, primary_key=True)
    name         = Column(String)                       # operator-friendly label, e.g. "Navy suit — the good one"
    source       = Column(String, default="openai")     # openai | fal | replicate | heygen | upload | reference
    style_preset = Column(String, nullable=True)        # preset used at generation time, if any
    image_path   = Column(String)                       # local path
    image_url    = Column(String)                       # public URL
    is_favorite  = Column(Boolean, default=False)
    times_used   = Column(Integer, default=0)
    created_at   = Column(DateTime, default=datetime.utcnow)
