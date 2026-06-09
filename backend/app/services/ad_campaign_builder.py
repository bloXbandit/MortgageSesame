"""
Ad Campaign Builder — Advertising Skills Chain Runner

Loads the mortgage-tuned SKILL.md files from app/agents/skills/advertising/
and runs the 9-step campaign generation chain via ai_service.

Called by POST /agent/build-campaign.
All output routes to the Approval Queue — nothing goes live without human review.
"""

import os
import json
import uuid
import structlog
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import ai_service
from app.middleware.audit import log_event
from app.config import settings as _s

log = structlog.get_logger()

# ── Skill file paths ──────────────────────────────────────────────────────────

SKILLS_DIR = Path(__file__).parent.parent / "agents" / "skills" / "advertising"

SKILL_FILES = {
    "avatar_library":       "00_mortgage-avatar-library.md",
    "offer_templates":      "01_offer-templates.md",
    "schwartz_guide":       "02_schwartz-awareness-guide.md",
    "mechanism_builder":    "03_mechanism-builder.md",
    "angle_multiplier":     "04_ad-angle-multiplier.md",
    "scroll_creative":      "05_scroll-stopping-creative.md",
    "sales_letter":         "06_sales-letter-architect.md",
    "objection_crusher":    "07_objection-crusher.md",
    "language_killer":      "08_generic-language-killer.md",
    "orchestrator":         "ORCHESTRATOR.md",
}

VALID_AVATARS  = {"declined_buyer", "first_timer", "equity_prisoner", "realtor_client"}
VALID_PRODUCTS = {"fha", "va", "dpa", "conventional", "heloc", "dscr", "refi"}
VALID_MARKETS  = {"MD", "DC", "both"}
VALID_BUDGETS  = {"low", "mid", "scale"}


def _load_skill(key: str) -> str:
    """Load a skill file and return its content as a string."""
    path = SKILLS_DIR / SKILL_FILES[key]
    if not path.exists():
        log.warning("skill_file_missing", path=str(path))
        return f"[Skill file {SKILL_FILES[key]} not found]"
    return path.read_text(encoding="utf-8")


def _build_system_prompt(avatar: str, product: str) -> str:
    """
    Assemble the full system prompt by loading all skill files.
    Injects avatar + product context so the chain is pre-focused.
    """
    avatar_lib    = _load_skill("avatar_library")
    offer_tpls    = _load_skill("offer_templates")
    schwartz      = _load_skill("schwartz_guide")
    mechanisms    = _load_skill("mechanism_builder")
    angles        = _load_skill("angle_multiplier")
    creative      = _load_skill("scroll_creative")
    letter        = _load_skill("sales_letter")
    objections    = _load_skill("objection_crusher")
    qa            = _load_skill("language_killer")
    orchestrator  = _load_skill("orchestrator")

    name  = _s.banker_name
    nmls  = _s.banker_nmls
    state = _s.service_states

    return f"""You are the advertising campaign builder for {name}, a {state} mortgage banker (NMLS #{nmls}).

You have deep expertise in direct-response mortgage advertising using the Eugene Schwartz awareness model,
the sales letter methodology, and conversion-focused copywriting.

CURRENT CAMPAIGN:
- Avatar: {avatar}
- Product: {product}

You have access to the following skill libraries that define exactly how to build this campaign.
Read them carefully. They are your operating instructions.

=== SKILL 00: AVATAR LIBRARY ===
{avatar_lib}

=== SKILL 01: OFFER TEMPLATES ===
{offer_tpls}

=== SKILL 02: SCHWARTZ AWARENESS GUIDE ===
{schwartz}

=== SKILL 03: MECHANISM BUILDER ===
{mechanisms}

=== SKILL 04: AD ANGLE MULTIPLIER ===
{angles}

=== SKILL 05: SCROLL-STOPPING CREATIVE ===
{creative}

=== SKILL 06: SALES LETTER ARCHITECT ===
{letter}

=== SKILL 07: OBJECTION CRUSHER ===
{objections}

=== SKILL 08: GENERIC LANGUAGE KILLER (apply to all output) ===
{qa}

=== ORCHESTRATOR (your operating sequence) ===
{orchestrator}

COMPLIANCE RULES (non-negotiable):
- Include NMLS #{nmls} in all copy
- No specific interest rate claims
- No guaranteed approval language
- Soft CTA only for cold/warm traffic
- Illustrative scenarios must be framed as "for example" or "hypothetically"
- Equal Housing Opportunity on all landing page copy
"""


async def build_ad_campaign(
    db: AsyncSession,
    avatar: str,
    product: str,
    proof: Optional[str] = None,
    market: str = "MD",
    budget_hint: str = "low",
    flyer_image_url: Optional[str] = None,
) -> dict:
    """
    Run the full 9-step advertising skill chain.

    Returns the complete campaign package.
    Routes all assets to the Approval Queue.
    """

    # ── Validate inputs ───────────────────────────────────────────────────────
    if avatar not in VALID_AVATARS:
        return {"error": f"Invalid avatar '{avatar}'. Valid: {sorted(VALID_AVATARS)}"}
    if product not in VALID_PRODUCTS:
        return {"error": f"Invalid product '{product}'. Valid: {sorted(VALID_PRODUCTS)}"}
    if market not in VALID_MARKETS:
        market = "MD"
    if budget_hint not in VALID_BUDGETS:
        budget_hint = "low"

    run_id = str(uuid.uuid4())
    log.info("ad_campaign.start", run_id=run_id, avatar=avatar, product=product, market=market)

    system = _build_system_prompt(avatar, product)

    proof_line  = f"\nReal proof point to weave in (use this verbatim or very close): {proof}" if proof else ""
    flyer_line  = (
        f"\nVISUAL CREATIVE: A branded flyer image has been prepared for this campaign. "
        f"URL: {flyer_image_url}\n"
        "Write all ad copy, email subject lines, and CTAs as if this visual will accompany "
        "the message. The flyer already carries the headline visually — the copy should "
        "complement it, not repeat it verbatim."
    ) if flyer_image_url else ""

    user_prompt = f"""Build a complete ad campaign using the full 9-step chain from the ORCHESTRATOR.

Campaign parameters:
- Avatar: {avatar}
- Product: {product}
- Market: {market}
- Budget hint: {budget_hint}{proof_line}{flyer_line}

Run all steps in sequence (0 through 8).
Return the final JSON output package exactly as specified in the ORCHESTRATOR's "FINAL OUTPUT PACKAGE" section.
Output ONLY valid JSON — no markdown, no preamble, no explanation outside the JSON object.
"""

    try:
        result = await ai_service.complete_json(user_prompt, system=system, model=None)
    except Exception as exc:
        log.error("ad_campaign.generation_failed", run_id=run_id, error=str(exc))
        return {"error": f"Generation failed: {str(exc)}", "run_id": run_id}

    # ── Save campaign page (unpublished by default) ───────────────────────────
    saved_slug = None
    try:
        from app.models.campaign import CampaignPage
        letter = result.get("sales_letter", {})
        slug = letter.get("url_slug") or f"{avatar}-{product}-{run_id[:6]}"
        # Sanitise slug — lowercase, hyphens only
        import re
        slug = re.sub(r"[^a-z0-9-]", "-", slug.lower()).strip("-")

        page = CampaignPage(
            slug=slug,
            avatar=avatar,
            product=product,
            market=market,
            run_id=run_id,
            headline=letter.get("headline"),
            subheadline=letter.get("subheadline"),
            lead_opening=letter.get("lead_opening"),
            villain_paragraph=letter.get("villain_paragraph"),
            method_steps=letter.get("method_steps", []),
            proof_block=letter.get("proof_block"),
            cta_primary=letter.get("cta_primary"),
            cta_secondary=letter.get("cta_secondary"),
            compliance_footer=letter.get("compliance_footer"),
            ad_units=result.get("ad_units", []),
            email_sequence=result.get("email_sequence", []),
            flyer_image_url=flyer_image_url,
            is_published=False,
            created_by="hermes_campaign_builder",
        )
        db.add(page)
        await db.flush()
        saved_slug = slug
        result["campaign_page_slug"] = slug
        result["campaign_page_url"] = f"/campaign/{slug}"
        log.info("ad_campaign.page_saved", run_id=run_id, slug=slug)
    except Exception as exc:
        log.error("ad_campaign.page_save_failed", run_id=run_id, error=str(exc))

    # ── Route assets to Approval Queue ────────────────────────────────────────
    queue_ids = []
    try:
        from app.models.agent import ApprovalQueue, ApprovalItemType

        ad_units = result.get("ad_units", [])
        for i, unit in enumerate(ad_units):
            hook_preview = unit.get("hook", "")[:120]
            item = ApprovalQueue(
                item_type=ApprovalItemType.SOCIAL_POST,
                item_id=run_id,
                title=f"Ad Unit {i+1} — {avatar} × {product} — {unit.get('angle_type', f'angle_{i+1}')}",
                preview=hook_preview,
                priority=1,
                created_by="hermes_campaign_builder",
            )
            db.add(item)
            await db.flush()
            queue_ids.append(item.id)

        letter = result.get("sales_letter", {})
        if letter:
            letter_item = ApprovalQueue(
                item_type=ApprovalItemType.CONTENT_ITEM,
                item_id=run_id,
                title=f"Sales Letter — {avatar} × {product} — {letter.get('url_slug', 'no-slug')}",
                preview=(letter.get("headline", "")[:200]),
                priority=1,
                created_by="hermes_campaign_builder",
            )
            db.add(letter_item)
            await db.flush()
            queue_ids.append(letter_item.id)

        email_seq = result.get("email_sequence", [])
        for email in email_seq:
            day = email.get("day", "?")
            email_item = ApprovalQueue(
                item_type=ApprovalItemType.CAMPAIGN_STEP,
                item_id=run_id,
                title=f"Email Day {day} — {avatar} × {product}",
                preview=email.get("subject", "")[:200],
                priority=0,
                created_by="hermes_campaign_builder",
            )
            db.add(email_item)
            await db.flush()
            queue_ids.append(email_item.id)

        await db.commit()
        log.info("ad_campaign.queued", run_id=run_id, queue_item_count=len(queue_ids))

    except Exception as exc:
        log.error("ad_campaign.queue_failed", run_id=run_id, error=str(exc))

    # ── Log the run ───────────────────────────────────────────────────────────
    try:
        await log_event(
            db, "agent.ad_campaign_built",
            actor_type="agent",
            resource_type="campaign",
            resource_id=run_id,
            details={
                "avatar": avatar,
                "product": product,
                "market": market,
                "budget_hint": budget_hint,
                "has_proof": bool(proof),
                "ad_units_count": len(result.get("ad_units", [])),
                "queue_items": len(queue_ids),
            },
        )
        await db.commit()
    except Exception:
        pass

    return {
        "status": "pipeline_complete",
        "run_id": run_id,
        "flyer_image_url": flyer_image_url,
        **result,
        "approval_queue_ids": queue_ids,
        "note": (
            "All assets are pending your review at /approvals. "
            "Nothing goes live until you approve each item."
        ),
    }
