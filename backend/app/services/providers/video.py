"""
Video generation provider adapters.

Same pattern as EmailProvider — select via env var:
  CAMPAIGN_VIDEO_PROVIDER=mock       # dev default, no API key needed
  CAMPAIGN_VIDEO_PROVIDER=heygen     # production: real AI avatar video

HeyGen API v2 docs: https://docs.heygen.com/reference/generate-video-v2
"""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Optional
import httpx
import structlog

log = structlog.get_logger()


@dataclass
class VideoResult:
    success: bool
    provider_id: Optional[str] = None        # HeyGen video_id
    status: str = "processing"               # processing | completed | failed
    video_url: Optional[str] = None          # CDN URL of rendered video
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    raw_response: Optional[dict] = None


class VideoProvider:
    """Abstract base — all providers implement this interface."""

    async def generate_video(self, payload: dict) -> VideoResult:
        raise NotImplementedError

    async def poll_status(self, provider_id: str) -> VideoResult:
        raise NotImplementedError

    async def wait_for_completion(
        self, provider_id: str, timeout_seconds: int = 300, poll_interval: int = 10
    ) -> VideoResult:
        """Poll until complete or timeout."""
        elapsed = 0
        while elapsed < timeout_seconds:
            result = await self.poll_status(provider_id)
            if result.status in ("completed", "failed"):
                return result
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        return VideoResult(
            success=False,
            provider_id=provider_id,
            status="timeout",
            error=f"Video generation timed out after {timeout_seconds}s",
        )


# ── Mock provider ──────────────────────────────────────────────────────────────

class MockVideoProvider(VideoProvider):
    """
    Dev/test provider — returns fake data immediately.
    No API key needed. Use test_mode in HeyGen for real watermarked renders.
    """

    async def generate_video(self, payload: dict) -> VideoResult:
        log.info("mock_video.generate", script_len=len(payload.get("script", "")))
        fake_id = f"mock_{os.urandom(4).hex()}"
        return VideoResult(
            success=True,
            provider_id=fake_id,
            status="completed",
            video_url=f"https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            thumbnail_url="https://picsum.photos/seed/mortgage/1080/1920",
            duration_seconds=15.0,
        )

    async def poll_status(self, provider_id: str) -> VideoResult:
        return VideoResult(success=True, provider_id=provider_id, status="completed")


# ── HeyGen provider ────────────────────────────────────────────────────────────

class HeyGenProvider(VideoProvider):
    """
    HeyGen AI avatar video generation.
    Record yourself once → avatar does every future video.
    API: https://docs.heygen.com/reference/generate-video-v2
    """

    BASE = "https://api.heygen.com"

    def __init__(self):
        self.api_key         = os.getenv("HEYGEN_API_KEY", "")
        self.default_avatar  = os.getenv("HEYGEN_AVATAR_ID", "")
        self.default_voice   = os.getenv("HEYGEN_VOICE_ID", "")   # optional: HeyGen built-in voice
        self.test_mode       = os.getenv("HEYGEN_TEST_MODE", "true").lower() == "true"

    async def generate_video(self, payload: dict) -> VideoResult:
        if not self.api_key:
            return VideoResult(success=False, error="HEYGEN_API_KEY not set")

        avatar_id = payload.get("avatar_id") or self.default_avatar
        if not avatar_id:
            return VideoResult(success=False, error="HEYGEN_AVATAR_ID not set — cannot generate video")

        aspect_ratio = payload.get("aspect_ratio", "9:16")
        script       = payload.get("script", "")
        test         = payload.get("test_mode", self.test_mode)

        # Build voice block — prefer ElevenLabs clone if el_voice_id provided
        el_voice_id = payload.get("elevenlabs_voice_id") or os.getenv("HEYGEN_ELEVENLABS_VOICE_ID", "")
        if el_voice_id:
            voice_block = {
                "type": "elevenlabs",
                "voice_id": el_voice_id,
                "speed": payload.get("speed", 1.0),
            }
        elif self.default_voice:
            voice_block = {
                "type": "text",
                "input_text": script,
                "voice_id": self.default_voice,
                "speed": payload.get("speed", 1.0),
            }
        else:
            return VideoResult(success=False, error="No voice configured. Set HEYGEN_VOICE_ID or HEYGEN_ELEVENLABS_VOICE_ID.")

        body = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal",
                    },
                    "voice": voice_block,
                    "background": {
                        "type": "color",
                        "value": "#fffbf5",  # Buttermilk — matches brand
                    },
                }
            ],
            "aspect_ratio": aspect_ratio,
            "test": test,       # True = watermarked, free; False = production
            "caption": payload.get("add_captions", True),
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.BASE}/v2/video/generate",
                    headers={
                        "X-Api-Key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
        except httpx.HTTPError as e:
            return VideoResult(success=False, error=f"HeyGen request failed: {e}")

        if resp.status_code != 200:
            return VideoResult(
                success=False,
                error=f"HeyGen {resp.status_code}: {resp.text[:300]}",
            )

        data = resp.json()
        video_id = data.get("data", {}).get("video_id")
        if not video_id:
            return VideoResult(success=False, error=f"HeyGen response missing video_id: {data}")

        log.info("heygen.submitted", video_id=video_id, test_mode=test)
        return VideoResult(
            success=True,
            provider_id=video_id,
            status="processing",
            raw_response=data,
        )

    async def poll_status(self, provider_id: str) -> VideoResult:
        """Check render status. Poll every ~10s after submitting."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.BASE}/v1/video_status.get",
                    headers={"X-Api-Key": self.api_key},
                    params={"video_id": provider_id},
                )
        except httpx.HTTPError as e:
            return VideoResult(success=False, provider_id=provider_id, error=str(e))

        if resp.status_code != 200:
            return VideoResult(
                success=False, provider_id=provider_id,
                error=f"Status check {resp.status_code}: {resp.text[:200]}",
            )

        data = resp.json().get("data", {})
        status = data.get("status", "processing")   # processing | completed | failed | waiting

        if status == "completed":
            return VideoResult(
                success=True,
                provider_id=provider_id,
                status="completed",
                video_url=data.get("video_url"),
                thumbnail_url=data.get("thumbnail_url"),
                duration_seconds=data.get("duration"),
            )
        elif status == "failed":
            return VideoResult(
                success=False,
                provider_id=provider_id,
                status="failed",
                error=data.get("error", "HeyGen generation failed"),
            )
        else:
            return VideoResult(success=True, provider_id=provider_id, status="processing")


# ── Registry ───────────────────────────────────────────────────────────────────

_PROVIDER: Optional[VideoProvider] = None

def get_video_provider() -> VideoProvider:
    global _PROVIDER
    if _PROVIDER is None:
        name = os.getenv("CAMPAIGN_VIDEO_PROVIDER", "mock").lower()
        if name == "heygen":
            _PROVIDER = HeyGenProvider()
        else:
            _PROVIDER = MockVideoProvider()
        log.info("video_provider.initialized", provider=name)
    return _PROVIDER
