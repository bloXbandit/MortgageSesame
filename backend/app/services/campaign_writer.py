"""
Campaign content writer — elite sales copy for every channel and campaign type.

Generates:
  - Direct mail HTML (via mail_templates.py merge data)
  - Email sequences (multi-touch subject + HTML + text)
  - SMS drip messages
  - Call scripts with talking points

Philosophy: We write like an elite mortgage sales pro who genuinely knows
the homeowner's situation — their specific rate, equity, loan vintage.
Personalization turns generic blast into "how did they know?"

Usage:
    writer = CampaignWriter()
    draft = await writer.generate_email(prospect, campaign_type="refi_rate_reduction", step=1)
    mailer = await writer.generate_direct_mail(prospect, template_key="equity_voucher")
    sms    = await writer.generate_sms(prospect, campaign_type="cash_out_equity", step=1)
    script = await writer.generate_call_script(prospect, trigger="qr_scan")
"""

import os
import json
import structlog
from typing import Optional, Literal
from dataclasses import dataclass, field
from app.config import settings as _s

# ── Operator identity — sourced from .env, never hardcode below this line ──────
_BANKER_NAME = _s.banker_name
_BANKER_NMLS = _s.banker_nmls
_BOOKING_URL = _s.calcom_link
_APP_NAME    = _s.app_name

# Imported lazily to avoid circular imports at module load
def _unsubscribe_url(email: str) -> str:
    try:
        from app.routers.unsubscribe import generate_unsubscribe_url
        return generate_unsubscribe_url(email)
    except Exception:
        return "#unsubscribe"

log = structlog.get_logger()

# ── Draft result types ────────────────────────────────────────────────────────

@dataclass
class EmailDraft:
    subject: str
    body_html: str
    body_text: str
    merge_data: dict = field(default_factory=dict)
    campaign_type: str = ""
    step: int = 1

@dataclass
class SmsDraft:
    body: str
    campaign_type: str = ""
    step: int = 1
    char_count: int = 0

    def __post_init__(self):
        self.char_count = len(self.body)

@dataclass
class CallScript:
    opener: str
    pitch: str
    talking_points: list[str] = field(default_factory=list)
    objection_handlers: dict = field(default_factory=dict)
    close: str = ""
    voicemail: str = ""
    trigger: str = ""

@dataclass
class MailMergeData:
    """Merge fields for a direct mail template."""
    recipient_name: str = "Homeowner"
    property_address: str = ""
    estimated_equity: str = ""
    estimated_equity_dollars: str = ""
    current_rate: str = ""
    current_payment: str = ""
    new_rate: str = ""
    new_payment: str = ""
    monthly_savings: str = ""
    loan_type: str = ""
    qr_url: str = ""
    qr_code: str = ""
    booking_url: str = field(default_factory=lambda: _s.calcom_link)
    phone: str = ""
    nmls: str = field(default_factory=lambda: _s.banker_nmls)
    banker_name: str = field(default_factory=lambda: _s.banker_name)
    template_key: str = "equity_voucher"


# ── Prospect data accessor ────────────────────────────────────────────────────

def _prospect_ctx(prospect) -> dict:
    """
    Extract a clean context dict from a Prospect ORM object or plain dict.
    Handles both because the writer is called from API routes (ORM) and
    agent endpoints (dicts).
    """
    if isinstance(prospect, dict):
        p = prospect
    else:
        p = {
            "first_name": getattr(prospect, "first_name", None),
            "last_name":  getattr(prospect, "last_name", None),
            "full_name":  getattr(prospect, "full_name", None),
            "email":      getattr(prospect, "email", None),
            "phone":      getattr(prospect, "phone", None),
            "property_address":        getattr(prospect, "property_address", None),
            "property_city":           getattr(prospect, "property_city", None),
            "property_state":          getattr(prospect, "property_state", None),
            "current_rate_estimate":   getattr(prospect, "current_rate_estimate", None),
            "origination_date":        getattr(prospect, "origination_date", None),
            "estimated_equity_pct":    getattr(prospect, "estimated_equity_pct", None),
            "estimated_equity_dollars":getattr(prospect, "estimated_equity_dollars", None),
            "estimated_current_value": getattr(prospect, "estimated_current_value", None),
            "current_loan_amount":     getattr(prospect, "current_loan_amount", None),
            "loan_type":               getattr(prospect, "loan_type", None),
            "is_owner_occupied":       getattr(prospect, "is_owner_occupied", None),
            "is_investment_property":  getattr(prospect, "is_investment_property", None),
            "prospect_type":           getattr(prospect, "prospect_type", None),
            "company_name":            getattr(prospect, "company_name", None),
            "recent_transactions":     getattr(prospect, "recent_transactions", None),
            "lender_name":             getattr(prospect, "lender_name", None),
        }

    # Derived values
    first = p.get("first_name") or (p.get("full_name") or "").split()[0] or "Homeowner"
    rate  = p.get("current_rate_estimate")
    equity_pct  = p.get("estimated_equity_pct")
    equity_dollars = p.get("estimated_equity_dollars")
    loan_bal = p.get("current_loan_amount")
    prop_val = p.get("estimated_current_value")
    loan_type = (p.get("loan_type") or "").upper()

    # Payment estimates (rough, used in copy — not a commitment)
    monthly_pmt = None
    if loan_bal and rate:
        r = rate / 100 / 12
        n = 360  # 30yr
        if r > 0:
            monthly_pmt = round(loan_bal * (r * (1 + r) ** n) / ((1 + r) ** n - 1))

    new_rate_est = 6.75   # illustrative market rate used in copy
    new_monthly_pmt = None
    if loan_bal:
        r2 = new_rate_est / 100 / 12
        n = 360
        if r2 > 0:
            new_monthly_pmt = round(loan_bal * (r2 * (1 + r2) ** n) / ((1 + r2) ** n - 1))

    savings = None
    if monthly_pmt and new_monthly_pmt:
        savings = monthly_pmt - new_monthly_pmt

    p["_first"] = first
    p["_rate_str"] = f"{rate:.2f}%" if rate else None
    p["_equity_str"] = f"{equity_pct:.0f}%" if equity_pct else None
    p["_equity_dollar_str"] = f"${equity_dollars:,.0f}" if equity_dollars else None
    p["_prop_val_str"] = f"${prop_val:,.0f}" if prop_val else None
    p["_loan_bal_str"] = f"${loan_bal:,.0f}" if loan_bal else None
    p["_monthly_pmt_str"] = f"${monthly_pmt:,}" if monthly_pmt else None
    p["_new_pmt_str"] = f"${new_monthly_pmt:,}" if new_monthly_pmt else None
    p["_savings_str"] = f"${savings:,}" if savings and savings > 0 else None
    p["_loan_type"] = loan_type or "Conventional"
    p["_prop_addr_short"] = (p.get("property_address") or "").split(",")[0] or "your home"
    p["_new_rate_str"] = f"{new_rate_est:.2f}%"

    return p


# ── Static email sequence templates ──────────────────────────────────────────
# These are carefully crafted multi-touch sequences.
# AI generation is used to personalize — these are the base frameworks.

EMAIL_SEQUENCES = {

    "refi_rate_reduction": [
        {
            "step": 1,
            "subject_template": "Your {rate} rate — I ran the numbers",
            "intent": "soft touch, informational, no hard sell — just awareness",
            "tone": "friendly, direct, like a neighbor who happens to be a mortgage expert",
        },
        {
            "step": 2,
            "subject_template": "The math on your {addr} mortgage",
            "intent": "show the savings calculation — make it real with their specific numbers",
            "tone": "analytical but warm — data-backed but human",
        },
        {
            "step": 3,
            "subject_template": "Last look: rate review for {first}",
            "intent": "urgency without pressure — rates move, window closes",
            "tone": "direct, brief, respectful of their time",
        },
    ],

    "cash_out_equity": [
        {
            "step": 1,
            "subject_template": "You have {equity} sitting in {addr}",
            "intent": "equity awareness — make them feel wealthy and ready",
            "tone": "aspirational, empowering — they've built something",
        },
        {
            "step": 2,
            "subject_template": "What {equity} unlocks for you",
            "intent": "show real use cases: payoff debt, fund renovation, invest, education",
            "tone": "visionary but grounded — real money, real possibilities",
        },
        {
            "step": 3,
            "subject_template": "Equity access — still holding your spot",
            "intent": "light follow-up with social proof and simple CTA",
            "tone": "professional, low-pressure, value-forward",
        },
    ],

    "fha_streamline_watch": [
        {
            "step": 1,
            "subject_template": "FHA Streamline alert for your {addr} loan",
            "intent": "educate on FHA streamline — most don't know it exists",
            "tone": "expert advisor — you spotted something they probably missed",
        },
        {
            "step": 2,
            "subject_template": "No appraisal. No income docs. Your FHA refi.",
            "intent": "remove objections preemptively — it's easier than they think",
            "tone": "confident, clear, benefit-led",
        },
    ],

    "past_client_equity_review": [
        {
            "step": 1,
            "subject_template": "Your annual mortgage check-in, {first}",
            "intent": "relationship-based touch from their actual banker — annual review",
            "tone": "warm, personal, like a financial advisor to a valued client",
        },
        {
            "step": 2,
            "subject_template": "What's changed for your loan since we closed",
            "intent": "market update + their specific equity growth — celebrate it",
            "tone": "celebratory and informative — 'look how well you've done'",
        },
    ],

    "investor_refi": [
        {
            "step": 1,
            "subject_template": "DSCR refi analysis for {addr}",
            "intent": "straight talk to an investor — cash flow math, not fluff",
            "tone": "investor-to-investor, analytical, no hand-holding",
        },
        {
            "step": 2,
            "subject_template": "Pull equity from {addr} — use it on the next one",
            "intent": "portfolio growth angle — leverage existing equity for acquisition",
            "tone": "growth-minded, ambitious, peer level",
        },
    ],

    "realtor_partnership": [
        {
            "step": 1,
            "subject_template": "Mortgage intel for your buyers — no strings",
            "intent": "value-first intro — give before asking anything",
            "tone": "collegial, peer-to-peer, zero salesy vibes",
        },
        {
            "step": 2,
            "subject_template": "Why your buyers keep losing — and how I fix that",
            "intent": "pain point: buyers losing in this market because of weak pre-approvals",
            "tone": "bold, problem-solving, expert positioning",
        },
        {
            "step": 3,
            "subject_template": "Lunch? Coffee? 15 min Zoom? Your choice, {first}",
            "intent": "ask for the meeting — simple, flexible, no pressure",
            "tone": "casual, direct, confident",
        },
    ],

    "listing_agent_outreach": [
        {
            "step": 1,
            "subject_template": "Your {addr} listing — I have buyers",
            "intent": "property-specific intro — not generic spam, real intel",
            "tone": "direct, useful, time-sensitive",
        },
        {
            "step": 2,
            "subject_template": "How I help your sellers' buyers close faster",
            "intent": "offer value to the listing agent — their sellers want fast closes",
            "tone": "solution-focused, professional",
        },
    ],

    "dpa_education": [
        {
            "step": 1,
            "subject_template": "Did you know Maryland has $40K in free homebuyer money?",
            "intent": "DPA awareness — most buyers have no idea these programs exist",
            "tone": "friendly, educational, surprising — 'free money' angle",
        },
        {
            "step": 2,
            "subject_template": "You likely qualify for DPA — here's how it works",
            "intent": "demystify the process — remove fear, build trust",
            "tone": "supportive, clear, empowering",
        },
    ],

}


# ── Email body builders ───────────────────────────────────────────────────────

def _refi_email_html(p: dict, step: int) -> tuple[str, str]:
    """Returns (html, text) for refi rate reduction sequence."""
    first = p["_first"]
    rate_str = p["_rate_str"] or "your current rate"
    new_rate = p["_new_rate_str"]
    savings = p["_savings_str"]
    addr_short = p["_prop_addr_short"]
    equity = p["_equity_str"]
    booking = _BOOKING_URL
    phone = os.getenv("BANKER_PHONE", "")

    if step == 1:
        subject = f"Your {rate_str} rate — I ran the numbers"
        savings_line = (
            f"<p>With current market rates near <strong>{new_rate}</strong>, you could be saving "
            f"<strong>{savings}/month</strong> on your mortgage.</p>"
            if savings else
            f"<p>With rates shifting, there's a real chance your current mortgage has room to improve — "
            f"especially at a {rate_str} rate.</p>"
        )
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9f9f7;margin:0;padding:20px;color:#1f1f1f;}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.07);}}
  .header{{background:#1f1f1f;padding:28px 32px;}}
  .header h1{{color:#f5c87a;margin:0;font-size:20px;font-weight:700;letter-spacing:0.3px;}}
  .header p{{color:#aaa;margin:6px 0 0;font-size:13px;}}
  .body{{padding:32px;}}
  .body p{{line-height:1.7;color:#2d2d2d;margin:0 0 16px;}}
  .callout{{background:#fffbf2;border-left:4px solid #f5c87a;padding:16px 20px;border-radius:0 6px 6px 0;margin:24px 0;}}
  .callout strong{{color:#c8860a;font-size:18px;}}
  .btn{{display:inline-block;background:#1f1f1f;color:#f5c87a !important;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:700;font-size:15px;margin-top:8px;}}
  .footer{{background:#f0ece4;padding:20px 32px;font-size:11px;color:#888;line-height:1.6;}}
  .footer a{{color:#888;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>MortgageSesame</h1>
    <p>A personal note from {_BANKER_NAME}&nbsp;&nbsp;·&nbsp;&nbsp;NMLS #{_BANKER_NMLS}</p>
  </div>
  <div class="body">
    <p>Hi {first},</p>
    <p>I looked at your mortgage on <strong>{addr_short}</strong> and wanted to reach out directly.</p>
    {savings_line}
    <div class="callout">
      <p style="margin:0 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#999;">Current Estimated Rate</p>
      <strong>{rate_str}</strong>
    </div>
    <p>I'm not sending a generic blast — I specifically ran your numbers because the spread between your rate and today's market is meaningful enough to at least have a 15-minute conversation.</p>
    <p>No pressure, no commitment. Just a quick look at what's possible.</p>
    <a class="btn" href="{booking}">Book a 15-Minute Rate Review →</a>
    <p style="margin-top:24px;font-size:13px;color:#888;">Or just reply to this email and I'll reach out directly.</p>
  </div>
  <div class="footer">
    <p><strong>{_BANKER_NAME}</strong>&nbsp;&nbsp;|&nbsp;&nbsp;NMLS #{_BANKER_NMLS}&nbsp;&nbsp;|&nbsp;&nbsp;MortgageSesame<br>
    {"Phone: " + phone + "<br>" if phone else ""}
    This is an ADVERTISEMENT. All rates and payment estimates are illustrative and subject to change based on your specific loan profile, credit score, and market conditions at time of application. This is not a commitment to lend, a loan approval, or a guarantee of any rate or term. Equal Housing Lender.</p>
    <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
  </div>
</div>
</body>
</html>"""

        text = f"""Hi {first},

I looked at your mortgage on {addr_short} and wanted to reach out directly.

Your estimated rate: {rate_str}
{"Current market near: " + new_rate + ("  |  Potential savings: " + savings + "/mo" if savings else "") if p.get("_rate_str") else ""}

I specifically ran your numbers because there may be real savings available. No pressure — just a quick 15-minute review.

Book a time: {booking}

Or reply to this email and I'll reach out directly.

{_BANKER_NAME} | NMLS #{_BANKER_NMLS} | MortgageSesame

ADVERTISEMENT. Rates/payments are illustrative. Not a commitment to lend. Equal Housing Lender.
Unsubscribe: {{unsubscribe_url}}"""

    elif step == 2:
        subject = f"The math on your {addr_short} mortgage"
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9f9f7;margin:0;padding:20px;color:#1f1f1f;}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.07);}}
  .header{{background:#1f1f1f;padding:28px 32px;}}
  .header h1{{color:#f5c87a;margin:0;font-size:20px;font-weight:700;}}
  .header p{{color:#aaa;margin:6px 0 0;font-size:13px;}}
  .body{{padding:32px;}}
  .body p{{line-height:1.7;color:#2d2d2d;margin:0 0 16px;}}
  .math-table{{width:100%;border-collapse:collapse;margin:24px 0;}}
  .math-table td{{padding:12px 16px;border-bottom:1px solid #f0ede6;font-size:15px;}}
  .math-table tr:last-child td{{border-bottom:none;}}
  .math-table td:first-child{{color:#888;font-size:13px;}}
  .math-table td:last-child{{text-align:right;font-weight:700;color:#1f1f1f;}}
  .highlight-row td{{background:#fffbf2;}}
  .highlight-row td:last-child{{color:#c8860a;font-size:18px;}}
  .btn{{display:inline-block;background:#1f1f1f;color:#f5c87a !important;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:700;font-size:15px;margin-top:8px;}}
  .footer{{background:#f0ece4;padding:20px 32px;font-size:11px;color:#888;line-height:1.6;}}
  .footer a{{color:#888;}}
  .disclaimer{{font-size:11px;color:#aaa;margin-top:20px;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>Rate Review — {addr_short}</h1>
    <p>Illustrative analysis&nbsp;&nbsp;·&nbsp;&nbsp;NMLS #{_BANKER_NMLS}</p>
  </div>
  <div class="body">
    <p>Hi {first},</p>
    <p>Quick follow-up. Here's what the numbers look like side by side (based on public records and estimated values):</p>
    <table class="math-table">
      <tr><td>Estimated Loan Balance</td><td>{p.get("_loan_bal_str") or "See note below"}</td></tr>
      <tr><td>Current Est. Rate</td><td>{rate_str}</td></tr>
      <tr><td>Current Est. Payment</td><td>{p.get("_monthly_pmt_str") or "—"}</td></tr>
      <tr><td>Illustrative New Rate</td><td>{new_rate}*</td></tr>
      <tr><td>Illustrative New Payment</td><td>{p.get("_new_pmt_str") or "—"}</td></tr>
      <tr class="highlight-row"><td><strong>Potential Monthly Savings</strong></td><td>{p.get("_savings_str") or "Request your review"}</td></tr>
    </table>
    <p>These numbers aren't a quote — they're based on public records. Your actual savings could be higher or lower depending on your full profile. That's why I want to do a real review.</p>
    <a class="btn" href="{booking}">Get My Actual Numbers →</a>
    <p class="disclaimer">*Rate shown is illustrative current market estimate. Not a rate lock or commitment. Actual rate based on credit, LTV, and market conditions at application.</p>
  </div>
  <div class="footer">
    <p>{_BANKER_NAME}&nbsp;|&nbsp;NMLS #{_BANKER_NMLS}&nbsp;|&nbsp;MortgageSesame<br>
    ADVERTISEMENT. Not a commitment to lend. Equal Housing Lender.</p>
    <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
  </div>
</div>
</body>
</html>"""

        text = f"""Hi {first},

Here's the quick breakdown on {addr_short}:

Estimated Balance:    {p.get("_loan_bal_str") or "—"}
Current Est. Rate:    {rate_str}
Current Est. Payment: {p.get("_monthly_pmt_str") or "—"}
Illustrative New Rate: {new_rate}
Illustrative Payment:  {p.get("_new_pmt_str") or "—"}
Potential Savings:     {p.get("_savings_str") or "Request your review"}

These aren't a quote — they're estimates from public records. Your real savings could be different. Get the actual numbers: {booking}

{_BANKER_NAME} | NMLS #{_BANKER_NMLS} | MortgageSesame
ADVERTISEMENT. Not a commitment to lend. Equal Housing Lender.
Unsubscribe: {{unsubscribe_url}}"""

    else:  # step 3 — final touch
        subject = f"Last look: rate review for {first}"
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9f9f7;margin:0;padding:20px;}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.07);}}
  .header{{background:#1f1f1f;padding:24px 32px;}}
  .header h1{{color:#f5c87a;margin:0;font-size:18px;font-weight:700;}}
  .body{{padding:32px;color:#2d2d2d;line-height:1.7;}}
  .body p{{margin:0 0 16px;}}
  .btn{{display:inline-block;background:#c8860a;color:#fff !important;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:700;font-size:15px;}}
  .footer{{background:#f0ece4;padding:16px 32px;font-size:11px;color:#888;}}
  .footer a{{color:#888;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header"><h1>Final note — {first}</h1></div>
  <div class="body">
    <p>{first},</p>
    <p>I've reached out a couple of times about your rate on {addr_short}. I know you're busy, and I respect your time — so this is the last note I'll send unless I hear from you.</p>
    <p>If the timing isn't right, no problem at all. Rates change and when you're ready, I'm here.</p>
    <p>If now is actually a good time and you've just been meaning to get to it — this is your nudge. Takes 15 minutes and you'll know exactly where you stand.</p>
    <a class="btn" href="{booking}">Schedule 15 Minutes →</a>
    <p style="margin-top:24px;font-size:13px;color:#999;">Or call/text me directly{(": " + phone) if phone else "."}</p>
  </div>
  <div class="footer">
    <p>{_BANKER_NAME}&nbsp;|&nbsp;NMLS #{_BANKER_NMLS}&nbsp;|&nbsp;MortgageSesame&nbsp;|&nbsp;Equal Housing Lender. ADVERTISEMENT.</p>
    <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
  </div>
</div>
</body>
</html>"""

        text = f"""{first},

I've reached out about your rate on {addr_short}. This is my last note unless I hear from you.

If the timing isn't right — no problem. When you're ready, I'm here.

If now is actually the time — it's a 15-minute call. You'll know exactly where you stand.

Schedule here: {booking}
{"Call/text: " + phone if phone else ""}

{_BANKER_NAME} | NMLS #{_BANKER_NMLS}
ADVERTISEMENT. Equal Housing Lender.
Unsubscribe: {{unsubscribe_url}}"""

    return subject, html, text


def _equity_email_html(p: dict, step: int) -> tuple[str, str, str]:
    first = p["_first"]
    equity_str = p["_equity_dollar_str"] or (p["_equity_str"] + " equity" if p["_equity_str"] else "significant equity")
    equity_pct = p["_equity_str"] or ""
    addr_short = p["_prop_addr_short"]
    booking = _BOOKING_URL
    phone = os.getenv("BANKER_PHONE", "")

    if step == 1:
        subject = f"You have {equity_str} sitting in {addr_short}"
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9f9f7;margin:0;padding:20px;color:#1f1f1f;}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.07);}}
  .header{{background:linear-gradient(135deg,#1f1f1f 60%,#2d2d1a);padding:32px;text-align:center;}}
  .header .equity-num{{color:#f5c87a;font-size:42px;font-weight:800;letter-spacing:-1px;margin:0;}}
  .header .equity-label{{color:#aaa;font-size:13px;text-transform:uppercase;letter-spacing:2px;margin:8px 0 0;}}
  .body{{padding:32px;}}
  .body p{{line-height:1.7;color:#2d2d2d;margin:0 0 16px;}}
  .use-list{{list-style:none;padding:0;margin:20px 0;}}
  .use-list li{{padding:10px 16px;border-left:3px solid #f5c87a;margin-bottom:8px;background:#fffbf2;border-radius:0 4px 4px 0;font-size:14px;}}
  .use-list li strong{{color:#c8860a;}}
  .btn{{display:inline-block;background:#1f1f1f;color:#f5c87a !important;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:700;font-size:15px;margin-top:8px;}}
  .footer{{background:#f0ece4;padding:20px 32px;font-size:11px;color:#888;}}
  .footer a{{color:#888;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="equity-num">{equity_str}</div>
    <div class="equity-label">Estimated Equity in {addr_short}</div>
  </div>
  <div class="body">
    <p>Hi {first},</p>
    <p>That{(" " + equity_pct + " equity") if equity_pct else " equity"} in your home isn't just a number on a statement. It's working capital — if you know how to use it.</p>
    <p>Here's what homeowners in your position are doing with theirs:</p>
    <ul class="use-list">
      <li><strong>Eliminate high-interest debt</strong> — credit cards at 24% vs. home equity at 7%</li>
      <li><strong>Fund a major renovation</strong> — add value while pulling equity</li>
      <li><strong>Down payment on investment property</strong> — use equity to build a portfolio</li>
      <li><strong>College tuition / major purchase</strong> — flexible access, favorable rate</li>
      <li><strong>Emergency liquidity</strong> — HELOC as a low-cost safety net</li>
    </ul>
    <p>I can show you exactly how much you can access, what it would cost, and whether a cash-out refi or HELOC makes more sense for your situation.</p>
    <a class="btn" href="{booking}">Explore My Equity Options →</a>
  </div>
  <div class="footer">
    <p>{_BANKER_NAME}&nbsp;|&nbsp;NMLS #{_BANKER_NMLS}&nbsp;|&nbsp;MortgageSesame<br>
    ADVERTISEMENT. Equity estimates based on estimated property values and public records. Not a commitment to lend. Actual loan terms subject to credit approval and market conditions. Equal Housing Lender.</p>
    <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
  </div>
</div>
</body>
</html>"""

        text = f"""Hi {first},

{equity_str} — that's what your equity in {addr_short} looks like.

That equity isn't just a number. Here's what homeowners are doing with it:
• Eliminate high-interest debt (24% credit card → 7% home equity)
• Fund renovations that add value
• Down payment on an investment property
• College / major purchases at favorable rates
• HELOC as low-cost emergency liquidity

I can show you exactly how much you can access and the best structure for your situation.

Book a review: {booking}

{_BANKER_NAME} | NMLS #{_BANKER_NMLS} | MortgageSesame
ADVERTISEMENT. Equity estimates are illustrative. Not a commitment to lend. Equal Housing Lender.
Unsubscribe: {{unsubscribe_url}}"""

    else:  # step 2+
        subject = f"What {equity_str} unlocks for you"
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9f9f7;margin:0;padding:20px;}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.07);}}
  .header{{background:#1f1f1f;padding:28px 32px;}}
  .header h1{{color:#f5c87a;margin:0;font-size:20px;}}
  .body{{padding:32px;color:#2d2d2d;line-height:1.7;}}
  .body p{{margin:0 0 16px;}}
  .compare{{display:table;width:100%;margin:20px 0;border-collapse:collapse;}}
  .compare-row{{display:table-row;}}
  .compare-cell{{display:table-cell;padding:12px 16px;border-bottom:1px solid #f0ede6;}}
  .btn{{display:inline-block;background:#c8860a;color:#fff !important;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:700;font-size:15px;margin-top:8px;}}
  .footer{{background:#f0ece4;padding:16px 32px;font-size:11px;color:#888;}}
  .footer a{{color:#888;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header"><h1>Your equity — two ways to access it</h1></div>
  <div class="body">
    <p>{first},</p>
    <p>Following up on your {addr_short} equity. There are two main tools — here's the quick difference:</p>
    <p><strong>Cash-Out Refinance</strong><br>
    Replace your current mortgage with a new one at a higher balance. Get the difference in cash at closing. One payment. Good if you want a fixed, predictable cost.</p>
    <p><strong>HELOC (Home Equity Line of Credit)</strong><br>
    A revolving credit line secured by your home. Draw what you need, when you need it. Pay interest only on what you use. Good for ongoing access or if you're not sure of the exact amount.</p>
    <p>Which is right for you depends on your current rate, your goal, and your timeline. That's the 15-minute conversation.</p>
    <a class="btn" href="{booking}">Find Out Which One I'd Recommend →</a>
  </div>
  <div class="footer">
    <p>{_BANKER_NAME}&nbsp;|&nbsp;NMLS #{_BANKER_NMLS}&nbsp;|&nbsp;MortgageSesame&nbsp;|&nbsp;ADVERTISEMENT. Equal Housing Lender.</p>
    <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
  </div>
</div>
</body>
</html>"""

        text = f"""{first},

Two ways to access your {equity_str} in {addr_short}:

CASH-OUT REFINANCE — Replace your mortgage, pull equity as cash at closing.
HELOC — Revolving credit line. Draw when you need it, pay interest only on what you use.

Which is right for you? Depends on your rate, goal, and timeline.

Let's figure it out together: {booking}

{_BANKER_NAME} | NMLS #{_BANKER_NMLS} | MortgageSesame
ADVERTISEMENT. Equal Housing Lender.
Unsubscribe: {{unsubscribe_url}}"""

    return subject, html, text


def _realtor_email_html(p: dict, step: int) -> tuple[str, str, str]:
    first = p["_first"]
    company = p.get("company_name") or "your brokerage"
    booking = _BOOKING_URL
    phone = os.getenv("BANKER_PHONE", "")

    if step == 1:
        subject = "Mortgage intel for your buyers — no strings"
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9f9f7;margin:0;padding:20px;}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.07);}}
  .header{{background:#1f1f1f;padding:28px 32px;}}
  .header h1{{color:#f5c87a;margin:0;font-size:20px;}}
  .header p{{color:#aaa;margin:6px 0 0;font-size:13px;}}
  .body{{padding:32px;color:#2d2d2d;line-height:1.7;}}
  .body p{{margin:0 0 16px;}}
  .value-list{{list-style:none;padding:0;margin:16px 0;}}
  .value-list li{{padding:8px 0 8px 20px;position:relative;border-bottom:1px solid #f5f2ea;font-size:14px;}}
  .value-list li::before{{content:"→";position:absolute;left:0;color:#f5c87a;font-weight:700;}}
  .btn{{display:inline-block;background:#1f1f1f;color:#f5c87a !important;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:700;font-size:15px;margin-top:8px;}}
  .footer{{background:#f0ece4;padding:16px 32px;font-size:11px;color:#888;}}
  .footer a{{color:#888;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>Hey {first} — quick note from {_BANKER_NAME}</h1>
    <p>NMLS #{_BANKER_NMLS}&nbsp;&nbsp;·&nbsp;&nbsp;MortgageSesame</p>
  </div>
  <div class="body">
    <p>I'm a local mortgage banker in Maryland/DC and I wanted to reach out to agents at {company}.</p>
    <p>Not a pitch. Just want to offer a few things that cost you nothing but might help your buyers:</p>
    <ul class="value-list">
      <li>Same-day pre-approvals (real credit pull, not soft)</li>
      <li>DPA program matches — I know every MD/DC program cold</li>
      <li>Underwriting in-house — no broker delays, no surprises at the table</li>
      <li>I answer my phone. At 8pm before a showing. Seriously.</li>
    </ul>
    <p>If you have a buyer in the pipeline who's struggling to get solid financing — let me take a look. No obligation, no poaching. Just a second opinion.</p>
    <a class="btn" href="{booking}">Grab 15 minutes with me →</a>
  </div>
  <div class="footer">
    <p>{_BANKER_NAME}&nbsp;|&nbsp;NMLS #{_BANKER_NMLS}&nbsp;|&nbsp;MortgageSesame{"&nbsp;|&nbsp;" + phone if phone else ""}</p>
    <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
  </div>
</div>
</body>
</html>"""

        text = f"""Hey {first},

I'm {_BANKER_NAME} — local mortgage banker in MD/DC. Reaching out to agents at {company}.

What I offer your buyers (at no cost to you):
→ Same-day pre-approvals (real credit pull)
→ Every MD/DC DPA program — I know them cold
→ Underwriting in-house — no delays
→ I answer my phone. 8pm before a showing. Seriously.

Have a buyer struggling with financing? Let me take a look.

{booking}

{_BANKER_NAME} | NMLS #{_BANKER_NMLS} | MortgageSesame{"  |  " + phone if phone else ""}
Unsubscribe: {{unsubscribe_url}}"""

    elif step == 2:
        subject = "Why your buyers keep losing — and how I fix that"
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9f9f7;margin:0;padding:20px;}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.07);}}
  .header{{background:#1f1f1f;padding:28px 32px;}}
  .header h1{{color:#f5c87a;margin:0;font-size:19px;font-weight:700;}}
  .body{{padding:32px;color:#2d2d2d;line-height:1.7;}}
  .body p{{margin:0 0 16px;}}
  .pain-box{{background:#fff8f0;border:1px solid #f5c87a;border-radius:6px;padding:20px 24px;margin:20px 0;}}
  .pain-box h3{{margin:0 0 12px;font-size:15px;color:#c8860a;}}
  .pain-box p{{margin:0;font-size:14px;color:#555;}}
  .btn{{display:inline-block;background:#1f1f1f;color:#f5c87a !important;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:700;font-size:15px;margin-top:8px;}}
  .footer{{background:#f0ece4;padding:16px 32px;font-size:11px;color:#888;}}
  .footer a{{color:#888;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="header"><h1>{first}, three reasons buyers lose in this market</h1></div>
  <div class="body">
    <p>Following up from last week. Here's what I see killing deals for buyers right now:</p>
    <div class="pain-box">
      <h3>1. Pre-approval letters that don't mean anything</h3>
      <p>Online lenders issue soft-pull "pre-approvals" in 60 seconds. Sellers' agents know the difference. Mine is a full credit pull with income verified. It holds.</p>
    </div>
    <div class="pain-box">
      <h3>2. No strategy around rate buydowns</h3>
      <p>Seller concession toward a 2-1 buydown can close the gap between what a buyer can afford today and what they need. Most loan officers don't structure this proactively.</p>
    </div>
    <div class="pain-box">
      <h3>3. DPA left on the table</h3>
      <p>Maryland has programs with up to $40K in assistance. Most agents don't know which buyers qualify. I do this every day — I'll tell you in 5 minutes if your buyer qualifies.</p>
    </div>
    <p>This is the difference between a buyer who loses 3 offers and a buyer who closes.</p>
    <a class="btn" href="{booking}">Let's talk about your buyer pipeline →</a>
  </div>
  <div class="footer">
    <p>{_BANKER_NAME}&nbsp;|&nbsp;NMLS #{_BANKER_NMLS}&nbsp;|&nbsp;MortgageSesame. Equal Housing Lender.</p>
    <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
  </div>
</div>
</body>
</html>"""

        text = f"""{first},

Three reasons buyers lose in this market:

1. Weak pre-approvals — soft-pull letters don't hold. Mine is full credit pull, income verified.
2. No rate buydown strategy — seller concessions structured as buydowns can close the affordability gap.
3. DPA left on the table — MD has up to $40K available. Most agents don't know who qualifies. I do.

This is the difference between losing 3 offers and closing.

Let's talk about your pipeline: {booking}

{_BANKER_NAME} | NMLS #{_BANKER_NMLS} | MortgageSesame. Equal Housing Lender.
Unsubscribe: {{unsubscribe_url}}"""

    else:
        subject = f"Lunch? Coffee? 15-min Zoom? Your choice, {first}"
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject}</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f9f9f7;margin:0;padding:20px;}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.07);}}
  .body{{padding:40px 32px;color:#2d2d2d;line-height:1.8;}}
  .body p{{margin:0 0 16px;}}
  .btn{{display:inline-block;background:#c8860a;color:#fff !important;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:700;font-size:15px;margin-top:8px;}}
  .footer{{background:#f0ece4;padding:16px 32px;font-size:11px;color:#888;}}
  .footer a{{color:#888;}}
</style>
</head>
<body>
<div class="wrap">
  <div class="body">
    <p>{first},</p>
    <p>Last note — promise.</p>
    <p>I'd love to grab 15 minutes — Zoom, phone, coffee, whatever works for you. No agenda beyond getting to know each other and seeing if there's a fit.</p>
    <p>If not, no worries. But if you ever have a buyer who needs a strong lender in their corner — you'll know exactly who to call.</p>
    <a class="btn" href="{booking}">Pick a time that works →</a>
    {"<p style='margin-top:20px;font-size:14px;'>Or text me: " + phone + "</p>" if phone else ""}
  </div>
  <div class="footer">
    <p>{_BANKER_NAME}&nbsp;|&nbsp;NMLS #{_BANKER_NMLS}&nbsp;|&nbsp;MortgageSesame. Equal Housing Lender.</p>
    <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
  </div>
</div>
</body>
</html>"""

        text = f"""{first},

Last note — promise.

15 minutes. Zoom, phone, coffee — whatever works.

Pick a time: {booking}
{"Text: " + phone if phone else ""}

{_BANKER_NAME} | NMLS #{_BANKER_NMLS}
Unsubscribe: {{unsubscribe_url}}"""

    return subject, html, text


# ── SMS Templates ─────────────────────────────────────────────────────────────

SMS_TEMPLATES = {

    "refi_rate_reduction": {
        1: (
            "Hi {first}, this is {_BANKER_NAME} — mortgage banker NMLS#{_BANKER_NMLS}. "
            "I pulled your loan on {addr_short} and think there's real savings available. "
            "Mind if I share? (Reply STOP to opt out)"
        ),
        2: (
            "{_BANKER_NAME} here — wanted to follow up on {addr_short}. "
            "Quick math: {rate_str} rate → potential {savings_str}/mo savings. "
            "Worth 15 min? {booking}"
        ),
        3: (
            "Last note from {_BANKER_NAME} re: {addr_short}. "
            "If now's not the right time, no worries. "
            "When you're ready: {booking}"
        ),
    },

    "cash_out_equity": {
        1: (
            "Hi {first}, {_BANKER_NAME} (NMLS#{_BANKER_NMLS}) here. "
            "You have an estimated {equity_str} in {addr_short}. "
            "I can show you how to access it — no obligation. "
            "Interested? (Reply STOP to opt out)"
        ),
        2: (
            "{_BANKER_NAME} following up — HELOC or cash-out refi on {addr_short}? "
            "I can show you both options in 15 min: {booking}"
        ),
    },

    "investor_refi": {
        1: (
            "Kenneth here (NMLS#{_BANKER_NMLS}) — I specialize in DSCR loans for investors. "
            "Saw {addr_short} in your portfolio. "
            "There may be better cash flow available. Worth a quick look? (Reply STOP to opt out)"
        ),
    },

    "realtor_partnership": {
        1: (
            "Hi {first}, {_BANKER_NAME} from MortgageSesame (NMLS#{_BANKER_NMLS}). "
            "Local lender, same-day pre-approvals, know every MD/DC DPA program. "
            "Good time to connect? (Reply STOP to opt out)"
        ),
        2: (
            "{_BANKER_NAME} here — I help realtors close faster with stronger buyer pre-approvals. "
            "Have a buyer struggling? Let me take a look: {booking}"
        ),
    },

    "fha_streamline_watch": {
        1: (
            "Hi {first}, {_BANKER_NAME} (NMLS#{_BANKER_NMLS}). "
            "You have an FHA loan on {addr_short} — you may qualify for a streamline refi. "
            "No appraisal needed. Worth checking: {booking} (Reply STOP to opt out)"
        ),
    },

}


# ── Call Script Builder ───────────────────────────────────────────────────────

def _build_call_script(p: dict, trigger: str = "cold", campaign_type: str = "refi_rate_reduction") -> CallScript:
    first = p["_first"]
    addr_short = p["_prop_addr_short"]
    rate_str = p["_rate_str"] or "your current rate"
    equity_str = p["_equity_dollar_str"] or p["_equity_str"] or "significant equity"
    savings_str = p["_savings_str"] or "meaningful savings"
    booking = _BOOKING_URL

    # Opener varies by trigger
    if trigger == "qr_scan":
        opener = (
            f"Hi, may I speak with {first}? ... Hi {first}, this is {_BANKER_NAME} — I'm the mortgage banker "
            f"who sent you the mail piece about {addr_short}. I see you scanned the QR code, which means "
            f"the numbers resonated. Did you get a chance to look at it? ... Great — I wanted to make sure "
            f"you had a chance to talk through it with a real person."
        )
    elif trigger == "form_fill":
        opener = (
            f"Hi {first}, this is {_BANKER_NAME} — you filled out a quick form on our site and wanted to connect. "
            f"Thanks for reaching out. I see your home is on {addr_short}. Is this a good time for just a "
            f"few minutes?"
        )
    elif trigger == "email_reply":
        opener = (
            f"Hi {first}, {_BANKER_NAME} here — you replied to my email about your mortgage on {addr_short}. "
            f"I wanted to follow up right away. Do you have a couple of minutes to talk?"
        )
    else:  # cold
        opener = (
            f"Hi, is this {first}? ... Hi {first}, this is {_BANKER_NAME} — I'm a mortgage banker in the area. "
            f"The reason I'm calling is I did an analysis on {addr_short} and I think there's a real "
            f"opportunity to improve your mortgage terms. Do you have two minutes?"
        )

    if campaign_type in ("refi_rate_reduction", "fha_streamline_watch"):
        pitch = (
            f"Based on public records, I see your current rate is around {rate_str} on {addr_short}. "
            f"With where rates sit today, there's a real possibility of {savings_str} per month in savings. "
            f"Now I want to be clear — I haven't pulled your credit or done a full application. "
            f"What I want to do is a 10-minute review — look at your full picture, give you an actual "
            f"number, not an estimate — and if it makes sense, we can talk about next steps. "
            f"If it doesn't pencil out, I'll tell you straight. No fluff."
        )
    elif campaign_type in ("cash_out_equity", "past_client_equity_review"):
        pitch = (
            f"I ran the numbers on {addr_short} and you've built up an estimated {equity_str} in equity. "
            f"A lot of homeowners don't realize that equity is accessible — and at a much better rate "
            f"than credit cards or personal loans. I wanted to reach out personally and walk you through "
            f"the options — a HELOC, a cash-out refi — and help you decide which one makes sense for "
            f"your situation, if any. It's a 15-minute conversation."
        )
    elif campaign_type in ("investor_refi", "dscr"):
        pitch = (
            f"I work with a lot of real estate investors in the MD/DC area and specialize in DSCR loans — "
            f"those are debt-service coverage ratio loans that qualify based on the property's income, "
            f"not your personal income. I pulled some data on {addr_short} and wanted to see if there's "
            f"an opportunity to improve cash flow or pull equity out for your next acquisition. "
            f"Do you have five minutes to walk through the numbers?"
        )
    elif campaign_type in ("realtor_partnership", "listing_agent_outreach"):
        pitch = (
            f"I work with agents in the MD/DC market and I specialize in getting buyers across the "
            f"finish line — same-day pre-approvals, DPA program expertise, in-house underwriting. "
            f"I wanted to introduce myself because I know buyers in this market lose deals when their "
            f"lender isn't sharp. I'd love to be a resource for you. Do you have any buyers in the "
            f"pipeline right now?"
        )
    else:
        pitch = (
            f"I analyzed your property at {addr_short} and wanted to share what I found. "
            f"There may be a real financial opportunity based on your current mortgage structure. "
            f"Can I share the details? It'll take two minutes."
        )

    talking_points = []
    if campaign_type in ("refi_rate_reduction", "fha_streamline_watch"):
        talking_points = [
            f"Current rate {rate_str} vs. market today — {savings_str}/mo savings estimate",
            "Full-credit pre-approval in same day — not a soft pull gimmick",
            "FHA Streamline: no appraisal, no income docs needed (if FHA loan)",
            "Closing costs can be rolled into loan — minimal out of pocket",
            "I underwrite in-house — faster close, no broker delays",
        ]
    elif campaign_type in ("cash_out_equity", "past_client_equity_review"):
        talking_points = [
            f"Estimated {equity_str} accessible in {addr_short}",
            "HELOC: revolving credit line, pay interest only on what you draw",
            "Cash-out refi: one loan, one payment, pull equity as lump sum",
            "Home equity rates typically lower than credit card, personal loan, student loan",
            "Tax implications: consult your CPA — mortgage interest often deductible",
        ]
    elif campaign_type in ("investor_refi", "dscr"):
        talking_points = [
            "DSCR loans qualify on property income, not W-2 — better for investors",
            "Pull equity from existing property for next acquisition",
            "Rate/term refi can improve monthly cash flow",
            "30-year fixed available on investment properties via DSCR",
            "No limit on number of properties with DSCR structure",
        ]
    elif campaign_type in ("realtor_partnership", "listing_agent_outreach"):
        talking_points = [
            "Same-day pre-approvals — full credit pull, not soft-pull theater",
            "Every MD/DC DPA program — I'll tell you in 5 min if buyer qualifies",
            "2-1 buydown structures using seller concessions",
            "In-house underwriting — no 3rd-party delays",
            "I answer my phone — 8pm, weekends, before showings",
        ]

    objections = {
        "I'm happy with my current lender": (
            "That's great — if you're locked in and the rate makes sense, there may be nothing to do. "
            "I'm not trying to move you just to move you. But I'd love 10 minutes just to see if there's "
            "actually savings available. If I can't beat your current deal, I'll tell you straight."
        ),
        "I just refinanced": (
            "Completely understand — if it was recent, the numbers probably won't work yet. "
            "When did you close? ... If it was more than 18 months ago, it might still be worth a "
            "quick look, especially if rates come down. If it was in the last 12 months, you're probably "
            "right — let's revisit in the fall."
        ),
        "I'm not looking to move / sell": (
            "I hear you — I'm not talking about buying or selling. This is strictly about your current "
            "mortgage. Refinancing or accessing equity doesn't require you to move at all. You stay put, "
            "your mortgage just works harder for you."
        ),
        "I don't have time right now": (
            "Totally get it. I have a link where you can grab 15 minutes whenever it works for you — "
            f"even Saturday morning or evenings. {booking} — or I can send a text link too."
        ),
        "How did you get my number": (
            "Completely fair question. I work from public property records — your name and address are "
            "part of the public deed filing. I use that data professionally to identify homeowners who "
            "may benefit from a conversation. If you'd like to opt out of future contact, I'll remove "
            "you right now — just say the word and you'll never hear from me again."
        ),
    }

    close = (
        f"So here's what I'd suggest — let me do a full review, no cost obviously, no obligation. "
        f"I'll look at your actual loan profile and give you a real number. If it makes sense, great. "
        f"If not, at least you'll know. Can I schedule 15 minutes with you — I have time this week. "
        f"Or you can grab a slot here: {booking}"
    )

    voicemail = (
        f"Hi {first}, this is {_BANKER_NAME} — I'm a mortgage banker and I wanted to reach out about "
        f"your property at {addr_short}. I've done some analysis that I think is worth sharing. "
        f"Please give me a call back at your convenience — or you can schedule a quick call "
        f"at {booking}. Again, this is {_BANKER_NAME}, NMLS #{_BANKER_NMLS}. Thanks."
    )

    return CallScript(
        opener=opener,
        pitch=pitch,
        talking_points=talking_points,
        objection_handlers=objections,
        close=close,
        voicemail=voicemail,
        trigger=trigger,
    )


# ── CampaignWriter class ──────────────────────────────────────────────────────

class CampaignWriter:
    """
    Main interface for generating campaign content.
    All methods work synchronously (static templates) with optional AI enhancement.
    AI enhancement requires OPENAI_API_KEY to be set.
    """

    def __init__(self):
        self.ai_enabled = bool(os.getenv("OPENAI_API_KEY"))

    async def generate_email(
        self,
        prospect,
        campaign_type: str = "refi_rate_reduction",
        step: int = 1,
    ) -> EmailDraft:
        """Generate an email for a prospect based on campaign type and sequence step."""
        p = _prospect_ctx(prospect)

        if campaign_type in ("refi_rate_reduction", "fha_streamline_watch"):
            subject, html, text = _refi_email_html(p, step)
        elif campaign_type in ("cash_out_equity", "past_client_equity_review"):
            subject, html, text = _equity_email_html(p, step)
        elif campaign_type in ("realtor_partnership", "listing_agent_outreach", "title_partner_outreach"):
            subject, html, text = _realtor_email_html(p, step)
        elif campaign_type == "investor_refi":
            subject, html, text = _equity_email_html(p, step)  # investor uses equity angle
        else:
            # Fallback to refi sequence for unknown types
            subject, html, text = _refi_email_html(p, step)

        # Wire real unsubscribe URL
        email_addr = p.get("email", "")
        unsub = _unsubscribe_url(email_addr) if email_addr else "#unsubscribe"
        html = html.replace("{{unsubscribe_url}}", unsub)
        text = text.replace("{{unsubscribe_url}}", unsub)

        draft = EmailDraft(
            subject=subject,
            body_html=html,
            body_text=text,
            merge_data=p,
            campaign_type=campaign_type,
            step=step,
        )

        if self.ai_enabled:
            draft = await self._ai_enhance_email(draft, p, campaign_type, step)

        return draft

    async def generate_sms(
        self,
        prospect,
        campaign_type: str = "refi_rate_reduction",
        step: int = 1,
    ) -> SmsDraft:
        """Generate an SMS message. Respects TCPA — always consent-gated before send."""
        p = _prospect_ctx(prospect)
        booking = _BOOKING_URL

        templates = SMS_TEMPLATES.get(campaign_type, SMS_TEMPLATES["refi_rate_reduction"])
        template = templates.get(step, templates.get(1, ""))

        body = template.format(
            first=p["_first"],
            addr_short=p["_prop_addr_short"],
            rate_str=p["_rate_str"] or "your current rate",
            savings_str=p["_savings_str"] or "potential savings",
            equity_str=p["_equity_dollar_str"] or p["_equity_str"] or "significant equity",
            booking=booking,
        )

        return SmsDraft(body=body, campaign_type=campaign_type, step=step)

    async def generate_call_script(
        self,
        prospect,
        trigger: str = "cold",
        campaign_type: str = "refi_rate_reduction",
    ) -> CallScript:
        """Generate a call script with talking points and objection handlers."""
        p = _prospect_ctx(prospect)
        return _build_call_script(p, trigger=trigger, campaign_type=campaign_type)

    async def generate_mail_merge_data(
        self,
        prospect,
        template_key: str = "equity_voucher",
        qr_url: str = "",
        qr_code: str = "",
    ) -> dict:
        """Build the merge data dict for a direct mail template."""
        p = _prospect_ctx(prospect)
        booking = _BOOKING_URL
        phone = os.getenv("BANKER_PHONE", "")

        return {
            "recipient_name": p.get("full_name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or "Homeowner",
            "property_address": p.get("property_address") or p.get("mailing_address") or "",
            "estimated_equity": p["_equity_str"] or "",
            "estimated_equity_dollars": p["_equity_dollar_str"] or "",
            "current_rate": p["_rate_str"] or "",
            "current_payment": p["_monthly_pmt_str"] or "",
            "new_rate": p["_new_rate_str"],
            "new_payment": p["_new_pmt_str"] or "",
            "monthly_savings": p["_savings_str"] or "",
            "loan_type": p["_loan_type"],
            "qr_url": qr_url or booking,
            "qr_code": qr_code,
            "booking_url": booking,
            "phone": phone,
            "nmls": _BANKER_NMLS,
            "banker_name": _BANKER_NAME,
            "template_key": template_key,
        }

    async def get_sequence_info(self, campaign_type: str) -> dict:
        """Return metadata about the email sequence for a campaign type."""
        seq = EMAIL_SEQUENCES.get(campaign_type, [])
        return {
            "campaign_type": campaign_type,
            "total_steps": len(seq),
            "steps": seq,
        }

    async def _ai_enhance_email(
        self,
        draft: EmailDraft,
        p: dict,
        campaign_type: str,
        step: int,
    ) -> EmailDraft:
        """
        Optional AI enhancement — personalize subject line and opening paragraph.
        Falls back gracefully if OpenAI is unavailable.
        """
        try:
            import httpx

            model = os.getenv("AI_FAST_MODEL", "gpt-4o-mini")
            api_key = os.getenv("OPENAI_API_KEY", "")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

            seq_info = EMAIL_SEQUENCES.get(campaign_type, [{}])[step - 1] if step <= len(EMAIL_SEQUENCES.get(campaign_type, [])) else {}
            intent = seq_info.get("intent", "")
            tone = seq_info.get("tone", "")

            system_prompt = (
                "You are an elite mortgage sales copywriter. You write email subject lines "
                "and opening paragraphs that feel personal, specific, and genuinely useful — "
                "never generic, never salesy, never pushy. You write to real people who have "
                "real financial situations. You know their rate, their equity, their address. "
                "Use that. Maximum 2 sentences for the opener. Never use exclamation points."
            )

            user_prompt = (
                f"Improve this email subject line and opening paragraph:\n\n"
                f"Current subject: {draft.subject}\n"
                f"Prospect: {p.get('_first')}, property {p.get('_prop_addr_short')}, "
                f"rate {p.get('_rate_str', 'unknown')}, equity {p.get('_equity_str', 'unknown')}\n"
                f"Campaign: {campaign_type}, step {step}\n"
                f"Intent: {intent}\nTone: {tone}\n\n"
                f"Return JSON only: {{\"subject\": \"...\", \"opener\": \"...\"}}"
            )

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 200,
                    },
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    enhanced = json.loads(content)
                    if enhanced.get("subject"):
                        draft.subject = enhanced["subject"]
                    # Note: opener injection into HTML is complex — subject line is the main win
        except Exception as e:
            log.warning("ai_enhance_email.failed", error=str(e))

        return draft


# ── Module-level convenience functions ───────────────────────────────────────

_writer_instance: Optional[CampaignWriter] = None


def get_writer() -> CampaignWriter:
    global _writer_instance
    if _writer_instance is None:
        _writer_instance = CampaignWriter()
    return _writer_instance
