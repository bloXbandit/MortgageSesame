"""
Content agent intelligence.

The "brain" that watches what's working and makes decisions:
  - Analyze content performance (approval rates, publish rates, category health)
  - Run the full pipeline (voice → video → queue)
  - Flag underperforming categories for pause/adjustment
  - Track estimated video generation costs

This is called by the agent API endpoints and runs autonomously during
scheduled content runs.
"""

import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import SocialPost, MediaAsset, ContentPlatform, ApprovalStatus

log = structlog.get_logger()

from app.config import settings as _s
BOOKING_URL = _s.calcom_link

# Cost estimates — overridable via env
COST_HEYGEN_PER_MIN   = float(os.getenv("COST_HEYGEN_PER_MIN",   "0.10"))
COST_CREATOMATE       = float(os.getenv("COST_CREATOMATE_RENDER", "0.05"))


# ── Performance analysis ───────────────────────────────────────────────────────

async def analyze_content_performance(db: AsyncSession, days: int = 30) -> dict:
    """
    Analyze content pipeline health and return structured decisions.

    Decision types:
      pause   — stop generating this category/platform, it's not working
      adjust  — keep generating but change approach (angle/tone)
      scale   — this category works well, generate more
      review  — content is approved but not publishing fast enough
      alert   — something unusual
    """
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(SocialPost).where(SocialPost.created_at >= since)
    )
    posts = result.scalars().all()

    if not posts:
        return {
            "status": "no_data",
            "period_days": days,
            "total_generated": 0,
            "recommendation": "No content generated in this period. Start by running POST /agent/generate-content.",
            "decisions": [],
            "by_category": {},
            "by_platform": {},
            "cost_estimate": 0.0,
        }

    # ── Group by category and platform ────────────────────────────────────────
    by_cat: dict[str, list] = defaultdict(list)
    by_plat: dict[str, list] = defaultdict(list)
    for p in posts:
        cat_key  = p.category.value  if p.category  else "uncategorized"
        plat_key = p.platform.value  if p.platform  else "unknown"
        by_cat[cat_key].append(p)
        by_plat[plat_key].append(p)

    APPROVED_STATUSES = {ApprovalStatus.APPROVED, ApprovalStatus.SCHEDULED, ApprovalStatus.PUBLISHED}

    def _stats(post_list):
        total     = len(post_list)
        approved  = sum(1 for p in post_list if p.approval_status in APPROVED_STATUSES)
        rejected  = sum(1 for p in post_list if p.approval_status == ApprovalStatus.REJECTED)
        published = sum(1 for p in post_list if p.approval_status == ApprovalStatus.PUBLISHED)
        pending   = sum(1 for p in post_list if p.approval_status == ApprovalStatus.PENDING)
        return {
            "total": total, "approved": approved, "rejected": rejected,
            "published": published, "pending": pending,
            "approval_rate": round(approved / total, 2) if total else 0,
            "publish_rate":  round(published / total, 2) if total else 0,
        }

    # ── Build decisions ────────────────────────────────────────────────────────
    decisions = []

    for cat, cps in by_cat.items():
        s = _stats(cps)
        if s["total"] < 2:
            continue  # Not enough data

        if s["approval_rate"] < 0.35:
            decisions.append({
                "type":     "pause",
                "target":   f"category:{cat}",
                "category": cat,
                "reason":   (
                    f"'{cat}' has only {s['approval_rate']:.0%} approval rate "
                    f"over {s['total']} attempts in {days} days. "
                    "Consider revising the style guide template or pausing this category."
                ),
                "action":   "pause_category",
                "severity": "high",
            })
        elif s["approval_rate"] < 0.5:
            decisions.append({
                "type":     "adjust",
                "target":   f"category:{cat}",
                "category": cat,
                "reason":   (
                    f"'{cat}' approval rate is {s['approval_rate']:.0%} — below 50%. "
                    "Try editing the style_guide or hook template for this category."
                ),
                "action":   "edit_template",
                "severity": "medium",
            })
        elif s["approval_rate"] >= 0.75 and s["publish_rate"] < 0.3:
            decisions.append({
                "type":     "review",
                "target":   f"category:{cat}",
                "category": cat,
                "reason":   (
                    f"'{cat}' has a strong approval rate ({s['approval_rate']:.0%}) "
                    f"but only {s['publish_rate']:.0%} publish rate — content is piling up. "
                    "Review the pending queue and approve for publishing."
                ),
                "action":   "clear_queue",
                "severity": "low",
            })
        elif s["approval_rate"] >= 0.75 and s["total"] <= 3:
            decisions.append({
                "type":     "scale",
                "target":   f"category:{cat}",
                "category": cat,
                "reason":   (
                    f"'{cat}' is performing well ({s['approval_rate']:.0%} approval). "
                    "Generate more content in this category."
                ),
                "action":   "increase_frequency",
                "severity": "info",
            })

    # ── Platform analysis ──────────────────────────────────────────────────────
    for plat, pps in by_plat.items():
        s = _stats(pps)
        if s["total"] >= 3 and s["approval_rate"] < 0.3:
            decisions.append({
                "type":     "pause",
                "target":   f"platform:{plat}",
                "platform": plat,
                "reason":   (
                    f"Platform '{plat}' has only {s['approval_rate']:.0%} approval rate. "
                    "Consider pausing this platform or adjusting platform-specific templates."
                ),
                "action":   "pause_platform",
                "severity": "high",
            })

    # ── Cost estimate ──────────────────────────────────────────────────────────
    video_platforms = {ContentPlatform.TIKTOK, ContentPlatform.INSTAGRAM_REEL}
    video_posts = [
        p for p in posts
        if p.platform in video_platforms and p.approval_status == ApprovalStatus.PUBLISHED
    ]
    # Assume avg 60s video at COST_HEYGEN_PER_MIN + assembly
    cost_estimate = len(video_posts) * (COST_HEYGEN_PER_MIN + COST_CREATOMATE)

    # ── Overall health ─────────────────────────────────────────────────────────
    total_all = len(posts)
    approved_all = sum(1 for p in posts if p.approval_status in APPROVED_STATUSES)
    overall_rate = round(approved_all / total_all, 2) if total_all else 0

    pauses  = [d for d in decisions if d["type"] == "pause"]
    scalers = [d for d in decisions if d["type"] == "scale"]

    if overall_rate >= 0.7 and not pauses:
        recommendation = "Pipeline is healthy. Content is being approved and published consistently."
    elif len(pauses) >= 2:
        recommendation = (
            "Multiple categories underperforming. Review your style_guide templates "
            "and ensure compliance language is current. Consider a fresh batch on different categories."
        )
    elif overall_rate < 0.4:
        recommendation = (
            "Low overall approval rate. Check compliance flags, review recent rejections, "
            "and update tone/style guide templates before generating more."
        )
    else:
        recommendation = "Some categories need attention — see decisions below."

    best_cat = max(
        by_cat.items(),
        key=lambda x: _stats(x[1])["approval_rate"] * _stats(x[1])["total"],
        default=(None, []),
    )[0]

    return {
        "status":           "analyzed",
        "period_days":      days,
        "total_generated":  total_all,
        "overall_approval_rate": overall_rate,
        "cost_estimate_usd": round(cost_estimate, 2),
        "video_posts_published": len(video_posts),
        "recommendation":   recommendation,
        "best_performing_category": best_cat,
        "decisions":        sorted(decisions, key=lambda d: {"high": 0, "medium": 1, "low": 2, "info": 3}[d["severity"]]),
        "by_category":      {cat: _stats(cps) for cat, cps in by_cat.items()},
        "by_platform":      {plat: _stats(pps) for plat, pps in by_plat.items()},
        "cost_assumptions": {
            "heygen_per_min":   COST_HEYGEN_PER_MIN,
            "creatomate_render": COST_CREATOMATE,
        },
    }


# ── Content pipeline orchestration ────────────────────────────────────────────

async def run_content_pipeline(
    db: AsyncSession,
    post_id: str,
    generate_voice: bool = True,
    generate_video: bool = False,   # off by default until HEYGEN_API_KEY is set
    auto_queue: bool = True,
) -> dict:
    """
    Orchestrate: existing approved/pending SocialPost → voice → video → approval queue.

    Called by:
      - Agent via POST /agent/content-pipeline
      - Manually via POST /content/posts/{id}/pipeline
    """
    from app.services.integrations.elevenlabs import generate_audio
    from app.services.providers.video import get_video_provider

    result = await db.execute(select(SocialPost).where(SocialPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        return {"error": "Post not found", "post_id": post_id}

    steps: list[dict] = []
    media_ids: list[dict] = list(post.media_asset_ids or [])
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    # ── Voice generation ───────────────────────────────────────────────────────
    if generate_voice and post.voiceover_script:
        # Skip if already have audio
        has_audio = any(m.get("type") == "audio" for m in media_ids)
        if not has_audio:
            try:
                audio_bytes = await generate_audio(post.voiceover_script)

                # Save to disk
                media_dir = os.getenv("MEDIA_STORAGE_PATH", "./media")
                os.makedirs(media_dir, exist_ok=True)

                asset = MediaAsset(
                    name=f"voice_{post.id[:8]}.mp3",
                    asset_type="audio",
                    mime_type="audio/mpeg",
                    file_size=len(audio_bytes),
                    tags=["voiceover", "elevenlabs", post.platform.value if post.platform else ""],
                )
                db.add(asset)
                await db.flush()

                file_path = f"{media_dir}/{asset.id}.mp3"
                with open(file_path, "wb") as f:
                    f.write(audio_bytes)

                asset.file_path = file_path
                asset.file_url  = f"{backend_url}/media/{asset.id}.mp3"
                await db.flush()

                media_ids.append({"id": asset.id, "type": "audio", "url": asset.file_url})
                post.media_asset_ids = list(media_ids)
                post.pipeline_stage = "voice_ready"
                await db.commit()

                steps.append({"step": "voice", "status": "done", "asset_id": asset.id, "url": asset.file_url})
                log.info("pipeline.voice_done", post_id=post_id, asset_id=asset.id)

            except Exception as exc:
                steps.append({"step": "voice", "status": "failed", "error": str(exc)})
                log.error("pipeline.voice_failed", post_id=post_id, error=str(exc))
        else:
            steps.append({"step": "voice", "status": "skipped", "reason": "audio already exists"})

    # ── Video generation ───────────────────────────────────────────────────────
    if generate_video and post.voiceover_script:
        has_video = any(m.get("type") in ("video_raw", "video_final") for m in media_ids)
        if not has_video:
            try:
                provider = get_video_provider()
                aspect   = "9:16" if post.platform and post.platform.value in ("tiktok", "instagram_reel") else "16:9"

                vr = await provider.generate_video({
                    "script":       post.voiceover_script,
                    "aspect_ratio": aspect,
                    "test_mode":    os.getenv("HEYGEN_TEST_MODE", "true").lower() == "true",
                })

                asset = MediaAsset(
                    name=f"video_raw_{post.id[:8]}",
                    asset_type="video_raw",
                    mime_type="video/mp4",
                    tags=["heygen", post.platform.value if post.platform else ""],
                )
                db.add(asset)
                await db.flush()

                if vr.video_url:
                    asset.file_url = vr.video_url

                # Store provider_id in tags for polling
                if vr.provider_id:
                    asset.tags = list(asset.tags or []) + [f"provider_id:{vr.provider_id}"]

                media_ids.append({
                    "id":          asset.id,
                    "type":        "video_raw",
                    "url":         vr.video_url or "",
                    "provider_id": vr.provider_id,
                    "status":      vr.status,
                })
                post.media_asset_ids = list(media_ids)
                post.pipeline_stage  = "video_processing" if vr.status == "processing" else "video_ready"
                await db.commit()

                steps.append({
                    "step":        "video",
                    "status":      vr.status,
                    "asset_id":    asset.id,
                    "provider_id": vr.provider_id,
                    "error":       vr.error,
                })
                log.info("pipeline.video_submitted", post_id=post_id, provider_id=vr.provider_id)

            except Exception as exc:
                steps.append({"step": "video", "status": "failed", "error": str(exc)})
                log.error("pipeline.video_failed", post_id=post_id, error=str(exc))
        else:
            steps.append({"step": "video", "status": "skipped", "reason": "video already exists"})

    # ── Auto-queue for human approval ──────────────────────────────────────────
    if auto_queue:
        try:
            from app.models.agent import ApprovalQueue, ApprovalItemType
            preview = (post.hook or post.script or "")[:200]
            plat    = post.platform.value if post.platform else "content"
            cat     = post.category.value if post.category else ""
            stage   = post.pipeline_stage or "generated"

            item = ApprovalQueue(
                item_type=ApprovalItemType.SOCIAL_POST,
                item_id=post.id,
                title=f"{plat} — {cat} — {stage}",
                preview=preview,
                created_by="agent",
            )
            db.add(item)
            await db.commit()
            steps.append({"step": "queue", "status": "done"})
        except Exception as exc:
            steps.append({"step": "queue", "status": "failed", "error": str(exc)})

    return {
        "post_id":      post_id,
        "platform":     post.platform.value if post.platform else None,
        "pipeline_stage": post.pipeline_stage,
        "steps":        steps,
        "media_assets": media_ids,
    }
