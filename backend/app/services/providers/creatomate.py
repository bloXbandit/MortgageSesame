"""
Creatomate video assembly provider.

Renders a branded final video by layering the raw HeyGen avatar clip over
a platform-optimised template (lower thirds, captions, logo, CTA overlay).

Required ENV:
  CREATOMATE_API_KEY
  CREATOMATE_TEMPLATE_ID_TIKTOK
  CREATOMATE_TEMPLATE_ID_REELS
  CREATOMATE_TEMPLATE_ID_LINKEDIN

Template dynamic element names (must match what you built in the Creatomate editor):
  video_url     — URL of the source video clip
  caption_text  — subtitle / caption overlay
  hook_text     — opening text card
  cta_text      — call-to-action overlay text
  logo_url      — brand logo (can point to a static asset URL)
"""

import os
import asyncio
import httpx
import structlog
from dataclasses import dataclass
from typing import Optional

log = structlog.get_logger()

BASE = "https://api.creatomate.com/v1"
MAX_POLL_ATTEMPTS = 40   # 40 × 10s = ~6 min max wait
POLL_INTERVAL    = 10    # seconds


@dataclass
class CreatomateResult:
    success: bool
    render_id: Optional[str] = None
    status: str = "queued"              # queued | rendering | succeeded | failed
    output_url: Optional[str] = None
    error: Optional[str] = None


class CreatomateProvider:

    PLATFORM_TEMPLATE_ENV = {
        "tiktok":           "CREATOMATE_TEMPLATE_ID_TIKTOK",
        "instagram_reel":   "CREATOMATE_TEMPLATE_ID_REELS",
        "instagram_carousel": "CREATOMATE_TEMPLATE_ID_REELS",
        "linkedin":         "CREATOMATE_TEMPLATE_ID_LINKEDIN",
        "facebook":         "CREATOMATE_TEMPLATE_ID_TIKTOK",  # reuse vertical
    }

    def __init__(self):
        self.api_key = os.getenv("CREATOMATE_API_KEY", "")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_template_id(self, platform: str) -> Optional[str]:
        env_key = self.PLATFORM_TEMPLATE_ENV.get(platform)
        if not env_key:
            return None
        return os.getenv(env_key, "") or None

    async def render(
        self,
        template_id: str,
        video_url: str,
        caption_text: str = "",
        hook_text: str = "",
        cta_text: str = "",
        logo_url: str = "",
        extra_modifications: Optional[dict] = None,
    ) -> CreatomateResult:
        if not self.api_key:
            return CreatomateResult(success=False, error="CREATOMATE_API_KEY not set")
        if not template_id:
            return CreatomateResult(success=False, error="No Creatomate template ID provided")

        modifications = {
            "video_url": video_url,
            "caption_text": caption_text,
            "hook_text": hook_text,
            "cta_text": cta_text,
        }
        if logo_url:
            modifications["logo_url"] = logo_url
        if extra_modifications:
            modifications.update(extra_modifications)

        payload = {
            "template_id": template_id,
            "modifications": modifications,
            "output_format": "mp4",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(f"{BASE}/renders", headers=self._headers(), json=payload)
        except httpx.RequestError as exc:
            return CreatomateResult(success=False, error=f"Network error: {exc}")

        if res.status_code not in (200, 201):
            log.error("creatomate_render_failed", status=res.status_code, body=res.text[:300])
            return CreatomateResult(success=False, error=f"Creatomate API error {res.status_code}: {res.text[:200]}")

        data = res.json()
        # Creatomate returns a list
        renders = data if isinstance(data, list) else [data]
        if not renders:
            return CreatomateResult(success=False, error="Empty response from Creatomate")

        render = renders[0]
        return CreatomateResult(
            success=True,
            render_id=render.get("id"),
            status=render.get("status", "queued"),
            output_url=render.get("url"),
        )

    async def poll_status(self, render_id: str) -> CreatomateResult:
        """Check render status once — do NOT loop here; caller should poll."""
        if not self.api_key:
            return CreatomateResult(success=False, error="CREATOMATE_API_KEY not set")

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                res = await client.get(f"{BASE}/renders/{render_id}", headers=self._headers())
        except httpx.RequestError as exc:
            return CreatomateResult(success=False, error=f"Network error: {exc}")

        if res.status_code != 200:
            return CreatomateResult(success=False, error=f"Poll error {res.status_code}")

        render = res.json()
        status = render.get("status", "queued")
        return CreatomateResult(
            success=(status == "succeeded"),
            render_id=render_id,
            status=status,
            output_url=render.get("url") if status == "succeeded" else None,
            error=render.get("error_message") if status == "failed" else None,
        )

    async def render_and_wait(
        self,
        template_id: str,
        video_url: str,
        caption_text: str = "",
        hook_text: str = "",
        cta_text: str = "",
        logo_url: str = "",
    ) -> CreatomateResult:
        """Submit render and block until succeeded or failed (max ~6 min)."""
        result = await self.render(template_id, video_url, caption_text, hook_text, cta_text, logo_url)
        if not result.success or not result.render_id:
            return result

        for _ in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL)
            result = await self.poll_status(result.render_id)
            if result.status in ("succeeded", "failed"):
                return result
            log.info("creatomate_polling", render_id=result.render_id, status=result.status)

        return CreatomateResult(
            success=False,
            render_id=result.render_id,
            status="timeout",
            error=f"Render did not complete within {MAX_POLL_ATTEMPTS * POLL_INTERVAL}s",
        )
