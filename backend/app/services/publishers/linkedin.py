"""
LinkedIn video post publisher via LinkedIn Marketing API.

Flow:
  1. POST /rest/videos?action=initializeUpload  → uploadUrl + video URN
  2. PUT to uploadUrl (single chunk for videos <4GB)
  3. POST /rest/videos?action=finalizeUpload
  4. POST /rest/posts (with video URN) → creates the LinkedIn post

For video, LinkedIn requires a direct file upload (not a URL pull).
We download the video from video_url first, then upload to LinkedIn.

Requirements:
  LINKEDIN_ACCESS_TOKEN — OAuth 2.0 access token
  LINKEDIN_PERSON_ID    — your person URN ID (from /rest/me endpoint)

OAuth scopes needed: w_member_social, r_basicprofile

LinkedIn API reference: https://learn.microsoft.com/en-us/linkedin/marketing/
"""

import os
import httpx
import structlog
from app.services.publishers.base import PlatformPublisher, PublishPayload, PublishResult
from typing import Optional

log = structlog.get_logger()

LI_BASE = "https://api.linkedin.com"


class LinkedInPublisher(PlatformPublisher):

    def __init__(self):
        self.token     = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
        self.person_id = os.getenv("LINKEDIN_PERSON_ID", "")

    def _headers(self, extra: Optional[dict] = None) -> dict:
        h = {
            "Authorization":             f"Bearer {self.token}",
            "Content-Type":              "application/json",
            "LinkedIn-Version":          "202401",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        if extra:
            h.update(extra)
        return h

    async def publish(self, payload: PublishPayload) -> PublishResult:
        if not self.token or not self.person_id:
            return PublishResult(
                success=False,
                error="LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_ID required",
            )

        # ── Step 1: Download video bytes ───────────────────────────────────────
        log.info("linkedin.download_video", url=payload.video_url[:60])
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            video_resp = await client.get(payload.video_url)
        if video_resp.status_code != 200:
            return PublishResult(
                success=False,
                error=f"Failed to download video: {video_resp.status_code}",
            )
        video_bytes = video_resp.content
        file_size   = len(video_bytes)

        person_urn = f"urn:li:person:{self.person_id}"

        # ── Step 2: Initialize upload ──────────────────────────────────────────
        init_body = {
            "initializeUploadRequest": {
                "owner":         person_urn,
                "fileSizeBytes": file_size,
                "uploadCaptions": False,
                "uploadThumbnail": False,
            }
        }
        async with httpx.AsyncClient(timeout=30) as client:
            init_resp = await client.post(
                f"{LI_BASE}/rest/videos?action=initializeUpload",
                headers=self._headers(),
                json=init_body,
            )
        if init_resp.status_code not in (200, 201):
            return PublishResult(
                success=False,
                error=f"LinkedIn initializeUpload failed ({init_resp.status_code}): {init_resp.text[:300]}",
            )

        init_data    = init_resp.json().get("value", {})
        upload_url   = init_data.get("uploadInstructions", [{}])[0].get("uploadUrl")
        video_urn    = init_data.get("video")
        upload_token = init_data.get("uploadToken")

        if not upload_url or not video_urn:
            return PublishResult(
                success=False,
                error=f"Missing upload details from LinkedIn: {init_data}",
            )

        # ── Step 3: Upload video bytes ─────────────────────────────────────────
        log.info("linkedin.upload", video_urn=video_urn, size_mb=round(file_size / 1024 / 1024, 1))
        async with httpx.AsyncClient(timeout=180) as client:
            upload_resp = await client.put(
                upload_url,
                content=video_bytes,
                headers={"Content-Type": "application/octet-stream"},
            )
        # LinkedIn expects 2xx on upload
        etag = upload_resp.headers.get("etag", "")

        # ── Step 4: Finalize upload ────────────────────────────────────────────
        finalize_body = {
            "finalizeUploadRequest": {
                "video":          video_urn,
                "uploadToken":    upload_token,
                "uploadedPartIds": [etag] if etag else [],
            }
        }
        async with httpx.AsyncClient(timeout=30) as client:
            fin_resp = await client.post(
                f"{LI_BASE}/rest/videos?action=finalizeUpload",
                headers=self._headers(),
                json=finalize_body,
            )
        if fin_resp.status_code not in (200, 201, 204):
            return PublishResult(
                success=False,
                error=f"LinkedIn finalizeUpload failed ({fin_resp.status_code}): {fin_resp.text[:200]}",
            )

        # ── Step 5: Create post ────────────────────────────────────────────────
        caption = payload.caption or ""
        if payload.hashtags:
            caption += "\n" + " ".join(f"#{h.strip('#')}" for h in payload.hashtags)

        post_body = {
            "author":        person_urn,
            "commentary":    caption[:3000],
            "visibility":    "PUBLIC",
            "distribution":  {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "content": {
                "media": {"id": video_urn}
            },
            "lifecycleState":          "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            post_resp = await client.post(
                f"{LI_BASE}/rest/posts",
                headers=self._headers(),
                json=post_body,
            )

        if post_resp.status_code not in (200, 201):
            return PublishResult(
                success=False,
                error=f"LinkedIn post creation failed ({post_resp.status_code}): {post_resp.text[:300]}",
            )

        post_urn = post_resp.headers.get("x-linkedin-id") or post_resp.json().get("id", "")
        log.info("linkedin.published", post_urn=post_urn)
        return PublishResult(
            success=True,
            external_post_id=post_urn,
            platform_url=f"https://www.linkedin.com/feed/update/{post_urn}/",
        )
