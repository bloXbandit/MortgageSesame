"""
Platform publisher base class.

All publishers implement publish(payload) → PublishResult.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PublishPayload:
    video_url: str            # Publicly accessible URL of the final video
    caption: str              # Post caption / text
    platform: str             # tiktok | instagram_reel | facebook | linkedin
    title: Optional[str] = None
    hashtags: Optional[list] = None
    post_id: Optional[str] = None   # Internal SocialPost.id for logging


@dataclass
class PublishResult:
    success: bool
    external_post_id: Optional[str] = None     # Platform's ID (Instagram media_id, TikTok publish_id)
    platform_url: Optional[str] = None         # URL to the published post (if available)
    status: str = "published"                  # published | processing | failed
    error: Optional[str] = None
    raw_response: Optional[dict] = None


class PlatformPublisher:
    """Abstract base — one per platform."""

    async def publish(self, payload: PublishPayload) -> PublishResult:
        raise NotImplementedError

    async def get_status(self, external_id: str) -> dict:
        """Check post status after publishing (for async platforms like TikTok)."""
        return {"status": "unknown"}
