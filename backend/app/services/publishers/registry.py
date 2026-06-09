"""
Publisher registry — returns the right publisher for a given platform.
"""

import structlog
from app.services.publishers.base import PlatformPublisher, PublishPayload, PublishResult

log = structlog.get_logger()


class MockPublisher(PlatformPublisher):
    """Used in dev/test — logs the payload, returns success without hitting any API."""

    async def publish(self, payload: PublishPayload) -> PublishResult:
        log.info(
            "mock_publisher.publish",
            platform=payload.platform,
            caption_preview=payload.caption[:60] if payload.caption else "",
            video_url=payload.video_url[:80],
        )
        return PublishResult(
            success=True,
            external_post_id=f"mock_{payload.platform}_{id(payload)}",
            platform_url="https://example.com/mock-post",
            status="published",
        )


def get_publisher(platform: str) -> PlatformPublisher:
    """
    Return the publisher for a platform.

    Platform strings (match ContentPlatform enum values):
      tiktok | instagram_reel | facebook | linkedin | google_business
    """
    import os
    mock_mode = os.getenv("CONTENT_PUBLISH_MODE", "mock").lower() == "mock"

    if mock_mode:
        return MockPublisher()

    if platform == "tiktok":
        from app.services.publishers.tiktok import TikTokPublisher
        return TikTokPublisher()

    elif platform in ("instagram_reel", "instagram"):
        from app.services.publishers.instagram import InstagramPublisher
        return InstagramPublisher()

    elif platform == "facebook":
        from app.services.publishers.tiktok_facebook import FacebookPublisher
        return FacebookPublisher()

    elif platform == "linkedin":
        from app.services.publishers.linkedin import LinkedInPublisher
        return LinkedInPublisher()

    else:
        log.warning("publisher.unknown_platform", platform=platform)
        return MockPublisher()
