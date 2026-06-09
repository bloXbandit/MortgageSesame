"""
TikTok Content Posting API v2.

Flow (PULL_FROM_URL — video must be at a public HTTPS URL):
  POST /v2/post/publish/video/init/  → returns publish_id
  TikTok pulls the video from your URL and processes it.
  Poll POST /v2/post/publish/status/fetch/ with publish_id

Requirements:
  TIKTOK_ACCESS_TOKEN  — OAuth 2.0 access token (scope: video.publish)
  TIKTOK_OPEN_ID       — user's open_id from OAuth flow
  BACKEND_URL          — must be publicly accessible

OAuth setup:
  Register your app at https://developers.tiktok.com/
  Scope needed: video.publish
  After OAuth, you get access_token + open_id
  Access tokens expire in 24h — use refresh_token to renew

TikTok Content Posting API: https://developers.tiktok.com/doc/content-posting-api-get-started
"""

import asyncio
import os
import httpx
import structlog
from app.services.publishers.base import PlatformPublisher, PublishPayload, PublishResult

log = structlog.get_logger()

TIKTOK_BASE = "https://open.tiktokapis.com/v2"


class TikTokPublisher(PlatformPublisher):

    def __init__(self):
        self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN", "")
        self.open_id      = os.getenv("TIKTOK_OPEN_ID", "")

    def _headers(self) -> dict:
        return {
            "Authorization":  f"Bearer {self.access_token}",
            "Content-Type":   "application/json; charset=UTF-8",
        }

    async def publish(self, payload: PublishPayload) -> PublishResult:
        if not self.access_token:
            return PublishResult(success=False, error="TIKTOK_ACCESS_TOKEN not set")

        caption = payload.caption or ""
        if payload.hashtags:
            caption += " " + " ".join(f"#{h.strip('#')}" for h in payload.hashtags)

        body = {
            "post_info": {
                "title":                    caption[:2200],
                "privacy_level":            "PUBLIC_TO_EVERYONE",
                "disable_duet":             False,
                "disable_stitch":           False,
                "disable_comment":          False,
                "video_cover_timestamp_ms": 1000,   # thumbnail at 1s mark
            },
            "source_info": {
                "source":    "PULL_FROM_URL",
                "video_url": payload.video_url,
            },
        }

        log.info("tiktok.init", video_url=payload.video_url[:60])
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{TIKTOK_BASE}/post/publish/video/init/",
                headers=self._headers(),
                json=body,
            )

        if resp.status_code != 200:
            return PublishResult(
                success=False,
                error=f"TikTok init {resp.status_code}: {resp.text[:300]}",
            )

        resp_data = resp.json()
        err = resp_data.get("error", {})
        if err.get("code", "ok") != "ok":
            return PublishResult(
                success=False,
                error=f"TikTok error: {err.get('message', 'unknown')} ({err.get('code')})",
            )

        publish_id = resp_data.get("data", {}).get("publish_id")
        log.info("tiktok.submitted", publish_id=publish_id)

        return PublishResult(
            success=True,
            external_post_id=publish_id,
            status="processing",
            raw_response=resp_data,
        )

    async def get_status(self, publish_id: str) -> dict:
        """Poll publish status. Status: PROCESSING_DOWNLOAD | PROCESSING_UPLOAD | PUBLISH_COMPLETE | FAILED"""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{TIKTOK_BASE}/post/publish/status/fetch/",
                headers=self._headers(),
                json={"publish_id": publish_id},
            )
        if resp.status_code != 200:
            return {"status": "unknown", "error": resp.text}
        data = resp.json().get("data", {})
        return {
            "status":      data.get("status"),
            "publish_id":  publish_id,
            "post_id":     data.get("publicaly_available_post_id"),  # TikTok's typo in their API
        }
