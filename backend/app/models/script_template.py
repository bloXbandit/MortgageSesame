"""
ScriptTemplate — editable templates that guide AI content generation.

This is the "media center" for script editing. Instead of changing code
when you want to shift tone, hooks, or CTAs, you edit templates here via
the admin UI or API and the AI picks them up on next generation.

Template types:
  hook        — Opening line the AI should use as a style reference
  cta         — Call-to-action text or style to follow
  style_guide — Tone/voice instructions ("be conversational, not salesy")
  full_script — A complete example script the AI should mirror in structure
  objection   — How to handle common objections in scripts

Templates can be platform-specific (tiktok only) or global (platform=None).
They can be category-specific (dpa_myths only) or global (category=None).
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from typing import Optional


class ScriptTemplate(Base):
    __tablename__ = "script_templates"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))

    # Scope — None means "applies to all"
    platform: Mapped[Optional[str]] = mapped_column(String(50))     # tiktok, instagram_reel, etc.
    category: Mapped[Optional[str]] = mapped_column(String(100))    # dpa_myths, refi_triggers, etc.

    # Type of template
    template_type: Mapped[str] = mapped_column(
        String(50), default="style_guide"
    )
    # hook | cta | style_guide | full_script | objection | tone_guide

    # The actual content — what the AI sees
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional: note what variables are expected ({{first_name}}, {{rate}}, etc.)
    variables: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # Controls
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(default=0)  # higher = injected first

    created_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
