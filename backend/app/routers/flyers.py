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
from app.middleware.auth import get_current_user, require_agent_key
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
    theme: Optional[str] = "midnight_gold"           # midnight_gold | ocean | forest | plum | slate_ember
    brand_name: Optional[str] = None                 # flyer brand label; defaults to FLYER_BRAND_NAME env
    logo_asset_id: Optional[int] = None              # BrandAsset id — logo composited into the footer strip
    logo_label: Optional[str] = None                 # text before the logo, e.g. "Powered by"


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
                theme=request_data.get("theme"),
                brand_name=request_data.get("brand_name"),
                logo_path=request_data.get("logo_path"),
                logo_label=request_data.get("logo_label"),
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

    # Resolve logo asset → local path (validated here so bad ids 404 immediately)
    request_data = data.model_dump()
    if data.logo_asset_id:
        from app.models.flyer import BrandAsset as _BA
        asset = (await db.execute(select(_BA).where(_BA.id == data.logo_asset_id))).scalar_one_or_none()
        if not asset:
            raise HTTPException(404, f"logo_asset_id {data.logo_asset_id} not found. GET /flyers/assets to list.")
        request_data["logo_path"] = asset.image_path

    # Run pipeline in background
    background_tasks.add_task(
        _run_pipeline,
        flyer_id=flyer_id,
        db_url=settings.database_url,
        ref_path=ref.file_path,
        style_prompt=style_prompt,
        request_data=request_data,
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
        "layout": f.layout,
        "layout_data": f.layout_data,
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
    layout: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_agent_key),
):
    q = select(GeneratedFlyer).order_by(desc(GeneratedFlyer.created_at)).limit(limit)
    if status:
        q = q.where(GeneratedFlyer.status == status)
    if use_case:
        q = q.where(GeneratedFlyer.use_case == use_case)
    if layout:
        q = q.where(GeneratedFlyer.layout == layout)
    rows = (await db.execute(q)).scalars().all()
    return {"count": len(rows), "flyers": [_flyer_dict(f) for f in rows]}


@router.get("/style-presets")
async def list_style_presets(current_user: User = Depends(get_current_user)):
    """List available AI style presets."""
    return {k: v[:80] + "..." for k, v in STYLE_PRESETS.items()}


# ── Avatar library — save best renders for reuse ──────────────────────────────
# Auth: require_agent_key (agent API key OR admin JWT) — the agent browses and
# reuses this library when building flyers.

from app.models.flyer import SavedAvatar


def _avatar_dict(a: SavedAvatar) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "source": a.source,
        "style_preset": a.style_preset,
        "image_url": a.image_url,
        "is_favorite": a.is_favorite,
        "times_used": a.times_used,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


class AvatarSaveRequest(BaseModel):
    flyer_id: int                    # save the avatar used by this flyer
    name: str                        # operator-friendly label
    is_favorite: bool = False


class AvatarUpdateRequest(BaseModel):
    name: Optional[str] = None
    is_favorite: Optional[bool] = None


@router.get("/avatars")
async def list_saved_avatars(db: AsyncSession = Depends(get_db),
                              _auth=Depends(require_agent_key)):
    """Avatar library — favorites first, then most recently saved."""
    rows = (await db.execute(
        select(SavedAvatar).order_by(desc(SavedAvatar.is_favorite), desc(SavedAvatar.created_at))
    )).scalars().all()
    return {"count": len(rows), "avatars": [_avatar_dict(a) for a in rows]}


@router.post("/avatars", status_code=201)
async def save_avatar(data: AvatarSaveRequest, db: AsyncSession = Depends(get_db),
                       _auth=Depends(require_agent_key)):
    """Save the avatar from an existing flyer into the reuse library."""
    f = (await db.execute(select(GeneratedFlyer).where(GeneratedFlyer.id == data.flyer_id))).scalar_one_or_none()
    if not f:
        raise HTTPException(404, "Flyer not found")
    if not f.avatar_image_path or not Path(f.avatar_image_path).exists():
        raise HTTPException(400, "That flyer has no avatar image on disk to save")

    # Copy the file so deleting the flyer later doesn't break the library
    lib_dir = Path(settings.media_storage_path) / "avatars" / "library"
    lib_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(f.avatar_image_path).suffix or ".png"
    filename = f"saved_{uuid.uuid4().hex[:10]}{ext}"
    dest = lib_dir / filename
    shutil.copy2(f.avatar_image_path, dest)

    avatar = SavedAvatar(
        name=data.name,
        source=f.provider or "openai",
        style_preset=f.avatar_style[:120] if f.avatar_style else None,
        image_path=str(dest),
        image_url=f"{settings.backend_url}/media/avatars/library/{filename}",
        is_favorite=data.is_favorite,
    )
    db.add(avatar)
    await db.commit()
    await db.refresh(avatar)
    await log_event(db, "avatar.saved", actor_type="user",
                    details={"avatar_id": avatar.id, "name": data.name, "from_flyer": data.flyer_id})
    await db.commit()
    return _avatar_dict(avatar)


@router.post("/avatars/upload", status_code=201)
async def upload_avatar(
    file: UploadFile = File(...),
    name: str = "Uploaded avatar",
    source: str = "upload",              # upload | heygen | reference
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_agent_key),
):
    """
    Add an external image to the avatar library — e.g. a HeyGen avatar still,
    or any photo the operator wants flyers built around.
    """
    if source not in ("upload", "heygen", "reference"):
        raise HTTPException(422, "source must be one of: upload | heygen | reference")
    lib_dir = Path(settings.media_storage_path) / "avatars" / "library"
    lib_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "avatar.png").suffix or ".png"
    filename = f"saved_{uuid.uuid4().hex[:10]}{ext}"
    dest = lib_dir / filename
    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out)

    avatar = SavedAvatar(
        name=name,
        source=source,
        image_path=str(dest),
        image_url=f"{settings.backend_url}/media/avatars/library/{filename}",
    )
    db.add(avatar)
    await db.commit()
    await db.refresh(avatar)
    return _avatar_dict(avatar)


@router.patch("/avatars/{avatar_id}")
async def update_avatar(avatar_id: int, data: AvatarUpdateRequest,
                         db: AsyncSession = Depends(get_db),
                         _auth=Depends(require_agent_key)):
    """Rename or favorite/unfavorite a saved avatar."""
    a = (await db.execute(select(SavedAvatar).where(SavedAvatar.id == avatar_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Saved avatar not found")
    if data.name is not None:
        a.name = data.name
    if data.is_favorite is not None:
        a.is_favorite = data.is_favorite
    await db.commit()
    await db.refresh(a)
    return _avatar_dict(a)


@router.delete("/avatars/{avatar_id}")
async def delete_saved_avatar(avatar_id: int, db: AsyncSession = Depends(get_db),
                               _auth=Depends(require_agent_key)):
    """Remove an avatar from the library (deletes its library copy on disk)."""
    a = (await db.execute(select(SavedAvatar).where(SavedAvatar.id == avatar_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Saved avatar not found")
    if a.image_path and Path(a.image_path).exists():
        try:
            Path(a.image_path).unlink()
        except Exception:
            pass
    await db.delete(a)
    await db.commit()
    return {"deleted": True, "id": avatar_id}


# ── Brand asset library — logos / images the agent can find by name ───────────

from app.models.flyer import BrandAsset


def _asset_dict(a: BrandAsset) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "kind": a.kind,
        "image_url": a.image_url,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/assets")
async def list_brand_assets(kind: Optional[str] = None,
                             db: AsyncSession = Depends(get_db),
                             _auth=Depends(require_agent_key)):
    """List uploaded brand assets (logos, images, screenshots) — newest first."""
    q = select(BrandAsset).order_by(desc(BrandAsset.created_at))
    if kind:
        q = q.where(BrandAsset.kind == kind)
    rows = (await db.execute(q)).scalars().all()
    return {"count": len(rows), "assets": [_asset_dict(a) for a in rows]}


@router.post("/assets/upload", status_code=201)
async def upload_brand_asset(
    file: UploadFile = File(...),
    name: str = "asset",
    kind: str = "logo",                  # logo | image | screenshot
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_agent_key),
):
    """
    Upload a brand asset (PNG/JPEG) with a simple name the agent can find later —
    e.g. name="uwm logo" then ask the agent: 'add the uwm logo to that flyer'.
    """
    if kind not in ("logo", "image", "screenshot"):
        raise HTTPException(422, "kind must be one of: logo | image | screenshot")
    ext = Path(file.filename or "asset.png").suffix.lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        raise HTTPException(422, "Only PNG, JPEG, or WebP images are supported")
    asset_dir = Path(settings.media_storage_path) / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    filename = f"asset_{uuid.uuid4().hex[:10]}{ext}"
    dest = asset_dir / filename
    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out)

    asset = BrandAsset(
        name=name.strip().lower(),
        kind=kind,
        image_path=str(dest),
        image_url=f"{settings.backend_url}/media/assets/{filename}",
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    await log_event(db, "brand_asset.uploaded", actor_type="user",
                    details={"asset_id": asset.id, "name": asset.name, "kind": kind})
    await db.commit()
    return _asset_dict(asset)


@router.delete("/assets/{asset_id}")
async def delete_brand_asset(asset_id: int, db: AsyncSession = Depends(get_db),
                              _auth=Depends(require_agent_key)):
    a = (await db.execute(select(BrandAsset).where(BrandAsset.id == asset_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Asset not found")
    if a.image_path and Path(a.image_path).exists():
        try:
            Path(a.image_path).unlink()
        except Exception:
            pass
    await db.delete(a)
    await db.commit()
    return {"deleted": True, "id": asset_id}


@router.get("/{flyer_id}")
async def get_flyer(flyer_id: int, db: AsyncSession = Depends(get_db),
                    _auth=Depends(require_agent_key)):
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
