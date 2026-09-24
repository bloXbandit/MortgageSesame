"""
Ad Campaign Builder — Advertising Skills Chain Runner

Loads the mortgage-tuned SKILL.md files from app/agents/skills/advertising/
and runs the 9-step campaign generation chain via ai_service.

Called by POST /agent/build-campaign.
All output routes to the Approval Queue — nothing goes live without human review.

NOTE: CAMPAIGN_TEMPLATES below are state-specific (MD/DC examples). Review and
update suggested_headline, geography, proof examples, and market fields before
deploying for another state or banker.
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
    "facebook_setup":       "09_facebook-meta-setup.md",
    "material_combos":      "12_material-combos.md",
    "orchestrator":         "ORCHESTRATOR.md",
}

VALID_AVATARS  = {"declined_buyer", "first_timer", "equity_prisoner", "realtor_client"}
VALID_PRODUCTS = {"fha", "va", "dpa", "conventional", "heloc", "dscr", "refi"}
VALID_MARKETS  = {"MD", "DC", "both"}
VALID_BUDGETS  = {"low", "mid", "scale"}
VALID_COMBOS   = {"static", "video", "voice_graphic", "full_stack", "repurpose"}


# ── Pre-built campaign templates ─────────────────────────────────────────────
# Each template is a plug-and-play scenario. Agent can list these and launch
# any one with a single call to build_ad_campaign(template_id=...).

CAMPAIGN_TEMPLATES = {
    "first_timer_dpa": {
        "id":          "first_timer_dpa",
        "name":        "First-Time Buyer + Down Payment Assistance",
        "description": "Targets renters ready to buy — removes the #1 objection (down payment) using MMP, Flex, and Chenoa Fund DPA programs. Highest volume opportunity in MD/DC.",
        "avatar":      "first_timer",
        "product":     "dpa",
        "market":      "MD",
        "budget_hint": "low",
        "suggested_headline":    "Maryland Has Down Payment Money Waiting for You",
        "suggested_subheadline": "First-time buyers are getting into homes with little to no money down.",
        "suggested_cta":         "See If You Qualify →",
        "sample_proof":          "e.g. 'Helped a Bowie MD renter buy a $320k home — $0 out of pocket using MMP DPA'",
        "facebook": {
            "special_ad_category": "HOUSING",
            "objective":           "LEAD_GENERATION",
            "geography":           "Maryland + DC metro (DMA — not ZIP restricted)",
            "interests":           ["First-time home buyer", "Renting an apartment", "Real estate", "Personal finance"],
            "behaviors":           ["Likely to move", "Recently moved"],
            "custom_audiences":    ["Website visitors — /dpa page", "Email list of renters"],
            "lookalike":           ["1% LAL of past FHA/DPA closings"],
            "exclude":             ["Known homeowners suppression list (if available)"],
            "budget_daily":        "$25–35/day",
            "min_run_days":        5,
            "placements":          ["Facebook Feed", "Instagram Feed", "Facebook Stories"],
            "ad_format":           "social_square (1080×1080) — show family at keys ceremony",
            "cta_button":          "Learn More",
        },
    },
    "fha_purchase": {
        "id":          "fha_purchase",
        "name":        "FHA Purchase — 3.5% Down",
        "description": "Broad purchase campaign — 3.5% down, flexible credit. Best for buyers with 580–680 credit who think they can't qualify conventional.",
        "avatar":      "first_timer",
        "product":     "fha",
        "market":      "MD",
        "budget_hint": "low",
        "suggested_headline":    "Get Into a Home with 3.5% Down",
        "suggested_subheadline": "FHA loans are built for real buyers — flexible credit, low down payment.",
        "suggested_cta":         "Check My Options →",
        "sample_proof":          "e.g. 'Closed a Hyattsville buyer — $312k home, 3.5% down, 11 business days'",
        "facebook": {
            "special_ad_category": "HOUSING",
            "objective":           "LEAD_GENERATION",
            "geography":           "Maryland + DC (DMA)",
            "interests":           ["Home buying", "Mortgage", "Real estate", "Credit score improvement"],
            "behaviors":           ["Likely to move", "Recently moved", "First-time home buyer"],
            "custom_audiences":    ["Website visitors", "Leads who opened but didn't convert"],
            "lookalike":           ["1% LAL of past FHA clients"],
            "budget_daily":        "$30–40/day",
            "min_run_days":        5,
            "placements":          ["Facebook Feed", "Instagram Feed"],
            "ad_format":           "social_square or carousel (show 3 home price ranges)",
            "cta_button":          "Learn More",
        },
    },
    "va_purchase": {
        "id":          "va_purchase",
        "name":        "VA Loan — Veterans & Active Duty",
        "description": "$0 down, no PMI — the most underused earned benefit. Best for veterans and active duty in MD/DC/PG County/Anne Arundel markets.",
        "avatar":      "first_timer",
        "product":     "va",
        "market":      "MD",
        "budget_hint": "low",
        "suggested_headline":    "You Earned $0 Down. Are You Using It?",
        "suggested_subheadline": "VA loans let veterans buy with no down payment and no PMI.",
        "suggested_cta":         "Check My VA Benefit →",
        "sample_proof":          "e.g. 'Closed a Fort Meade veteran — $415k home, $0 down, no PMI'",
        "facebook": {
            "special_ad_category": "HOUSING",
            "objective":           "LEAD_GENERATION",
            "geography":           "MD + DC + military-adjacent (PG County, Prince William, Anne Arundel, Fort Meade area)",
            "interests":           ["Veterans", "United States Armed Forces", "Military families", "VA loan"],
            "behaviors":           ["US military veterans", "Active duty military"],
            "custom_audiences":    ["Past VA clients", "Veteran org email lists"],
            "lookalike":           ["1% LAL of past VA clients"],
            "budget_daily":        "$20–30/day",
            "min_run_days":        5,
            "placements":          ["Facebook Feed", "Instagram Feed"],
            "ad_format":           "social_square — direct, respectful copy. No clickbait.",
            "cta_button":          "Learn More",
        },
    },
    "heloc_equity": {
        "id":          "heloc_equity",
        "name":        "HELOC — Tap Your Home Equity",
        "description": "Targets existing homeowners sitting on equity. Best for home improvement, debt consolidation, investment property down payment.",
        "avatar":      "equity_prisoner",
        "product":     "heloc",
        "market":      "MD",
        "budget_hint": "low",
        "suggested_headline":    "Your Home Equity Is Sitting Idle",
        "suggested_subheadline": "A HELOC puts your equity to work — home improvement, debt payoff, or investing.",
        "suggested_cta":         "See My Equity Options →",
        "sample_proof":          "e.g. 'Helped a Rockville homeowner pull $85k equity at 8.5% — paid off $60k in credit cards'",
        "facebook": {
            "special_ad_category": "HOUSING",
            "objective":           "LEAD_GENERATION",
            "geography":           "Maryland + DC homeowner-heavy areas (DMA level)",
            "interests":           ["Home improvement", "Home equity", "Real estate investing", "Debt consolidation"],
            "behaviors":           ["Homeowners"],
            "custom_audiences":    ["Past purchase clients 2+ years ago", "Website visitors — /rates or /heloc page"],
            "lookalike":           ["1% LAL of past HELOC/cash-out clients"],
            "budget_daily":        "$25–35/day",
            "min_run_days":        5,
            "placements":          ["Facebook Feed", "Instagram Feed"],
            "ad_format":           "social_square — before/after concept (debt burden vs. freedom)",
            "cta_button":          "Learn More",
        },
    },
    "refi_rate_term": {
        "id":          "refi_rate_term",
        "name":        "Refinance — Rate / Term",
        "description": "Targets homeowners who bought at higher rates (2022–2023). Rate-sensitive campaign — monitor FRED weekly and pause if rates rise significantly.",
        "avatar":      "equity_prisoner",
        "product":     "refi",
        "market":      "MD",
        "budget_hint": "low",
        "suggested_headline":    "Your Rate Is Too High. Here's What You Could Pay.",
        "suggested_subheadline": "Maryland homeowners are refinancing and cutting hundreds off their monthly payment.",
        "suggested_cta":         "See My New Rate →",
        "sample_proof":          "e.g. 'Refinanced a Silver Spring homeowner from 7.25% → 6.5% — saved $312/month'",
        "facebook": {
            "special_ad_category": "HOUSING",
            "objective":           "LEAD_GENERATION",
            "geography":           "Maryland + DC",
            "interests":           ["Refinancing", "Mortgage", "Personal finance", "Interest rates"],
            "behaviors":           ["Homeowners"],
            "custom_audiences":    ["Leads from 2020–2023 purchases", "Past clients not yet refinanced"],
            "lookalike":           ["1% LAL of past refi clients"],
            "budget_daily":        "$20–30/day",
            "min_run_days":        5,
            "placements":          ["Facebook Feed", "Instagram Feed"],
            "ad_format":           "social_square — rate comparison visual (old rate vs. new rate)",
            "cta_button":          "Get Quote",
        },
    },
    "conventional_purchase": {
        "id":          "conventional_purchase",
        "name":        "Conventional Purchase — 5–20% Down",
        "description": "Targets buyers who can qualify conventional — skip FHA and avoid lifetime MIP. Good for 680+ credit buyers.",
        "avatar":      "first_timer",
        "product":     "conventional",
        "market":      "MD",
        "budget_hint": "low",
        "suggested_headline":    "Skip FHA. Conventional Is Better For You.",
        "suggested_subheadline": "If your credit is 680+, conventional means lower long-term cost — no lifetime MIP.",
        "suggested_cta":         "See If I Qualify →",
        "sample_proof":          "e.g. 'Moved a buyer from FHA to conventional — saved $187/month by eliminating MIP'",
        "facebook": {
            "special_ad_category": "HOUSING",
            "objective":           "LEAD_GENERATION",
            "geography":           "Maryland + DC",
            "interests":           ["Home buying", "Real estate", "Personal finance", "Mortgage"],
            "behaviors":           ["Likely to move", "Recently moved"],
            "custom_audiences":    ["FHA leads who may now qualify conventional", "Website visitors"],
            "lookalike":           ["1% LAL of past conventional clients"],
            "budget_daily":        "$30–40/day",
            "min_run_days":        5,
            "placements":          ["Facebook Feed", "Instagram Feed"],
            "ad_format":           "social_square",
            "cta_button":          "Learn More",
        },
    },
    "dscr_investor": {
        "id":          "dscr_investor",
        "name":        "DSCR — Real Estate Investor",
        "description": "Targets real estate investors — no W2 required, qualify on rental income. Best for landlords and portfolio builders.",
        "avatar":      "realtor_client",
        "product":     "dscr",
        "market":      "both",
        "budget_hint": "mid",
        "suggested_headline":    "Buy Investment Property — No W2 Required",
        "suggested_subheadline": "DSCR loans qualify on rental income. Scale your portfolio without income docs.",
        "suggested_cta":         "See DSCR Options →",
        "sample_proof":          "e.g. 'Closed an investor in Laurel — $285k rental, DSCR 1.25x, closed in 18 days with no W2'",
        "facebook": {
            "special_ad_category": "HOUSING",
            "objective":           "LEAD_GENERATION",
            "geography":           "MD + DC + national (DSCR is nationwide)",
            "interests":           ["Real estate investing", "Rental property", "Passive income", "Landlord", "Real estate investor"],
            "behaviors":           ["Small business owners"],
            "custom_audiences":    ["Past investors", "Website visitors — rates page"],
            "lookalike":           ["1% LAL of past DSCR clients"],
            "budget_daily":        "$25–40/day",
            "min_run_days":        7,
            "placements":          ["Facebook Feed", "Instagram Feed"],
            "ad_format":           "social_square or short video — numbers-driven copy",
            "cta_button":          "Learn More",
        },
    },
    "declined_buyer": {
        "id":          "declined_buyer",
        "name":        "Declined Buyer — Second Chance",
        "description": "Retargets buyers who were turned down elsewhere. High-intent audience — they already want to buy, they just need the right lender.",
        "avatar":      "declined_buyer",
        "product":     "fha",
        "market":      "MD",
        "budget_hint": "low",
        "suggested_headline":    "Got Turned Down? We Get Buyers Approved.",
        "suggested_subheadline": "When other lenders say no, we find a way. FHA, DPA, and credit solutions.",
        "suggested_cta":         "Get a Second Opinion →",
        "sample_proof":          "e.g. 'Approved a buyer who had been declined twice — closed in 14 days'",
        "facebook": {
            "special_ad_category": "HOUSING",
            "objective":           "LEAD_GENERATION",
            "geography":           "Maryland + DC",
            "interests":           ["Home buying", "Credit repair", "Mortgage", "FHA loan"],
            "behaviors":           ["Likely to move"],
            "custom_audiences":    ["CRM — leads marked declined/lost (retarget list)", "Website visitors — /rates or /dpa page"],
            "lookalike":           ["1% LAL of past FHA clients with 580–640 credit"],
            "budget_daily":        "$20–25/day",
            "min_run_days":        5,
            "placements":          ["Facebook Feed", "Instagram Feed"],
            "ad_format":           "social_square — empathetic copy, second-chance framing",
            "cta_button":          "Learn More",
        },
    },
    "realtor_partner": {
        "id":          "realtor_partner",
        "name":        "Realtor Partnership",
        "description": "B2B campaign targeting real estate agents. Goal is referral relationships — position as the lender who closes fast and communicates clearly.",
        "avatar":      "realtor_client",
        "product":     "conventional",
        "market":      "MD",
        "budget_hint": "low",
        "suggested_headline":    "Your Buyers Need a Lender Who Closes in 10 Days",
        "suggested_subheadline": "I give your clients fast pre-approvals and keep you in the loop every step.",
        "suggested_cta":         "Let's Partner →",
        "sample_proof":          "e.g. 'Closed 3 of a Keller Williams agent's listings in 60 days — all on time'",
        "facebook": {
            "special_ad_category": "HOUSING",
            "objective":           "LEAD_GENERATION",
            "geography":           "Maryland + DC",
            "interests":           ["Real estate agent", "Real estate broker", "Keller Williams", "RE/MAX", "Coldwell Banker"],
            "behaviors":           ["Real estate agent (job title)"],
            "custom_audiences":    ["Realtor contacts from CRM", "Website visitors"],
            "lookalike":           ["1% LAL of past realtor referral partners"],
            "budget_daily":        "$15–25/day",
            "min_run_days":        7,
            "placements":          ["Facebook Feed", "Instagram Feed"],
            "ad_format":           "social_square or 30s video — face-to-camera, professional",
            "cta_button":          "Learn More",
        },
    },
}


def _load_skill(key: str) -> str:
    """Load a skill file and return its content as a string."""
    path = SKILLS_DIR / SKILL_FILES[key]
    if not path.exists():
        log.warning("skill_file_missing", path=str(path))
        return f"[Skill file {SKILL_FILES[key]} not found]"
    return path.read_text(encoding="utf-8")


def _build_system_prompt(avatar: str, product: str, reference_context: str = "") -> str:
    """
    Assemble the full system prompt by loading all skill files.
    Injects avatar + product context so the chain is pre-focused.
    Optionally injects reference_context (existing sales letter headline/proof)
    to anchor the new campaign to proven copy.
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
    facebook      = _load_skill("facebook_setup")
    combos        = _load_skill("material_combos")
    orchestrator  = _load_skill("orchestrator")

    name  = _s.banker_name
    nmls  = _s.banker_nmls
    state = _s.service_states

    reference_block = ""
    if reference_context:
        reference_block = f"""
=== REFERENCE CAMPAIGN (existing — use as inspiration, not copy) ===
The following is an existing sales letter/campaign that performed well.
Carry forward the core angle, proof, and hook. Evolve it — don't repeat it verbatim.

{reference_context}

===
"""

    return f"""You are the advertising campaign builder for {name}, a {state} mortgage banker (NMLS #{nmls}).

You have deep expertise in direct-response mortgage advertising using the Eugene Schwartz awareness model,
the sales letter methodology, and conversion-focused copywriting.

CURRENT CAMPAIGN:
- Avatar: {avatar}
- Product: {product}
{reference_block}
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

=== SKILL 09: FACEBOOK / META AD SETUP ===
{facebook}

=== SKILL 12: MATERIAL COMBOS (flyer / video / voice assembly) ===
{combos}

=== ORCHESTRATOR (your operating sequence) ===
{orchestrator}

COMPLIANCE RULES (non-negotiable):
- Include NMLS #{nmls} in all copy
- No specific interest rate claims
- No guaranteed approval language
- Soft CTA only for cold/warm traffic
- Illustrative scenarios must be framed as "for example" or "hypothetically"
- Equal Housing Opportunity on all landing page copy
- All Meta/Facebook ads must use Special Ad Category: HOUSING

REAL LINKS & FACTS — use these verbatim wherever copy calls for them.
NEVER output bracketed placeholders like [link], [url], [website], [phone]:
- Zillow profile / reviews: {_s.zillow_url or "(not configured — omit the link reference)"}
- Booking / free call: {_s.calcom_link or "(not configured)"}
- Full application (1003): {_s.app_1003_url or "(not configured)"}
- Banker phone: {_s.banker_phone or "(not configured)"}
- Email: {_s.campaign_from_email or "(not configured)"}
- Email merge fields [Name] / [First Name] are allowed ONLY inside email_sequence bodies — never in the sales letter.
"""


def _scrub_campaign_copy(result: dict) -> list:
    """
    Replace known placeholder tokens in generated copy with real configured
    values. Returns a list of leftover [token] strings we couldn't resolve
    (surfaced as result['placeholder_warnings']).
    Merge fields [Name]/[First Name] are kept inside email_sequence bodies —
    they're resolved per-recipient at deploy time.
    """
    import re as _re

    mapping = {
        "link": _s.zillow_url, "zillow": _s.zillow_url, "zillow link": _s.zillow_url,
        "zillow profile": _s.zillow_url, "review link": _s.zillow_url,
        "url": _s.zillow_url, "website": _s.zillow_url,
        "booking": _s.calcom_link, "cal.com link": _s.calcom_link,
        "calendar link": _s.calcom_link, "call link": _s.calcom_link,
        "1003": _s.app_1003_url, "application link": _s.app_1003_url,
        "phone": _s.banker_phone, "nmls": _s.banker_nmls,
        "email": _s.campaign_from_email,
    }
    merge_ok = {"name", "first name", "first_name"}

    def _sub_text(text, keep_merge=False):
        if not isinstance(text, str):
            return text, []
        leftovers = []

        def _rep(m):
            raw = m.group(0)
            token = (m.group(1) or m.group(2) or "").strip().lower()
            if token in merge_ok:
                return raw if keep_merge else "there"   # public letter — generic fallback
            val = mapping.get(token)
            if val:
                return val
            leftovers.append(raw)
            return raw

        out = _re.sub(r"\[([^\[\]]{1,40})\]|\{([^{}]{1,40})\}", _rep, text)
        return out, leftovers

    leftovers_all = []

    # Sales letter — public-facing, no merge fields allowed
    letter = result.get("sales_letter") or {}
    for key in ("headline", "subheadline", "lead_opening", "villain_paragraph",
                "proof_block", "cta_primary", "cta_secondary", "compliance_footer"):
        if key in letter:
            letter[key], left = _sub_text(letter[key])
            leftovers_all += left
    for step in letter.get("method_steps") or []:
        for key in ("title", "body"):
            if isinstance(step, dict) and key in step:
                step[key], left = _sub_text(step[key])
                leftovers_all += left

    # Email sequence — keep merge fields
    for email in result.get("email_sequence") or []:
        for key in ("subject", "body"):
            if isinstance(email, dict) and key in email:
                email[key], left = _sub_text(email[key], keep_merge=True)
                leftovers_all += left

    # Ad units — public-facing
    for unit in result.get("ad_units") or []:
        if isinstance(unit, dict):
            for key, val in list(unit.items()):
                if isinstance(val, str):
                    unit[key], left = _sub_text(val)
                    leftovers_all += left

    return sorted(set(leftovers_all))


async def build_ad_campaign(
    db: AsyncSession,
    avatar: str,
    product: str,
    proof: Optional[str] = None,
    market: str = "MD",
    budget_hint: str = "low",
    flyer_image_url: Optional[str] = None,
    template_id: Optional[str] = None,
    reference_page_slug: Optional[str] = None,
    material_combo: str = "static",
    video_aspect_ratio: Optional[str] = None,
) -> dict:
    """
    Run the full 9-step advertising skill chain.

    template_id: pre-built scenario (see CAMPAIGN_TEMPLATES) — auto-populates
                 avatar/product/market/budget_hint if not overridden.
    reference_page_slug: existing CampaignPage slug — pulls headline/proof_block
                 and injects as reference context so the new campaign builds on
                 what already worked.
    material_combo: static | video | voice_graphic | full_stack | repurpose —
                 which creative materials to assemble (see 12_material-combos.md).
                 video/full_stack also submit a HeyGen avatar video render from
                 the winning ad angle's hook (async — poll /agent/materials later).
    video_aspect_ratio: 9:16 | 1:1 — override auto-detection from template placements.

    Returns the complete campaign package including facebook_setup block.
    Routes all assets to the Approval Queue.
    """
    from app.models.campaign import CampaignPage
    from sqlalchemy import select as _sel

    # ── Apply template defaults (explicit args override template) ─────────────
    template = CAMPAIGN_TEMPLATES.get(template_id) if template_id else None
    if template:
        avatar      = avatar      or template["avatar"]
        product     = product     or template["product"]
        market      = market      or template.get("market", "MD")
        budget_hint = budget_hint or template.get("budget_hint", "low")

    # ── Validate inputs ───────────────────────────────────────────────────────
    if avatar not in VALID_AVATARS:
        return {"error": f"Invalid avatar '{avatar}'. Valid: {sorted(VALID_AVATARS)}"}
    if product not in VALID_PRODUCTS:
        return {"error": f"Invalid product '{product}'. Valid: {sorted(VALID_PRODUCTS)}"}
    if market not in VALID_MARKETS:
        market = "MD"
    if budget_hint not in VALID_BUDGETS:
        budget_hint = "low"
    if material_combo not in VALID_COMBOS:
        material_combo = "static"
    combo_warning = None
    if budget_hint == "low" and material_combo in ("video", "full_stack"):
        combo_warning = (
            "Video render requested on a 'low' budget hint — video costs provider credits. "
            "Honored because it was explicitly requested."
        )
        log.info("ad_campaign.combo_budget_mismatch", combo=material_combo, budget=budget_hint)
    # Auto aspect ratio: template placements decide; explicit arg wins
    if video_aspect_ratio not in ("9:16", "1:1"):
        video_aspect_ratio = None
    if video_aspect_ratio is None and template:
        placements = template.get("facebook", {}).get("placements", [])
        has_vertical = any(p for p in placements if "stor" in p.lower() or "reel" in p.lower())
        video_aspect_ratio = "9:16" if has_vertical else "1:1"
    if video_aspect_ratio is None:
        video_aspect_ratio = "1:1"

    # ── Pull reference sales letter if slug provided ───────────────────────────
    reference_context = ""
    if reference_page_slug:
        try:
            page = (await db.execute(
                _sel(CampaignPage).where(CampaignPage.slug == reference_page_slug)
            )).scalar_one_or_none()
            if page:
                parts = []
                if page.headline:
                    parts.append(f"Headline: {page.headline}")
                if page.subheadline:
                    parts.append(f"Subheadline: {page.subheadline}")
                if page.proof_block:
                    parts.append(f"Proof block: {page.proof_block}")
                if page.body_html:
                    # Strip HTML tags for clean text injection
                    import re
                    clean = re.sub(r'<[^>]+>', ' ', page.body_html)
                    clean = re.sub(r'\s+', ' ', clean).strip()
                    parts.append(f"Body (excerpt): {clean[:1500]}")
                reference_context = "\n".join(parts)
                log.info("ad_campaign.reference_loaded", slug=reference_page_slug)
        except Exception as e:
            log.warning("ad_campaign.reference_load_failed", slug=reference_page_slug, error=str(e))

    run_id = str(uuid.uuid4())
    log.info("ad_campaign.start", run_id=run_id, avatar=avatar, product=product,
             market=market, template_id=template_id, has_reference=bool(reference_context))

    system = _build_system_prompt(avatar, product, reference_context)

    proof_line  = f"\nReal proof point to weave in (use this verbatim or very close): {proof}" if proof else ""
    flyer_line  = (
        f"\nVISUAL CREATIVE: A branded flyer image has been prepared for this campaign. "
        f"URL: {flyer_image_url}\n"
        "Write all ad copy, email subject lines, and CTAs as if this visual will accompany "
        "the message. The flyer already carries the headline visually — the copy should "
        "complement it, not repeat it verbatim."
    ) if flyer_image_url else ""
    combo_line  = f"\nMATERIAL COMBO for this build: {material_combo}. Apply the rules in SKILL 12 — only reference materials that combo actually includes."

    user_prompt = f"""Build a complete ad campaign using the full 9-step chain from the ORCHESTRATOR.

Campaign parameters:
- Avatar: {avatar}
- Product: {product}
- Market: {market}
- Budget hint: {budget_hint}{proof_line}{flyer_line}{combo_line}

Run all steps in sequence (0 through 8).
Return the final JSON output package exactly as specified in the ORCHESTRATOR's "FINAL OUTPUT PACKAGE" section.
Output ONLY valid JSON — no markdown, no preamble, no explanation outside the JSON object.
"""

    try:
        result = await ai_service.complete_json(user_prompt, system=system, model=None)
    except Exception as exc:
        log.error("ad_campaign.generation_failed", run_id=run_id, error=str(exc))
        return {"error": f"Generation failed: {str(exc)}", "run_id": run_id}

    # ── Material assembly: HeyGen avatar video (video / full_stack combos) ─────
    video_info = None
    if material_combo in ("video", "full_stack"):
        try:
            from app.services.providers.video import get_video_provider
            from app.models.content import MediaAsset

            # Script: winning ad unit's hook + core argument, trimmed for 30–45s read
            ad_units = result.get("ad_units", [])
            first = ad_units[0] if ad_units else {}
            hook = first.get("hook", "")
            body = first.get("core_argument", "")
            cta  = first.get("cta_text", "Book a free call.")
            script = " ".join(p for p in [hook, body, cta] if p).strip()
            if not script:
                raise ValueError("No ad hook available to build a video script")
            script = script[:600]   # keep the read under ~45 seconds

            provider = get_video_provider()
            vr = await provider.generate_video({
                "script":       script,
                "aspect_ratio": video_aspect_ratio,
                "test_mode":    os.getenv("HEYGEN_TEST_MODE", "true").lower() == "true",
            })

            asset = MediaAsset(
                name=f"campaign_video_{run_id[:8]}",
                asset_type="video_raw",
                mime_type="video/mp4",
                file_url=vr.video_url,
                tags=["heygen", "campaign", avatar, product,
                      f"run:{run_id}", f"aspect:{video_aspect_ratio}"]
                     + ([f"provider_id:{vr.provider_id}"] if vr.provider_id else []),
            )
            db.add(asset)
            await db.flush()

            video_info = {
                "asset_id":     asset.id,
                "provider_id":  vr.provider_id,
                "status":       vr.status,          # processing | completed | failed
                "video_url":    vr.video_url,
                "aspect_ratio": video_aspect_ratio,
                "script_used":  script,
                "test_mode":    os.getenv("HEYGEN_TEST_MODE", "true").lower() == "true",
                "error":        vr.error,
            }
            result["video"] = video_info
            log.info("ad_campaign.video_submitted", run_id=run_id,
                     provider_id=vr.provider_id, status=vr.status, aspect=video_aspect_ratio)
        except Exception as exc:
            log.error("ad_campaign.video_failed", run_id=run_id, error=str(exc))
            result["video"] = {"status": "failed", "error": str(exc), "aspect_ratio": video_aspect_ratio}

    result["material_combo"] = material_combo
    if combo_warning:
        result["combo_warning"] = combo_warning

    # ── Scrub placeholder tokens out of generated copy before saving ─────────
    # The model sometimes emits [link], [Name], {booking} etc. — substitute the
    # real configured values for known tokens and log whatever remains.
    letter = result.get("sales_letter", {})
    placeholder_warnings = _scrub_campaign_copy(result)
    if placeholder_warnings:
        result["placeholder_warnings"] = placeholder_warnings
        log.warning("ad_campaign.placeholders_left", run_id=run_id, tokens=placeholder_warnings)

    # ── Save campaign page (unpublished by default) ───────────────────────────
    saved_slug = None
    try:
        from app.models.campaign import CampaignPage
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
