"""
Meta Marketing API — paid ad campaign publisher.

Creates the full stack: Campaign (HOUSING special ad category) → Ad Set
(targeting + budget) → Image → Creative → Ad. Everything is created PAUSED
unless activate=True, so nothing spends until the operator resumes it.

Env:
  META_AD_ACCOUNT_ID      — act_<digits> ad account ID
  META_ADS_ACCESS_TOKEN   — user/system-user token with ads_management scope
                            (falls back to META_ACCESS_TOKEN)
  META_PAGE_ID            — Facebook Page ID (already used for organic posting)

DRY RUN: if META_AD_ACCOUNT_ID or the token is missing, payloads are built and
logged but NOT sent — fake IDs prefixed "dry_" are returned. This lets the full
wiring be tested before credentials are in place.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx
import structlog

log = structlog.get_logger()

GRAPH = "https://graph.facebook.com/v25.0"   # supported until Jul 2028

CTA_MAP = {
    "learn more": "LEARN_MORE",
    "get quote":  "GET_QUOTE",
    "apply now":  "APPLY_NOW",
    "book now":   "BOOK_NOW",
    "sign up":    "SIGN_UP",
}

# Optimization goals that do NOT require a pixel/lead event — safe default
DEFAULT_OPTIMIZATION = "LANDING_PAGE_VIEWS"


@dataclass
class MetaPublishResult:
    success: bool
    dry_run: bool = False
    campaign_id: Optional[str] = None
    adset_id: Optional[str] = None
    creative_id: Optional[str] = None
    ad_id: Optional[str] = None
    error: Optional[str] = None
    steps: list = field(default_factory=list)   # [{step, status, id?, error?}]
    payloads: dict = field(default_factory=dict)  # what was (or would be) sent


def _token() -> str:
    return os.getenv("META_ADS_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN", "")


def _account() -> str:
    acct = os.getenv("META_AD_ACCOUNT_ID", "").strip()
    if acct and not acct.startswith("act_"):
        acct = f"act_{acct}"
    return acct


def configured() -> bool:
    return bool(_token() and _account())


def _parse_daily_budget(budget_str: str) -> Optional[int]:
    """'$25–35/day' → 2500 (cents, low end). Returns None if unparseable."""
    if not budget_str:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", budget_str.replace(",", ""))
    if not m:
        return None
    return int(float(m.group(1)) * 100)


async def _post(client: httpx.AsyncClient, path: str, payload: dict) -> dict:
    resp = await client.post(
        f"{GRAPH}/{path}",
        params={"access_token": _token()},
        json=payload,
    )
    data = resp.json() if resp.content else {}
    if resp.status_code not in (200, 201):
        err = data.get("error", {})
        raise RuntimeError(
            f"Meta {resp.status_code} on {path}: "
            f"{err.get('message', resp.text[:200])} (code {err.get('code')}, subcode {err.get('error_subcode')})"
        )
    return data


async def check_connection() -> dict:
    """Read-only: verify token + ad account access. Safe to call anytime."""
    if not configured():
        return {"configured": False, "dry_run": True,
                "note": "Set META_AD_ACCOUNT_ID + META_ADS_ACCESS_TOKEN to enable live publishing."}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{GRAPH}/{_account()}",
                params={"access_token": _token(), "fields": "name,account_status,currency,timezone_name,amount_spent"},
            )
            data = resp.json()
            if resp.status_code != 200:
                return {"configured": True, "connected": False,
                        "error": data.get("error", {}).get("message", resp.text[:200])}
            status_map = {1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED", 7: "PENDING_RISK_REVIEW",
                          8: "PENDING_SETTLEMENT", 9: "IN_GRACE_PERIOD", 100: "PENDING_CLOSURE", 101: "CLOSED"}
            return {
                "configured": True,
                "connected": True,
                "account_name": data.get("name"),
                "account_status": status_map.get(data.get("account_status"), data.get("account_status")),
                "currency": data.get("currency"),
                "timezone": data.get("timezone_name"),
                "amount_spent": data.get("amount_spent"),
            }
    except Exception as e:
        return {"configured": True, "connected": False, "error": str(e)}


async def _resolve_geo(client: httpx.AsyncClient, geo_str: str) -> list:
    """'Maryland + DC metro' → [{'key': <region id>, 'name': ...}]. Best-effort."""
    resolved = []
    terms = [t.strip() for t in re.split(r"\+|,", geo_str) if t.strip()]
    for term in terms[:2]:   # cap at 2 geo targets
        term = re.sub(r"\s*(metro|dma|area)\s*", "", term, flags=re.I).strip()
        try:
            resp = await client.get(
                f"{GRAPH}/search",
                params={"access_token": _token(), "type": "adgeolocation",
                        "q": term, "location_types": '["region"]', "limit": 1},
            )
            items = resp.json().get("data", [])
            if items:
                resolved.append({"key": items[0]["key"], "name": items[0].get("name", term)})
        except Exception as e:
            log.warning("meta_ads.geo_resolve_failed", term=term, error=str(e))
    return resolved


async def _resolve_interests(client: httpx.AsyncClient, names: list) -> list:
    """['First-time home buyer', ...] → [{'id': ..., 'name': ...}]. Best-effort."""
    resolved = []
    for name in (names or [])[:8]:
        try:
            resp = await client.get(
                f"{GRAPH}/search",
                params={"access_token": _token(), "type": "adinterest",
                        "q": name, "limit": 1},
            )
            items = resp.json().get("data", [])
            if items:
                resolved.append({"id": items[0]["id"], "name": items[0].get("name", name)})
        except Exception as e:
            log.warning("meta_ads.interest_resolve_failed", name=name, error=str(e))
    return resolved


def _placements_payload(placements: list) -> dict:
    fb_pos, ig_pos = [], []
    for p in placements or []:
        low = p.lower()
        if "facebook" in low and "feed" in low:
            fb_pos.append("feed")
        if "instagram" in low and "feed" in low:
            ig_pos.append("stream")
        if "stor" in low:
            (fb_pos if "facebook" in low else ig_pos).append("story" if "facebook" in low else "story")
        if "reel" in low:
            (fb_pos if "facebook" in low else ig_pos).append("facebook_reels" if "facebook" in low else "reels")
    payload = {}
    platforms = []
    if fb_pos:
        platforms.append("facebook")
        payload["facebook_positions"] = sorted(set(fb_pos))
    if ig_pos:
        platforms.append("instagram")
        payload["instagram_positions"] = sorted(set(ig_pos))
    if platforms:
        payload["publisher_platforms"] = platforms
    return payload


async def publish_campaign(
    name: str,
    facebook_setup: dict,
    ad_unit: dict,
    page_id: str,
    link_url: str,
    image_url: Optional[str] = None,
    daily_budget_override: Optional[int] = None,
    activate: bool = False,
) -> MetaPublishResult:
    """
    Full stack: Campaign → Ad Set → (Image) → Creative → Ad.

    facebook_setup: the template/LLM targeting block (geography, interests,
                    budget_daily, placements, cta_button, objective).
    ad_unit:        one ad angle (hook, ad_copy_body/body, headline).
    activate:       False → everything created PAUSED (default, safe).
    """
    result = MetaPublishResult(success=False, dry_run=not configured())
    status = "ACTIVE" if activate else "PAUSED"

    adset_cfg = facebook_setup.get("ad_set", facebook_setup)  # accept either nesting
    budget_cents = daily_budget_override or _parse_daily_budget(adset_cfg.get("budget_daily", ""))
    if not budget_cents:
        budget_cents = 2500   # $25/day fallback
        log.warning("meta_ads.budget_fallback", setup_budget=adset_cfg.get("budget_daily"))

    headline = (ad_unit.get("headline") or ad_unit.get("hook") or "")[:40]
    primary_text = ad_unit.get("ad_copy_body") or ad_unit.get("body") or ad_unit.get("core_argument") or ""
    cta_type = CTA_MAP.get((adset_cfg.get("cta_button") or "Learn More").strip().lower(), "LEARN_MORE")

    # ── Dry run: build all payloads, send nothing ─────────────────────────────
    campaign_payload = {
        "name": f"{name} — {facebook_setup.get('objective', 'LEAD_GENERATION')}",
        "objective": "OUTCOME_LEADS",
        "special_ad_categories": ["HOUSING"],
        "status": status,
    }
    targeting = {
        "geo_locations": {"regions": [], "country": "US"},
        "flexible_spec": [],
    }
    result.payloads["campaign"] = campaign_payload

    if result.dry_run:
        targeting["geo_locations"]["regions"] = [{"key": "UNRESOLVED", "name": adset_cfg.get("geography", "")}]
        targeting["flexible_spec"] = [{"interests": [{"id": "UNRESOLVED", "name": n} for n in (adset_cfg.get("interests") or [])]}]
        adset_payload = {
            "name": f"{name} — Ad Set",
            "campaign_id": "dry_campaign",
            "daily_budget": budget_cents,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": DEFAULT_OPTIMIZATION,
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "targeting": {**targeting, **_placements_payload(adset_cfg.get("placements"))},
            "status": status,
        }
        creative_payload = {
            "name": f"{name} — Creative",
            "object_story_spec": {
                "page_id": page_id,
                "link_data": {
                    "link": link_url,
                    "message": primary_text,
                    "name": headline,
                    "call_to_action": {"type": cta_type, "value": {"link": link_url}},
                    "image_hash": "dry_image" if image_url else None,
                },
            },
        }
        ad_payload = {"name": f"{name} — Ad", "adset_id": "dry_adset",
                      "creative": {"creative_id": "dry_creative"}, "status": status}
        result.payloads.update({"adset": adset_payload, "creative": creative_payload, "ad": ad_payload})
        result.success = True
        result.campaign_id, result.adset_id = "dry_campaign", "dry_adset"
        result.creative_id, result.ad_id = "dry_creative", "dry_ad"
        result.steps = [{"step": s, "status": "dry_run"} for s in ("campaign", "adset", "image", "creative", "ad")]
        log.info("meta_ads.dry_run", budget_cents=budget_cents, status=status)
        return result

    # ── Live ──────────────────────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            # 1. Campaign
            data = await _post(client, f"{_account()}/campaigns", campaign_payload)
            result.campaign_id = data["id"]
            result.steps.append({"step": "campaign", "status": "ok", "id": result.campaign_id})

            # 2. Ad Set — resolve geo + interests to Meta IDs
            regions = await _resolve_geo(client, adset_cfg.get("geography", ""))
            if regions:
                targeting["geo_locations"]["regions"] = regions
            else:
                del targeting["geo_locations"]["regions"]  # country-only fallback
            interests = await _resolve_interests(client, adset_cfg.get("interests") or [])
            if interests:
                targeting["flexible_spec"] = [{"interests": interests}]
            else:
                del targeting["flexible_spec"]

            adset_payload = {
                "name": f"{name} — Ad Set",
                "campaign_id": result.campaign_id,
                "daily_budget": budget_cents,
                "billing_event": "IMPRESSIONS",
                "optimization_goal": DEFAULT_OPTIMIZATION,
                "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                "targeting": {**targeting, **_placements_payload(adset_cfg.get("placements"))},
                "status": status,
            }
            result.payloads["adset"] = adset_payload
            data = await _post(client, f"{_account()}/adsets", adset_payload)
            result.adset_id = data["id"]
            result.steps.append({"step": "adset", "status": "ok", "id": result.adset_id})

            # 3. Image (optional, non-fatal) — Meta pulls from a PUBLIC url.
            #    localhost/unreachable URLs must not abort the publish: continue
            #    without image_hash (Meta falls back to scraping the link).
            image_hash = None
            if image_url:
                try:
                    data = await _post(client, f"{_account()}/adimages", {"url": image_url, "name": f"{name} creative"})
                    images = data.get("images", {})
                    first = next(iter(images.values()), {})
                    image_hash = first.get("hash")
                    result.steps.append({"step": "image", "status": "ok", "id": image_hash})
                except Exception as img_err:
                    log.warning("meta_ads.image_upload_failed", url=image_url, error=str(img_err))
                    result.steps.append({"step": "image", "status": "skipped", "error": str(img_err)[:150]})

            # 4. Creative
            link_data = {
                "link": link_url,
                "message": primary_text,
                "name": headline,
                "call_to_action": {"type": cta_type, "value": {"link": link_url}},
            }
            if image_hash:
                link_data["image_hash"] = image_hash
            creative_payload = {
                "name": f"{name} — Creative",
                "object_story_spec": {"page_id": page_id, "link_data": link_data},
            }
            result.payloads["creative"] = creative_payload
            data = await _post(client, f"{_account()}/adcreatives", creative_payload)
            result.creative_id = data["id"]
            result.steps.append({"step": "creative", "status": "ok", "id": result.creative_id})

            # 5. Ad
            ad_payload = {
                "name": f"{name} — Ad",
                "adset_id": result.adset_id,
                "creative": {"creative_id": result.creative_id},
                "status": status,
            }
            result.payloads["ad"] = ad_payload
            data = await _post(client, f"{_account()}/ads", ad_payload)
            result.ad_id = data["id"]
            result.steps.append({"step": "ad", "status": "ok", "id": result.ad_id})

        result.success = True
        log.info("meta_ads.published", campaign_id=result.campaign_id,
                 adset_id=result.adset_id, ad_id=result.ad_id, status=status)
        return result

    except Exception as e:
        result.error = str(e)
        result.steps.append({"step": "failed", "status": "error", "error": str(e)})
        log.error("meta_ads.publish_failed", error=str(e),
                  campaign_id=result.campaign_id, adset_id=result.adset_id)
        return result


# ── Performance + control ─────────────────────────────────────────────────────

async def get_campaign_insights(campaign_id: str, date_preset: str = "last_7d") -> dict:
    """
    Read-only performance pull for one campaign.

    "Leads" require a pixel/lead-form event; without one we fall back to
    landing_page_view as the result metric (matches LANDING_PAGE_VIEWS
    optimization) and say so in result_type.
    """
    if not configured():
        return {"error": "META_AD_ACCOUNT_ID / META_ADS_ACCESS_TOKEN not set", "dry_run": True}
    fields = "campaign_name,spend,impressions,clicks,inline_link_clicks,ctr,cpc,actions"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GRAPH}/{campaign_id}/insights",
                params={"access_token": _token(), "fields": fields, "date_preset": date_preset},
            )
            data = resp.json()
            if resp.status_code != 200:
                return {"campaign_id": campaign_id,
                        "error": data.get("error", {}).get("message", resp.text[:200])}
            rows = data.get("data", [])
            if not rows:
                return {"campaign_id": campaign_id, "spend": 0.0, "impressions": 0,
                        "clicks": 0, "results": 0, "result_type": "none",
                        "note": "no delivery in this date range"}
            r = rows[0]
            spend   = float(r.get("spend", 0) or 0)
            actions = r.get("actions", [])
            leads   = next((int(a["value"]) for a in actions if a.get("action_type") == "lead"), 0)
            lpvs    = next((int(a["value"]) for a in actions if a.get("action_type") == "landing_page_view"), 0)
            results, rtype = (leads, "lead") if leads else (lpvs, "landing_page_view")
            return {
                "campaign_id":   campaign_id,
                "campaign_name": r.get("campaign_name"),
                "spend":         spend,
                "impressions":   int(r.get("impressions", 0) or 0),
                "clicks":        int(r.get("clicks", 0) or 0),
                "link_clicks":   int(r.get("inline_link_clicks", 0) or 0),
                "ctr":           float(r.get("ctr", 0) or 0),
                "cpc":           float(r.get("cpc", 0) or 0),
                "results":       results,
                "result_type":   rtype,
                "cost_per_result": round(spend / results, 2) if results else None,
                "date_preset":   date_preset,
            }
    except Exception as e:
        return {"campaign_id": campaign_id, "error": str(e)}


async def set_campaign_status(campaign_id: str, status: str) -> dict:
    """ACTIVE | PAUSED — the go/stop switch."""
    if not configured():
        return {"success": False, "error": "not configured", "dry_run": True}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            data = await _post(client, campaign_id, {"status": status})
            ok = bool(data.get("success"))
            log.info("meta_ads.status_changed", campaign_id=campaign_id, status=status, ok=ok)
            return {"success": ok, "campaign_id": campaign_id, "status": status}
    except Exception as e:
        log.error("meta_ads.status_change_failed", campaign_id=campaign_id, error=str(e))
        return {"success": False, "campaign_id": campaign_id, "error": str(e)}
