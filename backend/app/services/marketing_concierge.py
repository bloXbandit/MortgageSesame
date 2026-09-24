"""
Marketing Concierge — conversational campaign builder.

POST /agent/chat → chat() here.

Flow: discover → propose → refine → confirm → build.
State persists in AgentChatSession so the conversation survives across turns.
When the operator confirms, the concierge calls build_ad_campaign directly
(same skill chain as /agent/build-campaign) — everything still routes to the
Approval Queue. Nothing goes live automatically.
"""

import os
import uuid
from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings as _s
from app.services import ai_service

log = structlog.get_logger()

SKILL_DIR = os.path.join(os.path.dirname(__file__), "..", "agents", "skills", "advertising")

HISTORY_CAP = 20


def _load_concierge_skill() -> str:
    path = os.path.join(SKILL_DIR, "13_marketing-concierge.md")
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        log.warning("concierge.skill_missing", path=path)
        return ""


async def get_materials_snapshot(db: AsyncSession) -> dict:
    """Shared inventory used by GET /agent/materials and the concierge prompt."""
    from app.models.flyer import GeneratedFlyer, ReferencePhoto
    from app.models.content import MediaAsset
    from app.services.ad_campaign_builder import CAMPAIGN_TEMPLATES

    ref = (await db.execute(
        select(ReferencePhoto).order_by(ReferencePhoto.id).limit(1)
    )).scalar_one_or_none()

    flyers_q = await db.execute(
        select(GeneratedFlyer)
        .where(GeneratedFlyer.status == "complete")
        .order_by(GeneratedFlyer.id.desc())
        .limit(30)
    )
    flyers = [
        {
            "id":              f.id,
            "headline":        f.headline,
            "use_case":        f.use_case,
            "flyer_format":    f.flyer_format,
            "flyer_image_url": f.flyer_image_url,
        }
        for f in flyers_q.scalars().all()
    ]

    vids_q = await db.execute(
        select(MediaAsset)
        .where(MediaAsset.asset_type.in_(["video_raw", "video_final"]))
        .order_by(MediaAsset.created_at.desc())
        .limit(30)
    )
    videos = [
        {"id": a.id, "name": a.name, "asset_type": a.asset_type,
         "file_url": a.file_url, "tags": a.tags or []}
        for a in vids_q.scalars().all()
    ]

    audio_q = await db.execute(
        select(MediaAsset)
        .where(MediaAsset.asset_type == "audio")
        .order_by(MediaAsset.created_at.desc())
        .limit(30)
    )
    voice_assets = [
        {"id": a.id, "name": a.name, "file_url": a.file_url, "tags": a.tags or []}
        for a in audio_q.scalars().all()
    ]

    return {
        "reference_photo": {
            "uploaded": bool(ref and ref.file_url),
            "file_url": ref.file_url if ref else None,
        },
        "flyers":       flyers,
        "videos":       videos,
        "voice_assets": voice_assets,
        "templates": [
            {"id": t["id"], "name": t["name"], "avatar": t["avatar"],
             "product": t["product"], "budget_hint": t.get("budget_hint", "low")}
            for t in CAMPAIGN_TEMPLATES.values()
        ],
        "providers": {
            "video_provider":     _s.campaign_video_provider,
            "video_test_mode":    os.getenv("HEYGEN_TEST_MODE", "true").lower() == "true",
            "voice_available":    bool(_s.elevenlabs_api_key),
            "heygen_configured":  bool(os.getenv("HEYGEN_API_KEY")),
            "heygen_voice_clone": bool(os.getenv("HEYGEN_ELEVENLABS_VOICE_ID")),
        },
    }


async def chat(
    db: AsyncSession,
    message: str,
    session_id: Optional[str] = None,
) -> dict:
    """
    One turn of the marketing concierge conversation.

    Returns: { session_id, reply, action, state, missing, build_result? }
    """
    from app.models.agent_memory import AgentChatSession
    from app.services.ad_campaign_builder import build_ad_campaign, CAMPAIGN_TEMPLATES

    # ── Load or create session ────────────────────────────────────────────────
    session = None
    if session_id:
        session = (await db.execute(
            select(AgentChatSession).where(AgentChatSession.id == session_id)
        )).scalar_one_or_none()
    if not session:
        session = AgentChatSession(id=str(uuid.uuid4()), state={}, history=[], status="active")
        db.add(session)
        await db.flush()

    state   = dict(session.state or {})
    history = list(session.history or [])

    # ── Build prompt ──────────────────────────────────────────────────────────
    import json
    materials = await get_materials_snapshot(db)
    skill     = _load_concierge_skill()

    system = f"""You are the marketing concierge for {_s.banker_name or "a mortgage banker"} (NMLS #{_s.banker_nmls or "n/a"}).

=== SKILL 13: MARKETING CONCIERGE (your operating rules) ===
{skill}

=== CURRENT SESSION STATE ===
{json.dumps(state, indent=2)}

=== MATERIALS SNAPSHOT (what the operator already has) ===
{json.dumps(materials, indent=2)}

Respond with ONLY the JSON object specified in SKILL 13's OUTPUT FORMAT.
"""

    # Include short rolling history so the LLM has conversational context
    convo = ""
    if history:
        convo = "\n\n=== CONVERSATION SO FAR ===\n" + "\n".join(
            f"{'Operator' if h.get('role') == 'user' else 'Concierge'}: {h.get('text', '')[:400]}"
            for h in history[-10:]
        )

    user_prompt = f"Operator says: {message}{convo}"

    # ── LLM turn ──────────────────────────────────────────────────────────────
    try:
        result = await ai_service.complete_json(user_prompt, system=system, model=None)
    except Exception as exc:
        log.error("concierge.llm_failed", session_id=session.id, error=str(exc))
        return {"error": f"Concierge generation failed: {str(exc)}", "session_id": session.id}

    reply  = result.get("reply") or "I didn't catch that — can you rephrase?"
    action = result.get("action") or "continue"

    # ── Merge state ───────────────────────────────────────────────────────────
    updates = result.get("state_updates") or {}
    if isinstance(updates, dict):
        state.update(updates)

    missing = result.get("missing") or []
    if not isinstance(missing, list):
        missing = []

    # ── Build trigger ─────────────────────────────────────────────────────────
    build_result = None
    if action == "build":
        payload = result.get("build_payload") or {}
        # State is the source of truth; payload may refine it
        merged = {**state, **{k: v for k, v in payload.items() if v is not None}}

        template_id = merged.get("template_id")
        avatar  = merged.get("avatar")  or (CAMPAIGN_TEMPLATES.get(template_id or "", {}).get("avatar"))
        product = merged.get("product") or (CAMPAIGN_TEMPLATES.get(template_id or "", {}).get("product"))

        if not avatar or not product:
            reply += " (I still need to know which audience and loan product before I can build.)"
            action = "continue"
        else:
            flyer_image_url = None
            flyer_id = merged.get("flyer_id")
            if flyer_id:
                from app.models.flyer import GeneratedFlyer
                flyer = (await db.execute(
                    select(GeneratedFlyer).where(
                        GeneratedFlyer.id == flyer_id,
                        GeneratedFlyer.status == "complete",
                    )
                )).scalar_one_or_none()
                if flyer:
                    flyer_image_url = flyer.flyer_image_url

            log.info("concierge.build_triggered", session_id=session.id,
                     avatar=avatar, product=product, template_id=template_id,
                     combo=merged.get("material_combo"))

            build_result = await build_ad_campaign(
                db=db,
                avatar=avatar,
                product=product,
                proof=merged.get("proof"),
                market=merged.get("market", "MD"),
                budget_hint=merged.get("budget_hint", "low"),
                flyer_image_url=flyer_image_url,
                template_id=template_id,
                material_combo=merged.get("material_combo", "static"),
                video_aspect_ratio=merged.get("video_aspect_ratio"),
            )

            if "error" in build_result:
                reply += f" (Build failed: {build_result['error']})"
                action = "continue"
            else:
                session.status = "built"
                state["last_build_run_id"] = build_result.get("run_id")
                slug = build_result.get("campaign_page_slug")
                queued = build_result.get("approval_queue_ids", [])
                reply += (
                    f"\n\nDone — campaign built. "
                    f"{len(build_result.get('ad_units', []))} ad angles, sales letter"
                    + (f" (/campaign/{slug})" if slug else "")
                    + f", 3-email sequence, and {len(queued)} items waiting in your Approval Queue."
                )
                if build_result.get("video"):
                    v = build_result["video"]
                    reply += f" Video render: {v.get('status')} ({v.get('aspect_ratio')})."
                if build_result.get("combo_warning"):
                    reply += f" Note: {build_result['combo_warning']}"

    # ── Persist ───────────────────────────────────────────────────────────────
    now = datetime.utcnow().isoformat()
    history.append({"role": "user",  "text": message, "ts": now})
    history.append({"role": "agent", "text": reply,   "ts": now})
    session.history = history[-HISTORY_CAP:]
    session.state   = state

    try:
        await db.commit()
    except Exception as exc:
        log.error("concierge.persist_failed", session_id=session.id, error=str(exc))

    return {
        "session_id":   session.id,
        "reply":        reply,
        "action":       action,
        "state":        state,
        "missing":      missing,
        "build_result": build_result,
    }
