"""
Bannerbear Flyer Composer

Sends a generated avatar image URL to Bannerbear's API to composite a
professionally designed flyer using your pre-built Bannerbear templates.

── Setup ─────────────────────────────────────────────────────────────────────
1. Sign up at https://bannerbear.com → API → copy your API key → BANNERBEAR_API_KEY
2. Create one template per format in the Bannerbear editor (or duplicate the
   default and adjust canvas size). Set FLYER_COMPOSER=bannerbear in .env.
3. In each template, name your layers EXACTLY as follows so the API can find them:
     avatar       — image layer  (your face photo)
     headline     — text layer   (main headline)
     subheadline  — text layer   (supporting copy)
     cta_text     — text layer   (button / CTA)
     nmls_text    — text layer   (NMLS # · Name · Equal Housing footer)
     brand_name   — text layer   (app/brand name top-left)
4. Copy each template's ID and set:
     BANNERBEAR_TEMPLATE_ID_SOCIAL_SQUARE
     BANNERBEAR_TEMPLATE_ID_FACEBOOK_BANNER
     BANNERBEAR_TEMPLATE_ID_STORY
     BANNERBEAR_TEMPLATE_ID_WIDE_BANNER

── Note on avatar URL ────────────────────────────────────────────────────────
Bannerbear pulls images by URL. For local dev you need a public tunnel
(ngrok / Cloudflare Tunnel / Render preview) so Bannerbear can reach your
/media/avatars/ path. Set BACKEND_URL to that tunnel URL.
In production this works automatically.
"""

import asyncio
import uuid
import structlog
import httpx
from pathlib import Path
from typing import Optional

from app.config import settings

log = structlog.get_logger()

_SYNC_URL  = "https://sync.api.bannerbear.com/v2/images"
_ASYNC_URL = "https://api.bannerbear.com/v2/images"
_POLL_URL  = "https://api.bannerbear.com/v2/images/{uid}"


def _template_id(flyer_format: str) -> Optional[str]:
    return {
        "social_square":   settings.bannerbear_template_social_square,
        "facebook_banner": settings.bannerbear_template_facebook_banner,
        "story":           settings.bannerbear_template_story,
        "wide_banner":     settings.bannerbear_template_wide_banner,
    }.get(flyer_format) or None


async def compose_flyer_bannerbear(
    avatar_url: str,
    headline: str,
    subheadline: str,
    cta_text: str,
    flyer_format: str,
    banker_name: str,
    banker_nmls: str,
) -> dict:
    """
    Composite a flyer via Bannerbear. Returns {"path": str, "url": str}.
    Tries the synchronous endpoint first (≤20 s), falls back to async polling.
    Raises ValueError/RuntimeError/TimeoutError on failure.
    """
    tid = _template_id(flyer_format)
    if not tid:
        raise ValueError(
            f"No Bannerbear template configured for format '{flyer_format}'. "
            f"Set BANNERBEAR_TEMPLATE_ID_{flyer_format.upper()} in .env"
        )
    if not settings.bannerbear_api_key:
        raise ValueError("BANNERBEAR_API_KEY not set in .env")

    # Warn early if avatar URL is local (Bannerbear can't reach localhost)
    if "localhost" in avatar_url or "127.0.0.1" in avatar_url:
        log.warning(
            "bannerbear.local_url_warning",
            msg="Avatar URL is localhost — Bannerbear cannot pull it. "
                "Set BACKEND_URL to a public tunnel URL for Bannerbear to work.",
            avatar_url=avatar_url,
        )

    headers = {
        "Authorization": f"Bearer {settings.bannerbear_api_key}",
        "Content-Type": "application/json",
    }
    modifications = [
        {"name": "headline",    "text": headline},
        {"name": "subheadline", "text": subheadline or ""},
        {"name": "cta_text",    "text": cta_text or ""},
        {"name": "avatar",      "image_url": avatar_url},
        {"name": "nmls_text",   "text": f"NMLS #{banker_nmls}  ·  {banker_name}  ·  Equal Housing Opportunity"},
        {"name": "brand_name",  "text": settings.app_name.upper()},
    ]
    payload = {"template": tid, "modifications": modifications}

    async with httpx.AsyncClient(timeout=25) as client:
        # ── Try sync endpoint (blocks up to ~20 s, no polling needed) ──────
        try:
            resp = await client.post(_SYNC_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "completed" and data.get("image_url"):
                log.info("bannerbear.sync_complete", format=flyer_format)
                return await _download_and_save(client, data["image_url"], flyer_format)
            log.info("bannerbear.sync_not_ready — switching to async poll")
        except httpx.TimeoutException:
            log.warning("bannerbear.sync_timeout — switching to async poll")
        except httpx.HTTPStatusError as exc:
            # Non-2xx from sync endpoint → raise immediately so caller can fallback
            raise RuntimeError(f"Bannerbear sync error {exc.response.status_code}: {exc.response.text}") from exc

        # ── Async create + poll ─────────────────────────────────────────────
        resp = await client.post(_ASYNC_URL, headers=headers, json=payload)
        resp.raise_for_status()
        uid = resp.json()["uid"]
        log.info("bannerbear.async_started", uid=uid, format=flyer_format)

    # Poll outside original client so timeout resets per-request
    async with httpx.AsyncClient(timeout=15) as client:
        for _ in range(45):          # up to 90 s
            await asyncio.sleep(2)
            poll = await client.get(_POLL_URL.format(uid=uid), headers=headers)
            poll.raise_for_status()
            data = poll.json()
            if data.get("status") == "completed" and data.get("image_url"):
                log.info("bannerbear.async_complete", uid=uid, format=flyer_format)
                return await _download_and_save(client, data["image_url"], flyer_format)
            if data.get("status") == "failed":
                raise RuntimeError(f"Bannerbear render failed (uid={uid}): {data}")

    raise TimeoutError(f"Bannerbear render timed out after 90 s (uid={uid})")


async def _download_and_save(client: httpx.AsyncClient, image_url: str, flyer_format: str) -> dict:
    """Download the finished Bannerbear image and save to local media/flyers/."""
    resp = await client.get(image_url, timeout=30)
    resp.raise_for_status()

    content_type = resp.headers.get("content-type", "")
    ext = ".png" if "png" in content_type else ".jpg"
    filename = f"flyer_{flyer_format}_{uuid.uuid4().hex[:10]}{ext}"

    out_dir = Path(settings.media_storage_path) / "flyers"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_bytes(resp.content)

    served_url = f"{settings.backend_url}/media/flyers/{filename}"
    log.info("bannerbear.file_saved", filename=filename)
    return {"path": str(out_path), "url": served_url}
