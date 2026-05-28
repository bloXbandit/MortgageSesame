"""
Compliance guardrail service.

Checks outreach drafts and content for prohibited claims before they reach the approval queue.
Never blocks user-initiated review — always surfaces flags as warnings or blocks.
"""

import re
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


@dataclass
class ComplianceResult:
    passed: bool
    flags: list[dict] = field(default_factory=list)
    sanitized_text: str | None = None

    def add_flag(self, rule: str, snippet: str, severity: Severity, suggestion: str = ""):
        self.flags.append({
            "rule": rule,
            "snippet": snippet,
            "severity": severity.value,
            "suggestion": suggestion,
        })
        if severity == Severity.BLOCKED:
            self.passed = False


# Patterns that are absolutely prohibited
BLOCKED_PATTERNS = [
    (r"\bguaranteed?\s+(approval|loan|rate|financing)\b", "guaranteed_approval",
     "Remove guaranteed approval claims. Replace with 'subject to credit approval'."),
    (r"\b100\s*%\s*(approval|approved|financing|guaranteed)\b", "guaranteed_100pct",
     "Remove guaranteed approval claims."),
    (r"\bno\s+(credit\s+check|income\s+verification|doc)\b", "no_verification_claim",
     "Never claim no credit check or no verification."),
    (r"\binstant\s+(approval|loan|pre-?approval)\b", "instant_approval",
     "Avoid 'instant approval' claims. Use 'fast turnaround' or 'quick decision'."),
    (r"\bi\s+(will\s+pay|am\s+paying|pay)\s+you\s+(for\s+)?(referral|leads?|sending)\b", "referral_fee_language",
     "Never offer to pay for referrals — RESPA violation risk."),
    (r"\b(kickback|referral\s+fee|split\s+(my\s+)?commission)\b", "kickback_language",
     "Referral fee/kickback language is a RESPA violation."),
    (r"\bgovernment\s+(approved|backed|endorsed)\b(?!.*\b(fha|va|usda)\b)", "false_gov_affiliation",
     "Avoid misleading government affiliation claims."),
    (r"\b(fake|fabricated)\s+(testimonial|review|closing|story)\b", "fake_testimonial",
     "Never create fake testimonials or fake closings."),
]

HIGH_PATTERNS = [
    (r"\blowest\s+(rate|payment|cost)\s+in\b", "lowest_rate_superlative",
     "Superlative rate claims require substantiation. Use 'competitive rates' instead."),
    (r"\bact\s+now.{0,20}(rates?\s+are\s+rising|before\s+rates?\s+go\s+up)\b", "false_urgency",
     "Avoid manufactured urgency. Real market conditions should be cited."),
    (r"\b(as\s+low\s+as|starting\s+at)\s+[\d.]+\s*%", "teaser_rate",
     "Teaser rate claims require APR disclosure and rep/warranty language."),
    (r"\btax\s+(free|exempt)\s+cash\b", "tax_claim",
     "Tax advice claims require CPA/attorney disclaimer."),
]

MEDIUM_PATTERNS = [
    (r"\bfree\s+(money|grant|cash)\b", "misleading_free_money",
     "DPA is not 'free money'. Use 'down payment assistance programs' instead."),
    (r"\bno\s+(money\s+down|down\s+payment\s+required)\b(?!\s+with\s+(va|usda))", "no_down_payment",
     "No-money-down claims should specify the program (VA, USDA, DPA)."),
    (r"\byour\s+(house|home)\s+is\s+at\s+risk", "scare_tactic",
     "Avoid fear-based messaging about losing homes."),
]

OPT_OUT_REQUIRED_CHANNELS = {"email", "sms"}


def check_content(text: str, channel: str = "general", is_ad: bool = False) -> ComplianceResult:
    result = ComplianceResult(passed=True)
    lower = text.lower()

    for pattern, rule, suggestion in BLOCKED_PATTERNS:
        match = re.search(pattern, lower)
        if match:
            result.add_flag(rule, match.group(0), Severity.BLOCKED, suggestion)

    for pattern, rule, suggestion in HIGH_PATTERNS:
        match = re.search(pattern, lower)
        if match:
            result.add_flag(rule, match.group(0), Severity.HIGH, suggestion)

    for pattern, rule, suggestion in MEDIUM_PATTERNS:
        match = re.search(pattern, lower)
        if match:
            result.add_flag(rule, match.group(0), Severity.MEDIUM, suggestion)

    if channel in OPT_OUT_REQUIRED_CHANNELS:
        if not re.search(r"(unsubscribe|opt.?out|reply\s+stop|remove\s+me)", lower):
            result.add_flag(
                "missing_opt_out",
                "[no opt-out language found]",
                Severity.HIGH,
                f"All {channel} messages must include opt-out instructions.",
            )

    if is_ad:
        if not re.search(r"(nmls|#\s*\d{4,}|equal\s+housing|not\s+a\s+commitment)", lower):
            result.add_flag(
                "missing_ad_disclaimer",
                "[no NMLS/Equal Housing disclaimer]",
                Severity.MEDIUM,
                "Mortgage ads should include NMLS ID and Equal Housing Opportunity disclosure.",
            )

    return result


def check_contact_sendable(contact) -> tuple[bool, str]:
    """Returns (can_send, reason). Blocks sending to DNC/opted-out contacts."""
    if contact.is_dnc:
        return False, "Contact is on Do-Not-Contact list."
    if contact.is_opted_out:
        return False, "Contact has opted out."
    return True, ""
