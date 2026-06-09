"""
FRED API service — pulls Freddie Mac PMMS weekly mortgage rate data.

Series IDs:
  MORTGAGE30US  — 30-yr fixed conventional (weekly, published Thursdays)
  MORTGAGE15US  — 15-yr fixed conventional (weekly, published Thursdays)

FRED requires a free API key — it's free and takes 30 seconds:
  https://fred.stlouisfed.org/docs/api/api_key.html

Set FRED_API_KEY=your_key in your .env file.

PMMS data is WEEKLY (Thursdays). sync-fred saves the current AND previous
week's observations as separate dated snapshots so the ticker immediately
shows week-over-week arrows.
"""

import httpx
from datetime import date, timedelta
from typing import Optional
from dataclasses import dataclass
from app.config import settings

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


@dataclass
class FredObservation:
    obs_date: str        # YYYY-MM-DD — actual FRED release date
    value: float


async def fetch_observations(series_id: str, n: int = 3) -> list[FredObservation]:
    """
    Fetch the N most recent non-missing observations for a FRED series.
    Returns [] if FRED_API_KEY is not set or request fails.
    """
    api_key = settings.fred_api_key
    if not api_key:
        return []

    today = date.today()
    observation_start = (today - timedelta(days=120)).isoformat()
    params = {
        "series_id":        series_id,
        "observation_start": observation_start,
        "sort_order":       "desc",
        "limit":            n + 2,   # small buffer for any missing values
        "file_type":        "json",
        "api_key":          api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(FRED_BASE, params=params)
            res.raise_for_status()
            data = res.json()
            obs = [
                FredObservation(obs_date=o["date"], value=round(float(o["value"]), 2))
                for o in data.get("observations", [])
                if o["value"] != "."
            ]
            return obs[:n]
    except Exception:
        return []


async def fetch_prime_rate() -> Optional[float]:
    """
    Fetch the US Prime Loan Rate (FRED series: DPRIME).
    This is what HELOC rates float off. Updated whenever the Fed moves rates.
    Returns None if FRED_API_KEY not set or request fails.
    """
    obs = await fetch_observations("DPRIME", n=1)
    return obs[0].value if obs else None


async def fetch_fred_two_weeks() -> dict:
    """
    Fetch the latest TWO weekly PMMS observations with their actual dates.

    Returns:
    {
      "current":  {"date": "YYYY-MM-DD", "conv_30": x, "conv_15": x, ...spreads},
      "previous": {"date": "YYYY-MM-DD", "conv_30": x, ...spreads},
      "has_key":  bool,
      "error":    str | None,
    }
    """
    if not settings.fred_api_key:
        return {
            "current":  None,
            "previous": None,
            "has_key":  False,
            "error":    "FRED_API_KEY not set in .env — get a free key at fred.stlouisfed.org/docs/api/api_key.html",
        }

    conv_obs  = await fetch_observations("MORTGAGE30US", n=2)
    conv15_obs = await fetch_observations("MORTGAGE15US", n=2)

    if not conv_obs:
        return {
            "current":  None,
            "previous": None,
            "has_key":  True,
            "error":    "FRED returned no data — check your FRED_API_KEY is valid and try again.",
        }

    # Pull Prime Rate for HELOC calculation (single extra request)
    prime = await fetch_prime_rate()
    heloc = round(prime + settings.heloc_prime_spread, 2) if prime else None

    def build_snapshot(conv_30: Optional[float], conv_15: Optional[float], obs_date: str) -> dict:
        return {
            "date":                   obs_date,
            "rate_conventional_30":   conv_30,
            "rate_conventional_15":   conv_15,
            "rate_fha_30":            round(conv_30 - 0.10, 2) if conv_30 else None,
            "rate_va_30":             round(conv_30 - 0.25, 2) if conv_30 else None,
            "rate_usda_30":           round(conv_30 - 0.15, 2) if conv_30 else None,
            "rate_dscr":              round(conv_30 + 1.00, 2) if conv_30 else None,
            "rate_heloc_prime_plus":  heloc,   # FRED Prime Rate + spread (HELOC_PRIME_SPREAD in .env)
            "rate_jumbo_30":          round(conv_30 + 0.25, 2) if conv_30 else None,
        }

    current_conv   = conv_obs[0].value  if len(conv_obs) > 0 else None
    previous_conv  = conv_obs[1].value  if len(conv_obs) > 1 else None
    current_date   = conv_obs[0].obs_date if len(conv_obs) > 0 else date.today().isoformat()
    previous_date  = conv_obs[1].obs_date if len(conv_obs) > 1 else None

    current_conv15  = conv15_obs[0].value if len(conv15_obs) > 0 else None
    previous_conv15 = conv15_obs[1].value if len(conv15_obs) > 1 else None

    return {
        "current":  build_snapshot(current_conv,  current_conv15,  current_date),
        "previous": build_snapshot(previous_conv, previous_conv15, previous_date) if previous_date else None,
        "has_key":  True,
        "error":    None,
    }


# ── Legacy helpers (still used by /rates/current live fallback) ──────────────

async def fetch_latest_rate(series_id: str) -> Optional[float]:
    obs = await fetch_observations(series_id, n=1)
    return obs[0].value if obs else None


async def fetch_fred_snapshot() -> dict:
    """Legacy: returns just the latest rate dict (no dates). Used by /rates/current fallback."""
    conv_30  = await fetch_latest_rate("MORTGAGE30US")
    conv_15  = await fetch_latest_rate("MORTGAGE15US")
    prime    = await fetch_prime_rate()
    heloc    = round(prime + settings.heloc_prime_spread, 2) if prime else None
    return {
        "rate_conventional_30":  conv_30,
        "rate_conventional_15":  conv_15,
        "rate_fha_30":           round(conv_30 - 0.10, 2) if conv_30 else None,
        "rate_va_30":            round(conv_30 - 0.25, 2) if conv_30 else None,
        "rate_usda_30":          round(conv_30 - 0.15, 2) if conv_30 else None,
        "rate_dscr":             round(conv_30 + 1.00, 2) if conv_30 else None,
        "rate_heloc_prime_plus": heloc,
        "rate_jumbo_30":         round(conv_30 + 0.25, 2) if conv_30 else None,
        "source": "fred",
    }
