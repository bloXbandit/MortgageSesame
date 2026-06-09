"""
Instagram Reels publisher via Meta Graph API.

Flow:
  1. POST /{ig_user_id}/media     → create container, returns creation_id
  2. Poll until status_code=FINISHED (video processing takes 1-5 min)
  3. POST /{ig_user_id}/media_publish → publish, returns media_id

Requirements:
  META_ACCESS_TOKEN  — long-lived user token (60-day, auto-refreshable)
  META_IG_USER_ID    — Instagram Business Account numeric ID
  BACKEND_URL        — must be publicly accessible (video is pulled from this URL)

Meta Graph API v19.0: https://developers.facebook.com/docs/instagram-api/guides/reels
"""

import asyncio
import os
import httpx
import structlog
from app.services.publishers.base import PlatformPublisher, PublishPayload, PublishResult

log = structlog.get_logger()

GRAPH = "https://graph.facebook.com/v19.0"
MAX_POLL_ATTEMPTS = 36    # 36 × 10s = 6 minutes max for video processing


class InstagramPublisher(PlatformPublisher):

    def __init__(self):
        self.token      = os.getenv("META_ACCESS_TOKEN", "")
        self.ig_user_id = os.getenv("META_IG_USER_ID", "")

    async def publish(self, payload: PublishPayload) -> PublishResult:
        if not self.token or not self.ig_user_id:
            return PublishResult(
                success=False,
                error="META_ACCESS_TOKEN and META_IG_USER_ID required",
            )

        caption = payload.caption or ""
        if payload.hashtags:
            caption += "\n\n" + " ".join(f"#{h.strip('#')}" for h in payload.hashtags)

        # ── Step 1: Create media container ────────────────────────────────────
        log.info("instagram.create_container", ig_user_id=self.ig_user_id)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GRAPH}/{self.ig_user_id}/media",
                params={
                    "access_token":  self.token,
                    "media_type":    "REELS",
                    "video_url":     payload.video_url,
                    "caption":       caption[:2200],   # IG caption limit
                    "share_to_feed": "true",
                },
            )

        if resp.status_code != 200:
            return PublishResult(
                success=False,
                error=f"Container creation failed ({resp.status_code}): {resp.text[:300]}",
            )

        creation_id = resp.json().get("id")
        if not creation_id:
            return PublishResult(success=False, error="No creation_id in Meta response")

        log.info("instagram.container_created", creation_id=creation_id)

        # ── Step 2: Poll until Instagram finishes processing ──────────────────
        for attempt in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(10)
            async with httpx.AsyncClient(timeout=15) as client:
                status_resp = await client.get(
                    f"{GRAPH}/{creation_id}",
                    params={
                        "fields":       "status_code",
                        "access_token": self.token,
                    },
                )
            status_code = status_resp.json().get("status_code", "IN_PROGRESS")
            log.info("instagram.poll", attempt=attempt, status=status_code)

            if status_code == "FINISHED":
                break
            elif status_code == "ERROR":
                err = status_resp.json().get("status", {})
                return PublishResult(
                    success=False,
                    error=f"Instagram media processing error: {err}",
                )
        else:
            return PublishResult(
                success=False,
                error="Instagram video processing timed out (>6 min)",
            )

        # ── Step 3: Publish ───────────────────────────────────────────────────
        async with httpx.AsyncClient(timeout=30) as client:
            pub_resp = await client.post(
                f"{GRAPH}/{self.ig_user_id}/media_publish",
                params={
                    "access_token": self.token,
                    "creation_id":  creation_id,
                },
            )

        if pub_resp.status_code != 200:
            return PublishResult(
                success=False,
                error=f"Publish step failed ({pub_resp.status_code}): {pub_resp.text[:300]}",
            )

        media_id = pub_resp.json().get("id")
        log.info("instagram.published", media_id=media_id)
        return PublishResult(
            success=True,
            external_post_id=media_id,
            platform_url=f"https://www.instagram.com/reel/{media_id}/",
            raw_response=pub_resp.json(),
        )
