"""
Facebook Reels / video post publisher via Meta Graph API.

Uses the same Meta Graph API as Instagram but targets a Page instead of
an IG User account.

Requirements:
  META_ACCESS_TOKEN  — Page access token
  META_PAGE_ID       — Facebook Page numeric ID
"""

import asyncio
import os
import httpx
import structlog
from app.services.publishers.base import PlatformPublisher, PublishPayload, PublishResult

log = structlog.get_logger()

GRAPH = "https://graph.facebook.com/v19.0"


class FacebookPublisher(PlatformPublisher):

    def __init__(self):
        self.token   = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
        self.page_id = os.getenv("FACEBOOK_PAGE_ID", "")

    async def publish(self, payload: PublishPayload) -> PublishResult:
        if not self.token or not self.page_id:
            return PublishResult(
                success=False,
                error="FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_PAGE_ID required for Facebook posting",
            )

        caption = payload.caption or ""
        if payload.hashtags:
            caption += "\n\n" + " ".join(f"#{h.strip('#')}" for h in payload.hashtags)

        # Facebook Reels: POST /{page_id}/video_reels
        log.info("facebook.upload_reel", page_id=self.page_id)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GRAPH}/{self.page_id}/video_reels",
                params={
                    "upload_phase":  "finish",
                    "access_token":  self.token,
                    "video_url":     payload.video_url,
                    "description":   caption[:63206],   # FB description limit
                    "published":     "true",
                },
            )

        if resp.status_code not in (200, 201):
            # Fallback: try standard page video post
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{GRAPH}/{self.page_id}/videos",
                    params={
                        "access_token": self.token,
                        "file_url":     payload.video_url,
                        "description":  caption[:63206],
                        "published":    "true",
                    },
                )

        if resp.status_code not in (200, 201):
            return PublishResult(
                success=False,
                error=f"Facebook post failed ({resp.status_code}): {resp.text[:300]}",
            )

        data = resp.json()
        video_id = data.get("id") or data.get("video_id")
        log.info("facebook.published", video_id=video_id)
        return PublishResult(
            success=True,
            external_post_id=video_id,
            raw_response=data,
        )
