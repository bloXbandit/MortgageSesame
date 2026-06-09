"""
Campaign prospect scoring engine.

Scores each prospect for refi/HELOC/DSCR/DPA/realtor campaign fit.
Designed to run on imported property data — works with or without full loan details.

Score components are additive/subtractive. Final score 0–100+ clamped to 0–100.
Grade cutoffs:  80+ = A_TARGET | 60–79 = B_TARGET | 40–59 = NURTURE | <40 = SKIP
Blocked (DNC/opt-out) always → BLOCKED regardless of score.
"""

from datetime import date, datetime
from typing import Optional
from dataclasses import dataclass, field
from app.models.outreach import ScoreGrade

# ── Reason codes ──────────────────────────────────────────────────────────────
REASON = {
    "HIGH_RATE_RECENT_BUYER":    "Bought in high-rate window (2022–present) — refi candidate",
    "HIGH_EQUITY_HELOC":         "25%+ equity — strong HELOC/cash-out candidate",
    "FHA_STREAMLINE_WATCH":      "FHA loan, elevated rate — streamline refi possible",
    "CASHOUT_REVIEW":            "Significant equity — cash-out refi review warranted",
    "INVESTOR_DSCR":             "Non-owner-occupied — DSCR investor refi candidate",
    "DPA_BUYER_POSSIBLE":        "Low equity / new buyer profile — DPA intro valuable",
    "REALTOR_PARTNER_TARGET":    "Realtor/agent — partnership outreach target",
    "TITLE_PARTNER_TARGET":      "Title/settlement — partner outreach target",
    "LARGE_LOAN_AMOUNT":         "Loan ≥$250K — higher-value refinance opportunity",
    "NO_REFI_DETECTED":          "No recent refinance — likely still on original rate",
    "OWNER_OCCUPIED_REFI":       "Owner-occupied — eligible for refi/HELOC programs",
    "RATE_WATCH_ONLY":           "Marginal score — add to nurture/rate watch",
    "SKIP_LOW_SIGNAL":           "Insufficient data or low probability of fit",
    "BLOCKED_DNC":               "Do-not-contact flagged — blocked",
    "BLOCKED_SUPPRESSED":        "On suppression list — blocked",
    "RECENT_PURCHASE":           "Purchased within 90 days — too soon for refi",
    "RECENT_REFI":               "Refinanced within 12 months — unlikely candidate",
}


@dataclass
class ScoreResult:
    score: int = 0
    grade: ScoreGrade = ScoreGrade.SKIP
    reason_codes: list[str] = field(default_factory=list)
    score_details: dict = field(default_factory=dict)
    recommended_channel: str = "email"
    recommended_template: str = "refi_certificate"

    def add(self, points: int, reason: str, detail: str = ""):
        self.score += points
        if reason not in self.reason_codes:
            self.reason_codes.append(reason)
        self.score_details[reason] = {"points": points, "detail": detail or REASON.get(reason, reason)}

    def clamp(self):
        self.score = max(0, min(100, self.score))

    def classify(self):
        self.clamp()
        if "BLOCKED_DNC" in self.reason_codes or "BLOCKED_SUPPRESSED" in self.reason_codes:
            self.grade = ScoreGrade.BLOCKED
        elif self.score >= 80:
            self.grade = ScoreGrade.A_TARGET
        elif self.score >= 60:
            self.grade = ScoreGrade.B_TARGET
        elif self.score >= 40:
            self.grade = ScoreGrade.NURTURE
        else:
            self.grade = ScoreGrade.SKIP


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _days_since(date_str: Optional[str]) -> Optional[int]:
    d = _parse_date(date_str)
    if d:
        return (date.today() - d).days
    return None


def score_prospect(
    current_rate_estimate: Optional[float] = None,
    origination_date: Optional[str] = None,
    purchase_date: Optional[str] = None,
    estimated_equity_pct: Optional[float] = None,
    current_loan_amount: Optional[float] = None,
    loan_type: Optional[str] = None,
    last_refi_date: Optional[str] = None,
    is_owner_occupied: Optional[bool] = None,
    is_investment_property: Optional[bool] = None,
    prospect_type: Optional[str] = None,   # homeowner/investor/realtor/title_agent/past_client
    is_do_not_contact: bool = False,
    is_suppressed: bool = False,
) -> ScoreResult:
    """
    Score a single prospect. Returns a ScoreResult with grade, reasons, and recommendations.
    All inputs are optional — scoring degrades gracefully with partial data.
    """
    result = ScoreResult(score=50)  # Start at neutral; adjustments move it up or down

    # ── Hard blocks ───────────────────────────────────────────────────────────
    if is_do_not_contact:
        result.add(-200, "BLOCKED_DNC")
        result.classify()
        return result
    if is_suppressed:
        result.add(-200, "BLOCKED_SUPPRESSED")
        result.classify()
        return result

    # ── Realtor / title partner scoring (different logic) ────────────────────
    if prospect_type in ("realtor", "title_agent"):
        result.score = 60  # Start higher — these are always worth reaching
        if prospect_type == "realtor":
            result.add(0, "REALTOR_PARTNER_TARGET")
            result.recommended_channel = "email"
            result.recommended_template = "realtor_invite"
        else:
            result.add(0, "TITLE_PARTNER_TARGET")
            result.recommended_channel = "email"
            result.recommended_template = "realtor_invite"
        result.classify()
        return result

    # ── Rate environment scoring ──────────────────────────────────────────────
    if current_rate_estimate and current_rate_estimate >= 6.5:
        result.add(30, "HIGH_RATE_RECENT_BUYER",
                   f"Estimated rate {current_rate_estimate:.2f}% — meaningful savings possible")
    elif current_rate_estimate and current_rate_estimate >= 6.0:
        result.add(15, "HIGH_RATE_RECENT_BUYER",
                   f"Estimated rate {current_rate_estimate:.2f}% — marginal savings opportunity")

    # ── Origination / purchase date ────────────────────────────────────────────
    orig_days = _days_since(origination_date) or _days_since(purchase_date)
    if orig_days is not None:
        if orig_days <= 90:
            result.add(-50, "RECENT_PURCHASE", "Closed within 90 days — skip for now")
        elif 90 < orig_days <= 365 * 1.5:  # 90 days to 18 months
            result.add(25, "HIGH_RATE_RECENT_BUYER",
                       "Originated in high-rate window (likely 2022–2024)")
        elif 365 * 1.5 < orig_days <= 365 * 4:  # 18mo to 4yr
            result.add(15, "HIGH_RATE_RECENT_BUYER",
                       "Mid-vintage loan — may still be above current market")

    # ── Equity scoring ────────────────────────────────────────────────────────
    if estimated_equity_pct:
        if estimated_equity_pct >= 40:
            result.add(25, "HIGH_EQUITY_HELOC",
                       f"{estimated_equity_pct:.0f}% equity — prime HELOC/cash-out candidate")
            result.add(5, "CASHOUT_REVIEW", "High equity warrants cash-out review")
        elif estimated_equity_pct >= 25:
            result.add(20, "HIGH_EQUITY_HELOC",
                       f"{estimated_equity_pct:.0f}% equity — solid HELOC candidate")
        elif estimated_equity_pct < 10 and is_owner_occupied:
            result.add(8, "DPA_BUYER_POSSIBLE", "Low equity — could benefit from DPA info")

    # ── Loan amount ───────────────────────────────────────────────────────────
    if current_loan_amount and current_loan_amount >= 250_000:
        result.add(15, "LARGE_LOAN_AMOUNT",
                   f"${current_loan_amount:,.0f} balance — larger rate savings per basis point")
    elif current_loan_amount and current_loan_amount >= 150_000:
        result.add(8, "LARGE_LOAN_AMOUNT", f"${current_loan_amount:,.0f} balance")

    # ── FHA streamline ────────────────────────────────────────────────────────
    loan_type_lower = (loan_type or "").lower()
    if "fha" in loan_type_lower:
        if current_rate_estimate and current_rate_estimate >= 6.0:
            result.add(10, "FHA_STREAMLINE_WATCH",
                       "FHA loan at elevated rate — streamline refi likely eligible")
        result.recommended_template = "fha_streamline_notice"

    # ── No recent refi ────────────────────────────────────────────────────────
    refi_days = _days_since(last_refi_date)
    if refi_days is None:
        result.add(10, "NO_REFI_DETECTED", "No refinance history found in public records")
    elif refi_days < 365:
        result.add(-25, "RECENT_REFI", "Refinanced within last 12 months")

    # ── Occupancy ─────────────────────────────────────────────────────────────
    if is_owner_occupied is True:
        result.add(10, "OWNER_OCCUPIED_REFI", "Owner-occupied — full product menu eligible")
    if is_investment_property is True or prospect_type == "investor":
        result.add(10, "INVESTOR_DSCR", "Investment/non-owner — DSCR refi candidate")
        result.recommended_template = "dscr_investor_notice"

    # ── Channel + template recommendation based on equity ─────────────────────
    if estimated_equity_pct and estimated_equity_pct >= 25:
        result.recommended_channel = "direct_mail"
        result.recommended_template = result.recommended_template or "equity_voucher"
    elif current_rate_estimate and current_rate_estimate >= 6.5:
        result.recommended_channel = "direct_mail"
        result.recommended_template = result.recommended_template or "refi_certificate"
    else:
        result.recommended_channel = "email"
        result.recommended_template = result.recommended_template or "refi_certificate"

    result.classify()
    return result


def score_prospect_from_dict(data: dict) -> ScoreResult:
    """Convenience wrapper — pass a prospect record as a dict."""
    return score_prospect(
        current_rate_estimate=data.get("current_rate_estimate"),
        origination_date=data.get("origination_date"),
        purchase_date=data.get("purchase_date"),
        estimated_equity_pct=data.get("estimated_equity_pct"),
        current_loan_amount=data.get("current_loan_amount"),
        loan_type=data.get("loan_type"),
        last_refi_date=data.get("last_refi_date"),
        is_owner_occupied=data.get("is_owner_occupied"),
        is_investment_property=data.get("is_investment_property"),
        prospect_type=data.get("prospect_type"),
        is_do_not_contact=data.get("is_do_not_contact", False),
        is_suppressed=data.get("is_suppressed", False),
    )
