"""
Avatar Generator — AI face-consistent image generation + background removal.

── Providers ─────────────────────────────────────────────────────────────────
  openai      Uses gpt-image-1 image editing. Sends your photo + a style
              prompt ("put me in a navy suit"). Natural language — simple.
              Uses your existing OPENAI_API_KEY. Best starting point.

  fal         fal.ai flux-pulid. Best raw face-consistency. Separate FAL_API_KEY.

  replicate   Replicate photomaker-v2. Backup option. REPLICATE_API_TOKEN.

  passthrough No AI. Copies your reference photo as-is. Zero cost, instant.
              Good for testing or when no API key is set.

  auto        (default) Tries: openai → fal → replicate → passthrough.
              Uses whatever key you've set. No config headache.

── Background removal ────────────────────────────────────────────────────────
  remove_background(image_path) uses rembg (runs locally, zero cost) to cut
  the person out of the AI-generated image. Returns a transparent PNG.
  The flyer builder then composites that clean cutout onto the branded template.

  Falls back gracefully if rembg is not installed.

── AVATAR_PROVIDER env var ───────────────────────────────────────────────────
  Set AVATAR_PROVIDER=openai  to use OpenAI explicitly.
  Set AVATAR_PROVIDER=fal     for best quality.
  Omit or set to "auto"       to let the system pick based on available keys.
"""

import io as _io
import os
import uuid
import base64
import asyncio
import shutil
import structlog
import httpx
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from app.config import settings

log = structlog.get_logger()


# ── Style presets ─────────────────────────────────────────────────────────────

STYLE_PRESETS = {
    "suit_headshot": (
        "professional mortgage banker in a crisp navy blue suit and white dress shirt, "
        "confident warm smile, modern office background with soft bokeh, natural lighting, "
        "photorealistic, high-quality portrait photography"
    ),
    "casual_expert": (
        "friendly mortgage advisor in smart casual attire, approachable smile, "
        "modern home or coffee shop background, warm natural light, "
        "photorealistic lifestyle photography"
    ),
    "outdoor_realtor": (
        "real estate professional standing in front of a beautiful suburban home, "
        "business casual attire, warm sunny day, confident welcoming expression, "
        "photorealistic"
    ),
    "dark_brand": (
        "professional mortgage banker in dark charcoal suit, confident pose, "
        "dark studio background with warm gold accent lighting, "
        "high-end corporate brand photography, dramatic lighting"
    ),
    "community": (
        "friendly local mortgage expert in business casual, standing in a welcoming "
        "residential neighborhood, warm afternoon light, approachable and trustworthy expression, "
        "photorealistic"
    ),
}


@dataclass
class AvatarResult:
    success: bool
    image_path: Optional[str] = None   # local file path
    image_url: Optional[str] = None    # served URL
    provider: str = "passthrough"
    error: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _media_dir() -> Path:
    p = Path(settings.media_storage_path) / "avatars"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _encode_photo(photo_path: str) -> str:
    """Encode a local image as a base64 data URI."""
    path = Path(photo_path)
    if not path.exists():
        raise FileNotFoundError(f"Reference photo not found: {photo_path}")
    ext = path.suffix.lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _save_bytes(data: bytes, prefix: str = "avatar", ext: str = ".png") -> Tuple[str, str]:
    """Save raw image bytes to media/avatars/. Returns (local_path, served_url)."""
    filename = f"{prefix}_{uuid.uuid4().hex[:12]}{ext}"
    save_path = _media_dir() / filename
    save_path.write_bytes(data)
    served_url = f"{settings.backend_url}/media/avatars/{filename}"
    return str(save_path), served_url


# ── Background removal ────────────────────────────────────────────────────────

async def remove_background(image_path: str) -> Tuple[str, str]:
    """
    Remove background from an avatar image, returning a transparent PNG.

    Provider chain (first available wins):
      1. rembg        — local, free, zero API cost. Requires Python ≤3.11
                        (llvmlite build dep; install: pip install rembg)
      2. remove.bg    — REMOVE_BG_API_KEY in .env. 50 free images/month.
                        Works on any Python version including 3.13.
      3. passthrough  — no removal; original image returned unchanged.

    Returns (local_path, served_url).
    """
    # ── 1. rembg (local, zero cost) ───────────────────────────────────────────
    try:
        from rembg import remove as _rembg_remove

        input_bytes = Path(image_path).read_bytes()
        # rembg is CPU-bound sync — run in executor to avoid blocking event loop
        output_bytes = await asyncio.get_event_loop().run_in_executor(
            None, _rembg_remove, input_bytes
        )
        local_path, served_url = _save_bytes(output_bytes, prefix="avatar_nobg", ext=".png")
        log.info("avatar_generator.bg_removed_rembg", path=local_path)
        return local_path, served_url

    except ImportError:
        pass   # not installed — fall through to next option
    except Exception as exc:
        log.warning("avatar_generator.rembg_failed", error=str(exc))

    # ── 2. remove.bg API ──────────────────────────────────────────────────────
    removebg_key = os.getenv("REMOVE_BG_API_KEY", "")
    if removebg_key:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.remove.bg/v1.0/removebg",
                    headers={"X-Api-Key": removebg_key},
                    files={"image_file": ("avatar.jpg", Path(image_path).read_bytes(), "image/jpeg")},
                    data={"size": "auto"},
                )
                if resp.status_code == 200:
                    local_path, served_url = _save_bytes(resp.content, prefix="avatar_nobg", ext=".png")
                    log.info("avatar_generator.bg_removed_removebg", path=local_path)
                    return local_path, served_url
                log.warning("avatar_generator.removebg_api_error",
                             status=resp.status_code, body=resp.text[:200])
        except Exception as exc:
            log.warning("avatar_generator.removebg_failed", error=str(exc))

    # ── 3. Passthrough ────────────────────────────────────────────────────────
    log.info("avatar_generator.bg_removal_skipped — set REMOVE_BG_API_KEY or install rembg")
    orig_name = Path(image_path).name
    return image_path, f"{settings.backend_url}/media/avatars/{orig_name}"


# ── OpenAI gpt-image-1 ────────────────────────────────────────────────────────

async def _generate_openai(
    reference_photo_path: str,
    style_prompt: str,
    output_size: str,
) -> AvatarResult:
    """
    Generate avatar using OpenAI gpt-image-1 image editing.

    Sends your reference photo + a natural-language style prompt.
    The model rewrites your attire, background, and lighting while
    preserving your face and identity.

    No extra API key — uses your existing OPENAI_API_KEY.
    """
    from PIL import Image

    if not settings.openai_api_key:
        return AvatarResult(success=False, provider="openai", error="OPENAI_API_KEY not set")

    size_map = {
        "square_hd": "1024x1024",
        "portrait":  "1024x1536",
        "landscape": "1536x1024",
        "story":     "1024x1536",
    }

    try:
        # gpt-image-1 edit endpoint requires PNG
        img = Image.open(reference_photo_path).convert("RGBA")
        png_buf = _io.BytesIO()
        img.save(png_buf, format="PNG")
        png_buf.seek(0)

        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

        full_prompt = (
            f"{style_prompt}. "
            "Preserve the person's face, skin tone, and identity exactly. "
            "Professional quality, photorealistic."
        )

        response = await client.images.edit(
            model="gpt-image-1",
            image=("reference.png", png_buf, "image/png"),
            prompt=full_prompt,
            size=size_map.get(output_size, "1024x1024"),
            n=1,
        )

        img_data = base64.b64decode(response.data[0].b64_json)
        local_path, served_url = _save_bytes(img_data, prefix="avatar_oai", ext=".png")
        log.info("avatar_generator.openai_success", path=local_path)

        return AvatarResult(
            success=True,
            image_path=local_path,
            image_url=served_url,
            provider="openai",
        )

    except Exception as exc:
        log.error("avatar_generator.openai_error", error=str(exc))
        return AvatarResult(success=False, provider="openai", error=str(exc))


# ── fal.ai flux-pulid ─────────────────────────────────────────────────────────

async def _generate_fal(
    reference_photo_path: str,
    style_prompt: str,
    output_size: str,
) -> AvatarResult:
    """Generate avatar via fal.ai flux-pulid — best raw face-consistency."""
    try:
        data_uri = _encode_photo(reference_photo_path)
    except FileNotFoundError as e:
        return AvatarResult(success=False, error=str(e))

    size_map = {
        "square_hd": "square_hd",
        "portrait":  "portrait_4_3",
        "landscape": "landscape_4_3",
        "story":     "portrait_16_9",
    }

    payload = {
        "main_face_image": data_uri,
        "prompt": style_prompt,
        "num_images": 1,
        "image_size": size_map.get(output_size, "square_hd"),
        "num_inference_steps": 20,
        "guidance_scale": 4.0,
        "true_cfg": 1.0,
        "id_weight": 1.0,
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://fal.run/fal-ai/flux-pulid",
                headers={
                    "Authorization": f"Key {settings.fal_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code != 200:
                return AvatarResult(
                    success=False, provider="fal",
                    error=f"fal.ai {resp.status_code}: {resp.text[:300]}",
                )
            images = resp.json().get("images", [])
            if not images:
                return AvatarResult(success=False, provider="fal", error="fal.ai returned no images")

            img_resp = await client.get(images[0]["url"], timeout=30)
            local_path, served_url = _save_bytes(img_resp.content, prefix="avatar_fal", ext=".jpg")
            log.info("avatar_generator.fal_success", path=local_path)

            return AvatarResult(
                success=True, image_path=local_path, image_url=served_url, provider="fal"
            )

    except httpx.TimeoutException:
        return AvatarResult(success=False, provider="fal",
                            error="fal.ai timed out (120 s). Try again or switch provider.")
    except Exception as exc:
        log.error("avatar_generator.fal_error", error=str(exc))
        return AvatarResult(success=False, provider="fal", error=str(exc))


# ── Replicate photomaker-v2 ───────────────────────────────────────────────────

async def _generate_replicate(
    reference_photo_path: str,
    style_prompt: str,
) -> AvatarResult:
    """Generate avatar via Replicate photomaker-v2 (backup)."""
    try:
        data_uri = _encode_photo(reference_photo_path)
    except FileNotFoundError as e:
        return AvatarResult(success=False, error=str(e))

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                "https://api.replicate.com/v1/models/tencentarc/photomaker-v2/predictions",
                headers={
                    "Authorization": f"Bearer {settings.replicate_api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": {
                        "input_image": data_uri,
                        "prompt": f"img {style_prompt}",  # photomaker needs "img" token
                        "num_outputs": 1,
                        "style_strength_ratio": 35,
                    }
                },
            )
            if resp.status_code not in (200, 201):
                return AvatarResult(success=False, provider="replicate",
                                    error=f"Replicate {resp.status_code}: {resp.text[:300]}")

            pred_id = resp.json()["id"]
            for _ in range(60):
                await asyncio.sleep(3)
                poll = await client.get(
                    f"https://api.replicate.com/v1/predictions/{pred_id}",
                    headers={"Authorization": f"Bearer {settings.replicate_api_token}"},
                )
                result = poll.json()
                if result["status"] == "succeeded":
                    img_resp = await client.get(result["output"][0], timeout=30)
                    local_path, served_url = _save_bytes(
                        img_resp.content, prefix="avatar_rep", ext=".jpg"
                    )
                    return AvatarResult(
                        success=True, image_path=local_path,
                        image_url=served_url, provider="replicate",
                    )
                if result["status"] == "failed":
                    return AvatarResult(
                        success=False, provider="replicate",
                        error=f"Replicate failed: {result.get('error', 'unknown')}",
                    )

        return AvatarResult(success=False, provider="replicate",
                            error="Replicate timed out after 3 minutes.")

    except Exception as exc:
        log.error("avatar_generator.replicate_error", error=str(exc))
        return AvatarResult(success=False, provider="replicate", error=str(exc))


# ── Passthrough ───────────────────────────────────────────────────────────────

async def _passthrough(reference_photo_path: str) -> AvatarResult:
    """No AI — copies reference photo into avatars dir. Zero cost, instant."""
    try:
        path = Path(reference_photo_path)
        if not path.exists():
            return AvatarResult(success=False, error="Reference photo not found. Upload one first.")
        filename = f"avatar_ref_{uuid.uuid4().hex[:8]}{path.suffix}"
        save_path = _media_dir() / filename
        shutil.copy2(path, save_path)
        served_url = f"{settings.backend_url}/media/avatars/{filename}"
        return AvatarResult(
            success=True, image_path=str(save_path),
            image_url=served_url, provider="passthrough",
        )
    except Exception as exc:
        return AvatarResult(success=False, provider="passthrough", error=str(exc))


# ── Main entry point ──────────────────────────────────────────────────────────

async def generate_avatar(
    reference_photo_path: str,
    style_prompt: str,
    output_size: str = "square_hd",
) -> AvatarResult:
    """
    Generate an AI avatar from a reference face photo.

    Provider is controlled by AVATAR_PROVIDER in .env:
      auto        — openai → fal → replicate → passthrough (default)
      openai      — gpt-image-1 edit (uses existing OPENAI_API_KEY)
      fal         — flux-pulid (best face consistency, needs FAL_API_KEY)
      replicate   — photomaker-v2 (backup, needs REPLICATE_API_TOKEN)
      passthrough — no AI, uses photo as-is
    """
    provider = settings.avatar_provider.lower()

    if provider == "passthrough":
        return await _passthrough(reference_photo_path)

    if provider == "openai":
        result = await _generate_openai(reference_photo_path, style_prompt, output_size)
        if not result.success:
            log.warning("avatar_generator.openai_failed — using passthrough", error=result.error)
            return await _passthrough(reference_photo_path)
        return result

    if provider == "fal":
        result = await _generate_fal(reference_photo_path, style_prompt, output_size)
        if not result.success:
            log.warning("avatar_generator.fal_failed — using passthrough", error=result.error)
            return await _passthrough(reference_photo_path)
        return result

    if provider == "replicate":
        result = await _generate_replicate(reference_photo_path, style_prompt)
        if not result.success:
            log.warning("avatar_generator.replicate_failed — using passthrough", error=result.error)
            return await _passthrough(reference_photo_path)
        return result

    # ── Auto mode: try each in order until one works ──────────────────────────
    if settings.openai_api_key:
        log.info("avatar_generator.auto → openai")
        result = await _generate_openai(reference_photo_path, style_prompt, output_size)
        if result.success:
            return result
        log.warning("avatar_generator.openai_failed", error=result.error)

    if settings.fal_api_key:
        log.info("avatar_generator.auto → fal")
        result = await _generate_fal(reference_photo_path, style_prompt, output_size)
        if result.success:
            return result
        log.warning("avatar_generator.fal_failed", error=result.error)

    if settings.replicate_api_token:
        log.info("avatar_generator.auto → replicate")
        result = await _generate_replicate(reference_photo_path, style_prompt)
        if result.success:
            return result
        log.warning("avatar_generator.replicate_failed", error=result.error)

    log.info("avatar_generator.auto → passthrough (no keys set)")
    return await _passthrough(reference_photo_path)


def get_style_preset(preset_key: str) -> str:
    """Get a predefined style prompt by key."""
    return STYLE_PRESETS.get(preset_key, STYLE_PRESETS["suit_headshot"])
