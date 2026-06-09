"""
Flyer & Avatar Generation API

Routes:
  POST  /flyers/reference-photo        Upload / update the banker's reference face photo
  GET   /flyers/reference-photo        Get current reference photo info
  POST  /flyers/generate               Generate avatar + build flyer (full pipeline)
  GET   /flyers/                       List all generated flyers
  GET   /flyers/{id}                   Single flyer detail
  DELETE /flyers/{id}                  Delete a flyer

Agent endpoint (in agent.py):
  POST  /agent/build-flyer             Agent-triggered flyer build
"""

import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.audit import log_event
from app.models.flyer import GeneratedFlyer, ReferencePhoto
from app.models.user import User
from app.services.avatar_generator import generate_avatar, remove_background, get_style_preset, STYLE_PRESETS
from app.services.flyer_builder import build_flyer, build_flyer_async, TEMPLATE_MAP

log = structlog.get_logger()
router = APIRouter(prefix="/flyers", tags=["flyers"])


# ── Reference photo upload ────────────────────────────────────────────────────

@router.post("/reference-photo")
async def upload_reference_photo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload or replace the banker's reference face photo.
    This photo is used as the identity anchor for all AI avatar generation.
    JPEG or PNG, ideally a clear frontal face photo.
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Only JPEG, PNG, or WebP images are accepted.")

    ext = Path(file.filename).suffix or ".jpg"
    save_dir = Path(settings.media_storage_path) / "avatar"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"reference{ext}"

    content = await file.read()
    save_path.write_bytes(content)

    served_url = f"{settings.backend_url}/media/avatar/reference{ext}"

    # Upsert — only one reference photo per system
    existing = (await db.execute(select(ReferencePhoto).limit(1))).scalar_one_or_none()
    if existing:
        existing.file_path = str(save_path)
        existing.file_url = served_url
        existing.uploaded_by = str(current_user.id)
        existing.updated_at = datetime.utcnow()
    else:
        db.add(ReferencePhoto(
            file_path=str(save_path),
            file_url=served_url,
            uploaded_by=str(current_user.id),
        ))

    await db.commit()
    await log_event(db, "flyer.reference_photo_uploaded", actor_id=str(current_user.id),
                    actor_type="user", details={"path": str(save_path)})
    await db.commit()

    return {
        "status": "uploaded",
        "file_url": served_url,
        "path": str(save_path),
        "note": "Reference photo saved. You can now generate flyers.",
    }


@router.get("/reference-photo")
async def get_reference_photo(db: AsyncSession = Depends(get_db),
                               current_user: User = Depends(get_current_user)):
    ref = (await db.execute(select(ReferencePhoto).limit(1))).scalar_one_or_none()
    if not ref:
        return {"uploaded": False, "note": "No reference photo yet. Upload one to enable AI avatar generation."}
    return {
        "uploaded": True,
        "file_url": ref.file_url,
        "uploaded_at": ref.created_at.isoformat() if ref.created_at else None,
        "updated_at": ref.updated_at.isoformat() if ref.updated_at else None,
    }


# ── Flyer generation ──────────────────────────────────────────────────────────

class FlyerGenerateRequest(BaseModel):
    use_case: str = "purchase"              # purchase | dpa | refi | realtor | generic
    flyer_format: str = "social_square"     # social_square | facebook_banner | story | wide_banner
    headline: str
    subheadline: Optional[str] = ""
    cta_text: Optional[str] = "Book a Free Call →"
    style_preset: Optional[str] = "suit_headshot"   # key from STYLE_PRESETS
    style_prompt_override: Optional[str] = None     # custom prompt, overrides preset
    skip_ai: bool = False                            # skip AI generation, use photo directly


async def _run_pipeline(flyer_id: int, db_url: str, ref_path: str,
                         style_prompt: str, request_data: dict):
    """Background task: generate avatar then composite flyer."""
    from app.database import AsyncSessionLocal
    from sqlalchemy import update

    async with AsyncSessionLocal() as db:
        try:
            # Step 1 — AI avatar
            skip_ai = request_data.get("skip_ai", False)
            if skip_ai:
                from app.services.avatar_generator import _passthrough
                avatar_result = await _passthrough(ref_path)
            else:
                from app.services.avatar_generator import generate_avatar
                avatar_result = await generate_avatar(
                    reference_photo_path=ref_path,
                    style_prompt=style_prompt,
                    output_size=_format_to_size(request_data["flyer_format"]),
                )

            if not avatar_result.success:
                await db.execute(
                    update(GeneratedFlyer)
                    .where(GeneratedFlyer.id == flyer_id)
                    .values(status="failed", error=avatar_result.error)
                )
                await db.commit()
                return

            # Step 2 — Background removal (rembg, local, zero cost)
            # Cuts the person out of the AI image → transparent PNG for cleaner flyer composite
            skip_ai = request_data.get("skip_ai", False)
            if not skip_ai and avatar_result.image_path:
                bg_path, bg_url = await remove_background(avatar_result.image_path)
            else:
                bg_path = avatar_result.image_path
                bg_url  = avatar_result.image_url

            # Update DB — avatar ready, bg removed
            await db.execute(
                update(GeneratedFlyer)
                .where(GeneratedFlyer.id == flyer_id)
                .values(
                    status="avatar_ready",
                    avatar_image_path=bg_path,
                    avatar_image_url=bg_url,
                    provider=avatar_result.provider,
                )
            )
            await db.commit()

            # Step 3 — Composite flyer (Bannerbear if configured, else Pillow)
            flyer_result = await build_flyer_async(
                avatar_image_path=bg_path,
                avatar_image_url=bg_url,
                headline=request_data["headline"],
                subheadline=request_data.get("subheadline", ""),
                cta_text=request_data.get("cta_text", ""),
                flyer_format=request_data["flyer_format"],
            )

            await db.execute(
                update(GeneratedFlyer)
                .where(GeneratedFlyer.id == flyer_id)
                .values(
                    status="complete",
                    flyer_image_path=flyer_result["path"],
                    flyer_image_url=flyer_result["url"],
                )
            )
            await db.commit()
            log.info("flyer_pipeline.complete", flyer_id=flyer_id)

        except Exception as exc:
            log.error("flyer_pipeline.failed", flyer_id=flyer_id, error=str(exc))
            try:
                await db.execute(
                    update(GeneratedFlyer)
                    .where(GeneratedFlyer.id == flyer_id)
                    .values(status="failed", error=str(exc))
                )
                await db.commit()
            except Exception:
                pass


def _format_to_size(flyer_format: str) -> str:
    return {
        "social_square":   "square_hd",
        "story":           "story",
        "facebook_banner": "landscape",
        "wide_banner":     "landscape",
    }.get(flyer_format, "square_hd")


@router.post("/generate")
async def generate_flyer(
    data: FlyerGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Full pipeline: AI avatar generation → branded flyer compositing.

    Returns immediately with a flyer ID and status=pending.
    Poll GET /flyers/{id} to check when status=complete.
    """
    if data.flyer_format not in TEMPLATE_MAP:
        raise HTTPException(400, f"Invalid format. Valid: {list(TEMPLATE_MAP.keys())}")

    # Get reference photo
    ref = (await db.execute(select(ReferencePhoto).limit(1))).scalar_one_or_none()
    if not ref or not ref.file_path or not Path(ref.file_path).exists():
        raise HTTPException(400, "No reference photo uploaded. POST /flyers/reference-photo first.")

    # Resolve style prompt
    style_prompt = (
        data.style_prompt_override
        or get_style_preset(data.style_preset or "suit_headshot")
    )

    # Create DB record
    flyer = GeneratedFlyer(
        use_case=data.use_case,
        flyer_format=data.flyer_format,
        avatar_style=style_prompt,
        headline=data.headline,
        subheadline=data.subheadline,
        cta_text=data.cta_text,
        status="pending",
        created_by=str(current_user.id),
    )
    db.add(flyer)
    await db.flush()
    flyer_id = flyer.id
    await db.commit()

    # Run pipeline in background
    background_tasks.add_task(
        _run_pipeline,
        flyer_id=flyer_id,
        db_url=settings.database_url,
        ref_path=ref.file_path,
        style_prompt=style_prompt,
        request_data=data.model_dump(),
    )

    await log_event(db, "flyer.generation_started", actor_id=str(current_user.id),
                    actor_type="user", details={"flyer_id": flyer_id, "format": data.flyer_format})
    await db.commit()

    return {
        "flyer_id": flyer_id,
        "status": "pending",
        "message": "Generation started. Poll GET /flyers/{flyer_id} for status.",
        "poll_url": f"/api/v1/flyers/{flyer_id}",
    }


# ── List / get / delete ───────────────────────────────────────────────────────

def _flyer_dict(f: GeneratedFlyer) -> dict:
    return {
        "id": f.id,
        "use_case": f.use_case,
        "flyer_format": f.flyer_format,
        "headline": f.headline,
        "subheadline": f.subheadline,
        "cta_text": f.cta_text,
        "provider": f.provider,
        "avatar_image_url": f.avatar_image_url,
        "flyer_image_url": f.flyer_image_url,
        "status": f.status,
        "error": f.error,
        "created_by": f.created_by,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.get("/")
async def list_flyers(
    status: Optional[str] = None,
    use_case: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(GeneratedFlyer).order_by(desc(GeneratedFlyer.created_at)).limit(limit)
    if status:
        q = q.where(GeneratedFlyer.status == status)
    if use_case:
        q = q.where(GeneratedFlyer.use_case == use_case)
    rows = (await db.execute(q)).scalars().all()
    return {"count": len(rows), "flyers": [_flyer_dict(f) for f in rows]}


@router.get("/style-presets")
async def list_style_presets(current_user: User = Depends(get_current_user)):
    """List available AI style presets."""
    return {k: v[:80] + "..." for k, v in STYLE_PRESETS.items()}


@router.get("/{flyer_id}")
async def get_flyer(flyer_id: int, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    f = (await db.execute(select(GeneratedFlyer).where(GeneratedFlyer.id == flyer_id))).scalar_one_or_none()
    if not f:
        raise HTTPException(404, "Flyer not found")
    return _flyer_dict(f)


@router.delete("/{flyer_id}")
async def delete_flyer(flyer_id: int, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    f = (await db.execute(select(GeneratedFlyer).where(GeneratedFlyer.id == flyer_id))).scalar_one_or_none()
    if not f:
        raise HTTPException(404, "Flyer not found")

    # Clean up files
    for p in [f.avatar_image_path, f.flyer_image_path]:
        if p and Path(p).exists():
            try:
                Path(p).unlink()
            except Exception:
                pass

    await db.delete(f)
    await db.commit()
    return {"deleted": flyer_id}
