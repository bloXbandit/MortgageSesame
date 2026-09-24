"""
OAuth token refresh utilities for platform publishers.

Neither LinkedIn nor TikTok auto-refresh tokens — you must call these when
tokens expire. Recommended: set a monthly cron reminder.

Expiry reference:
  LinkedIn    access_token       60 days    (refresh_token up to 1 year)
  TikTok      access_token       24 hours   (refresh_token 365 days)

Additional ENV required (beyond publisher tokens):
  LINKEDIN_CLIENT_ID
  LINKEDIN_CLIENT_SECRET
  TIKTOK_CLIENT_KEY
  TIKTOK_CLIENT_SECRET

After refreshing, update LINKEDIN_ACCESS_TOKEN / TIKTOK_ACCESS_TOKEN in your .env
and restart the backend.  (A future enhancement could persist tokens to the DB.)
"""

import os
import httpx
import structlog

log = structlog.get_logger()


async def refresh_linkedin_token(refresh_token: str) -> dict:
    """
    Exchange a LinkedIn refresh_token for a new access_token.

    Returns:
        {success, access_token, expires_in, refresh_token, refresh_token_expires_in}
        OR {success: False, error: str}
    """
    client_id     = os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        return {"success": False, "error": "LINKEDIN_CLIENT_ID or LINKEDIN_CLIENT_SECRET not set in env"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type":    "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id":     client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.RequestError as exc:
        return {"success": False, "error": f"Network error: {exc}"}

    if res.status_code != 200:
        log.error("linkedin_token_refresh_failed", status=res.status_code, body=res.text[:300])
        return {"success": False, "error": f"LinkedIn returned {res.status_code}: {res.text[:200]}"}

    data = res.json()
    log.info("linkedin_token_refreshed", expires_in=data.get("expires_in"))
    return {
        "success":                    True,
        "access_token":               data.get("access_token"),
        "expires_in":                 data.get("expires_in"),          # seconds
        "refresh_token":              data.get("refresh_token"),
        "refresh_token_expires_in":   data.get("refresh_token_expires_in"),
        "note": (
            "Update LINKEDIN_ACCESS_TOKEN in your .env file with the new access_token, "
            "then restart the backend process."
        ),
    }


async def refresh_tiktok_token(refresh_token: str) -> dict:
    """
    Exchange a TikTok refresh_token for a new access_token + open_id.

    Returns:
        {success, access_token, open_id, expires_in, refresh_token, refresh_expires_in}
        OR {success: False, error: str}
    """
    client_key    = os.getenv("TIKTOK_CLIENT_KEY", "")
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "")

    if not client_key or not client_secret:
        return {"success": False, "error": "TIKTOK_CLIENT_KEY or TIKTOK_CLIENT_SECRET not set in env"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                "https://open.tiktokapis.com/v2/oauth/token/refresh/",
                data={
                    "client_key":    client_key,
                    "client_secret": client_secret,
                    "grant_type":    "refresh_token",
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.RequestError as exc:
        return {"success": False, "error": f"Network error: {exc}"}

    if res.status_code != 200:
        log.error("tiktok_token_refresh_failed", status=res.status_code, body=res.text[:300])
        return {"success": False, "error": f"TikTok returned {res.status_code}: {res.text[:200]}"}

    data = res.json()
    if data.get("error"):
        return {"success": False, "error": data.get("error_description", data.get("error"))}

    log.info("tiktok_token_refreshed", open_id=data.get("open_id"), expires_in=data.get("expires_in"))
    return {
        "success":             True,
        "access_token":        data.get("access_token"),
        "open_id":             data.get("open_id"),
        "expires_in":          data.get("expires_in"),          # seconds
        "refresh_token":       data.get("refresh_token"),
        "refresh_expires_in":  data.get("refresh_expires_in"),  # seconds
        "note": (
            "Update TIKTOK_ACCESS_TOKEN and TIKTOK_OPEN_ID in your .env file with the new values, "
            "then restart the backend process."
        ),
    }


async def exchange_meta_token(short_lived_token: str) -> dict:
    """
    Exchange a short-lived Meta user token (~1-2h) for a long-lived one (~60 days).

    Requires FB_APP_ID + FB_APP_SECRET in env
    (App Dashboard → Settings → Basic).

    Returns {success, access_token, expires_in_days, expires_at} or {success: False, error}.
    """
    app_id     = os.getenv("FB_APP_ID", "")
    app_secret = os.getenv("FB_APP_SECRET", "")
    if not app_id or not app_secret:
        return {"success": False, "error": "FB_APP_ID or FB_APP_SECRET not set in env"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                "https://graph.facebook.com/v25.0/oauth/access_token",
                params={
                    "grant_type":        "fb_exchange_token",
                    "client_id":         app_id,
                    "client_secret":     app_secret,
                    "fb_exchange_token": short_lived_token,
                },
            )
    except httpx.RequestError as exc:
        return {"success": False, "error": f"Network error: {exc}"}

    data = res.json()
    if res.status_code != 200 or data.get("error"):
        err = data.get("error", {})
        log.error("meta_token_exchange_failed", status=res.status_code, body=str(data)[:300])
        return {"success": False, "error": err.get("message", f"Meta returned {res.status_code}")}

    from datetime import datetime, timedelta
    expires_in = data.get("expires_in")          # seconds; ~5,184,000 = 60 days
    expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() if expires_in else None
    log.info("meta_token_exchanged", expires_in=expires_in)
    return {
        "success":       True,
        "access_token":  data.get("access_token"),
        "expires_in":    expires_in,
        "expires_days":  round(expires_in / 86400, 1) if expires_in else None,
        "expires_at":    expires_at,
        "note": "Paste this as META_ADS_ACCESS_TOKEN in .env, then restart the backend.",
    }
