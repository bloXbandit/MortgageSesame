from app.config import settings as _s
"""
Direct mail HTML templates.

All templates produce 4.25" x 6" postcard-size or 8.5" x 11" letter HTML.
Design intent: premium financial document aesthetic — dark/gold palette,
certificate-style framing. Creates urgency through specificity (real address,
real equity estimate) not fake urgency. Clearly labeled ADVERTISEMENT throughout.

CRITICAL COMPLIANCE RULES baked into every template:
  - "ADVERTISEMENT" in top header
  - "NOT A CHECK · NOT A LOAN APPROVAL · NOT A COMMITMENT TO LEND"
  - "Estimates are illustrative only"
  - NMLS # on every piece
  - Equal Housing Opportunity
  - Opt-out / contact instructions

All templates accept a merge_data dict with prospect-specific values.
Missing values render as sensible defaults or placeholders.
"""


from app.services.qr_service import qr_img_tag as _qr_img_tag


def _dollars(v) -> str:
    if v is None:
        return "$—"
    try:
        return f"${float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _pct(v) -> str:
    if v is None:
        return "—%"
    try:
        return f"{float(v):.1f}%"
    except (TypeError, ValueError):
        return str(v)


BASE_CSS = """
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', Arial, sans-serif; background: #fff; color: #1a1a1a; }
  .ad-label { background: #1a1a1a; color: #f5c87a; font-size: 9px; font-weight: 700;
    letter-spacing: 0.18em; text-align: center; padding: 5px 0; text-transform: uppercase; }
  .disclaimer { font-size: 7.5px; color: #888; line-height: 1.5; padding: 12px 18px;
    border-top: 1px solid #e0d8cc; margin-top: 10px; }
  .nmls { font-size: 7.5px; color: #aaa; text-align: right; padding: 6px 18px 4px; }
"""


# ── 1. HOME EQUITY OPPORTUNITY NOTICE (flagship "voucher") ────────────────────

def equity_voucher(merge_data: dict) -> str:
    name = merge_data.get("prospect_name", "Homeowner")
    address = merge_data.get("property_address", "Your Property")
    city_state = merge_data.get("property_city_state", "")
    equity_dollars = _dollars(merge_data.get("estimated_equity_dollars"))
    equity_pct = _pct(merge_data.get("estimated_equity_pct"))
    current_value = _dollars(merge_data.get("estimated_current_value"))
    banker_name = merge_data.get("banker_name", "Your Local Mortgage Banker")
    banker_phone = merge_data.get("banker_phone", "")
    banker_nmls = merge_data.get("banker_nmls", _s.banker_nmls)
    service_states = merge_data.get("service_states", _s.service_states)
    qr_url = merge_data.get("tracking_url", "")
    expires = merge_data.get("expires_label", "90 days")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
{BASE_CSS}
.outer {{ width: 650px; border: 2px solid #1a1a1a; background: #fff; }}
.header {{ background: #1a1a1a; padding: 14px 22px; display: flex; justify-content: space-between; align-items: center; }}
.header-title {{ color: #f5c87a; font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; }}
.header-notice {{ color: #666; font-size: 9px; }}
.body {{ padding: 20px 22px 14px; }}
.property-line {{ font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 2px; }}
.property-address {{ font-size: 17px; font-weight: 900; color: #1a1a1a; line-height: 1.15; margin-bottom: 4px; }}
.property-city {{ font-size: 13px; color: #555; margin-bottom: 14px; }}
.divider {{ border: none; border-top: 1px solid #e0d8cc; margin: 12px 0; }}
.equity-box {{ background: #f8f4ec; border: 1.5px solid #e8a84c; border-radius: 4px; padding: 14px 18px; margin-bottom: 14px; }}
.equity-label {{ font-size: 9px; color: #92520b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 4px; }}
.equity-amount {{ font-size: 42px; font-weight: 900; color: #1a1a1a; line-height: 1; letter-spacing: -1px; }}
.equity-sub {{ font-size: 10px; color: #888; margin-top: 4px; }}
.options-title {{ font-size: 9px; font-weight: 700; color: #555; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px; }}
.option-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 11px; color: #333; }}
.option-box {{ width: 12px; height: 12px; border: 1.5px solid #1a1a1a; border-radius: 2px; flex-shrink: 0; }}
.cta-section {{ background: #1a1a1a; padding: 12px 18px; border-radius: 4px; margin-top: 12px; display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
.cta-text {{ color: #fff; font-size: 11px; font-weight: 700; }}
.cta-phone {{ color: #f5c87a; font-size: 14px; font-weight: 900; }}
.cta-sub {{ color: #888; font-size: 9px; }}
.qr-placeholder {{ width: 58px; height: 58px; background: #fff; border-radius: 3px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
.cert-border {{ border: 0.5px solid #e0d8cc; padding: 3px; margin-bottom: 10px; }}
.est-note {{ font-size: 9px; color: #e8a84c; font-weight: 600; margin-top: 3px; }}
</style>
</head>
<body>
<div class="outer">
  <div class="ad-label">ADVERTISEMENT — NOT A CHECK — NOT A LOAN APPROVAL — NOT A COMMITMENT TO LEND</div>
  <div class="header">
    <div class="header-title">Home Equity Opportunity Notice</div>
    <div class="header-notice">Prepared for homeowner of record · {expires}</div>
  </div>
  <div class="body">
    <div class="property-line">Regarding property at</div>
    <div class="property-address">{address}</div>
    <div class="property-city">{city_state}</div>
    <div class="divider"></div>

    <div class="cert-border">
      <div class="equity-box">
        <div class="equity-label">Estimated Available Equity</div>
        <div class="equity-amount">{equity_dollars}</div>
        <div class="equity-sub">Est. current value {current_value} · Est. equity {equity_pct} of value</div>
        <div class="est-note">★ Illustrative estimate based on public records — not a guaranteed value or appraisal</div>
      </div>
    </div>

    <div class="options-title">This notice covers the following review options:</div>
    {"".join(f'<div class="option-row"><div class="option-box"></div>{opt}</div>' for opt in [
        "Rate-and-term refinance review — reduce your monthly payment",
        "Cash-out equity review — access funds for renovations, payoff, or investment",
        "HELOC / equity line review — flexible access, interest-only draw period",
        "Investment property / DSCR review — qualify on rental income",
    ])}

    <div class="cta-section">
      <div>
        <div class="cta-text">Activate your free equity review</div>
        <div class="cta-phone">{banker_phone}</div>
        <div class="cta-sub">{banker_name} · No obligation · Takes 10 minutes</div>
      </div>
      {'<div class="qr-placeholder">' + _qr_img_tag(qr_url, width=52) + '</div>' if qr_url else '<div class="qr-placeholder" style="font-size:7px;color:#ccc;text-align:center">QR<br>code</div>'}
    </div>
  </div>
  <div class="disclaimer">
    <strong>ADVERTISEMENT.</strong> This notice was prepared by {banker_name} (NMLS #{banker_nmls}) as an advertisement for mortgage services.
    It is NOT a check, NOT a negotiable instrument, NOT a loan approval, and NOT a commitment to lend.
    Estimated equity figures are derived from public records and automated valuation models and may not reflect
    actual property value. Actual loan terms, rates, monthly payments, and eligibility are determined by credit
    score, debt-to-income ratio, property appraisal, loan-to-value ratio, and full underwriting review.
    Equal Housing Opportunity. To stop receiving this type of mail, contact us at {banker_phone}.
    NMLS #{banker_nmls}. Licensed in {service_states}.
  </div>
</div>
</body></html>"""


# ── 2. REFINANCE REVIEW CERTIFICATE ──────────────────────────────────────────

def refi_certificate(merge_data: dict) -> str:
    name = merge_data.get("prospect_name", "Homeowner")
    address = merge_data.get("property_address", "Your Property")
    city_state = merge_data.get("property_city_state", "")
    orig_date = merge_data.get("origination_date", "")
    orig_date_label = f"originated {orig_date}" if orig_date else "based on public records"
    current_rate = merge_data.get("current_rate_estimate")
    rate_label = f"{float(current_rate):.2f}%" if current_rate else "your current rate"
    loan_amount = _dollars(merge_data.get("current_loan_amount"))
    banker_name = merge_data.get("banker_name", "Your Local Mortgage Banker")
    banker_phone = merge_data.get("banker_phone", "")
    banker_nmls = merge_data.get("banker_nmls", _s.banker_nmls)
    qr_url = merge_data.get("tracking_url", "")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
{BASE_CSS}
.outer {{ width: 650px; border: 2.5px solid #1a1a1a; background: #fff; }}
.ribbon {{ background: linear-gradient(135deg, #1a1a1a 0%, #2e2e2e 100%); padding: 18px 22px; }}
.ribbon-title {{ color: #f5c87a; font-size: 13px; font-weight: 900; letter-spacing: 0.06em; text-transform: uppercase; }}
.ribbon-sub {{ color: #888; font-size: 9px; margin-top: 2px; }}
.body {{ padding: 18px 22px; }}
.cert-frame {{ border: 1.5px solid #c8b878; background: #fffbf2; padding: 16px 18px; border-radius: 3px; margin-bottom: 14px; }}
.cert-seal {{ font-size: 8px; color: #92520b; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 6px; border-bottom: 1px solid #e8d0a0; padding-bottom: 5px; }}
.cert-headline {{ font-size: 22px; font-weight: 900; color: #1a1a1a; line-height: 1.1; margin-bottom: 6px; }}
.cert-body {{ font-size: 11px; color: #444; line-height: 1.65; }}
.rate-highlight {{ display: inline-block; background: #1a1a1a; color: #f5c87a; padding: 1px 8px; border-radius: 3px; font-weight: 700; font-size: 13px; }}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }}
.info-box {{ background: #f5f5f5; border-left: 3px solid #1a1a1a; padding: 8px 10px; }}
.info-label {{ font-size: 8px; color: #888; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; margin-bottom: 2px; }}
.info-value {{ font-size: 13px; font-weight: 700; color: #1a1a1a; }}
.cta {{ background: #f5c87a; color: #1a1a1a; padding: 12px 18px; border-radius: 4px; text-align: center; }}
.cta-main {{ font-size: 13px; font-weight: 900; }}
.cta-phone {{ font-size: 18px; font-weight: 900; display: block; margin-top: 2px; }}
</style>
</head>
<body>
<div class="outer">
  <div class="ad-label">ADVERTISEMENT — NOT A COMMITMENT TO LEND — ESTIMATES ARE EDUCATIONAL ONLY</div>
  <div class="ribbon">
    <div class="ribbon-title">Mortgage Rate Review Certificate</div>
    <div class="ribbon-sub">Prepared for homeowner of record at: {address}</div>
  </div>
  <div class="body">
    <div class="cert-frame">
      <div class="cert-seal">Issued by {banker_name} · NMLS #{banker_nmls}</div>
      <div class="cert-headline">Your loan ({orig_date_label}) may<br>be costing you more than necessary.</div>
      <div class="cert-body">
        Mortgage rates have changed significantly since many homeowners in your area locked in their rate.
        Based on public records, your current estimated rate is <span class="rate-highlight">{rate_label}</span>
        on a balance of approximately {loan_amount}.<br><br>
        <strong>A rate review costs nothing.</strong> In 10 minutes, you'll know exactly where you stand.
      </div>
    </div>

    <div class="two-col">
      <div class="info-box">
        <div class="info-label">Est. current rate</div>
        <div class="info-value">{rate_label}</div>
      </div>
      <div class="info-box">
        <div class="info-label">Est. loan balance</div>
        <div class="info-value">{loan_amount}</div>
      </div>
    </div>

    <div class="cta">
      <div class="cta-main">Redeem your free rate review →</div>
      <span class="cta-phone">{banker_phone if banker_phone else "Scan QR or call"}</span>
      <div style="font-size:8px;margin-top:3px;">No credit pull. No obligation. 10 minutes.</div>
    </div>
  </div>
  <div class="disclaimer">
    <strong>ADVERTISEMENT.</strong> {banker_name} (NMLS #{banker_nmls}). NOT a check. NOT a commitment to lend.
    Rate estimates are based on public records and may not reflect your actual rate or balance.
    Actual rate savings depend on your credit profile, remaining loan term, closing costs, and
    current market conditions. Equal Housing Opportunity.
    To opt out of future mailings, call or text {banker_phone if banker_phone else "the number above"}.
  </div>
</div>
</body></html>"""


# ── 3. FHA STREAMLINE WATCH NOTICE ────────────────────────────────────────────

def fha_streamline_notice(merge_data: dict) -> str:
    address = merge_data.get("property_address", "Your FHA-Insured Property")
    city_state = merge_data.get("property_city_state", "")
    orig_date = merge_data.get("origination_date", "2022–2023")
    current_rate = merge_data.get("current_rate_estimate")
    rate_label = f"{float(current_rate):.2f}%" if current_rate else "your current rate"
    banker_name = merge_data.get("banker_name", "Your Local FHA Lender")
    banker_phone = merge_data.get("banker_phone", "")
    banker_nmls = merge_data.get("banker_nmls", _s.banker_nmls)
    qr_url = merge_data.get("tracking_url", "")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
{BASE_CSS}
.outer {{ width: 650px; border: 2px solid #1a1a1a; background: #fff; }}
.header {{ background: #1a3050; color: #fff; padding: 14px 22px; }}
.header-flag {{ background: #f5c87a; color: #1a1a1a; font-size: 9px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase; display: inline-block;
  padding: 2px 8px; border-radius: 2px; margin-bottom: 6px; }}
.header-title {{ font-size: 17px; font-weight: 900; }}
.header-sub {{ font-size: 10px; color: #93b8d8; margin-top: 3px; }}
.body {{ padding: 18px 22px; }}
.watch-box {{ background: #f0f6ff; border: 1.5px solid #3a6fa8; border-radius: 4px; padding: 14px 16px; margin-bottom: 14px; }}
.watch-label {{ font-size: 9px; font-weight: 700; color: #1e4d8c; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 5px; }}
.watch-text {{ font-size: 12px; color: #1a1a1a; line-height: 1.6; }}
.benefits {{ margin-bottom: 14px; }}
.benefit {{ display: flex; align-items: flex-start; gap: 8px; margin-bottom: 7px; font-size: 11px; color: #333; line-height: 1.45; }}
.check {{ color: #1e4d8c; font-weight: 900; font-size: 13px; flex-shrink: 0; }}
.cta {{ background: #1a3050; padding: 12px 18px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }}
.cta-text {{ color: #fff; font-size: 12px; font-weight: 700; }}
.cta-phone {{ color: #f5c87a; font-size: 15px; font-weight: 900; display: block; }}
</style>
</head>
<body>
<div class="outer">
  <div class="ad-label">ADVERTISEMENT — NOT A LOAN APPROVAL — EDUCATIONAL ESTIMATE ONLY</div>
  <div class="header">
    <div class="header-flag">FHA Streamline Watch</div>
    <div class="header-title">Your FHA loan may qualify for a streamline refinance.</div>
    <div class="header-sub">Property: {address}{', ' + city_state if city_state else ''} · Originated approx. {orig_date}</div>
  </div>
  <div class="body">
    <div class="watch-box">
      <div class="watch-label">Why this notice was prepared</div>
      <div class="watch-text">
        FHA Streamline refinances allow eligible homeowners to refinance with
        <strong>reduced documentation and no appraisal required</strong> in most cases.
        If your current rate is near <strong>{rate_label}</strong> and rates have moved,
        a streamline review is worth 10 minutes of your time.
      </div>
    </div>

    <div class="benefits">
      {"".join(f'<div class="benefit"><span class="check">✓</span>{b}</div>' for b in [
          "No appraisal required in most cases",
          "Reduced income/credit documentation",
          "Net tangible benefit test — lender confirms savings before proceeding",
          "Must be current on payments — no 30-day lates in last 12 months",
          "6 months minimum seasoning from original FHA loan",
      ])}
    </div>

    <div class="cta">
      <div>
        <div class="cta-text">Get your free FHA Streamline eligibility check</div>
        <span class="cta-phone">{banker_phone if banker_phone else 'Call or scan QR'}</span>
        <div style="color:#93b8d8;font-size:9px;margin-top:2px;">{banker_name} · NMLS #{banker_nmls}</div>
      </div>
      {_qr_img_tag(qr_url, width=54) if qr_url else ''}
    </div>
  </div>
  <div class="disclaimer">
    <strong>ADVERTISEMENT.</strong> {banker_name} (NMLS #{banker_nmls}). NOT a commitment to lend.
    FHA Streamline refinance eligibility requires meeting HUD guidelines including payment history,
    seasoning requirements, and net tangible benefit. Not all borrowers will qualify. Actual rate,
    payment, and costs depend on credit, property, and lender underwriting. Equal Housing Opportunity.
  </div>
</div>
</body></html>"""


# ── 4. DSCR INVESTOR REVIEW NOTICE ────────────────────────────────────────────

def dscr_investor_notice(merge_data: dict) -> str:
    address = merge_data.get("property_address", "Your Investment Property")
    city_state = merge_data.get("property_city_state", "")
    loan_amount = _dollars(merge_data.get("current_loan_amount"))
    equity_dollars = _dollars(merge_data.get("estimated_equity_dollars"))
    banker_name = merge_data.get("banker_name", "Your Investment Mortgage Specialist")
    banker_phone = merge_data.get("banker_phone", "")
    banker_nmls = merge_data.get("banker_nmls", _s.banker_nmls)
    qr_url = merge_data.get("tracking_url", "")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
{BASE_CSS}
.outer {{ width: 650px; border: 2px solid #1a1a1a; background: #0e0e0e; color: #fff; }}
.header {{ padding: 16px 22px; border-bottom: 1px solid #2a2a2a; }}
.tag {{ background: #f5c87a; color: #1a1a1a; font-size: 9px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase; padding: 2px 8px; border-radius: 2px; display: inline-block; margin-bottom: 7px; }}
.header-title {{ font-size: 20px; font-weight: 900; color: #fff; line-height: 1.1; }}
.header-address {{ font-size: 10px; color: #888; margin-top: 5px; }}
.body {{ padding: 18px 22px; }}
.stat-row {{ display: flex; gap: 10px; margin-bottom: 14px; }}
.stat-box {{ flex: 1; background: #1a1a1a; border: 1px solid #2e2e2e; border-radius: 5px; padding: 10px 12px; }}
.stat-label {{ font-size: 8px; color: #888; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; margin-bottom: 3px; }}
.stat-value {{ font-size: 18px; font-weight: 900; color: #f5c87a; }}
.pitch {{ font-size: 11px; color: #ccc; line-height: 1.7; margin-bottom: 14px; }}
.feature {{ display: flex; gap: 8px; margin-bottom: 6px; font-size: 10px; color: #bbb; }}
.dot {{ color: #f5c87a; font-weight: 900; flex-shrink: 0; }}
.cta {{ background: #f5c87a; color: #1a1a1a; padding: 12px 18px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }}
</style>
</head>
<body>
<div class="outer">
  <div class="ad-label">ADVERTISEMENT — NOT A COMMITMENT TO LEND — EDUCATIONAL REVIEW ONLY</div>
  <div class="header">
    <div class="tag">DSCR Investor Review</div>
    <div class="header-title">Your investment property<br>may qualify for a no-income-check refi.</div>
    <div class="header-address">{address}{', ' + city_state if city_state else ''}</div>
  </div>
  <div class="body">
    <div class="stat-row">
      <div class="stat-box"><div class="stat-label">Est. loan balance</div><div class="stat-value">{loan_amount}</div></div>
      <div class="stat-box"><div class="stat-label">Est. equity</div><div class="stat-value">{equity_dollars}</div></div>
      <div class="stat-box"><div class="stat-label">Qualification method</div><div class="stat-value" style="font-size:12px">Rental income only</div></div>
    </div>

    <div class="pitch">
      DSCR (Debt Service Coverage Ratio) loans let real estate investors refinance
      <strong style="color:#fff">without W2s, tax returns, or personal income verification</strong>.
      Qualification is based entirely on whether the property's rental income covers the new
      payment — typically at a 1.0–1.25× ratio.
    </div>

    {"".join(f'<div class="feature"><span class="dot">▸</span>{f}</div>' for f in [
        "No personal income documentation required",
        "Close in an LLC or personal name",
        "Cash-out refinance options available",
        "25% equity typically required",
        "Rates typically 0.75–1.25% above conventional",
    ])}

    <div class="cta" style="margin-top:14px;">
      <div>
        <div style="font-size:12px;font-weight:900;">Get your free DSCR analysis</div>
        <div style="font-size:15px;font-weight:900;margin-top:2px;">{banker_phone}</div>
        <div style="font-size:8px;margin-top:2px;">{banker_name} · NMLS #{banker_nmls} · No tax returns needed</div>
      </div>
      {_qr_img_tag(qr_url, width=52) if qr_url else ''}
    </div>
  </div>
  <div class="disclaimer" style="background:#0e0e0e;color:#555;">
    <strong style="color:#666;">ADVERTISEMENT.</strong> {banker_name} (NMLS #{banker_nmls}). NOT a commitment to lend.
    DSCR loan qualification and terms depend on property income, credit score, LTV, property type,
    and lender underwriting guidelines. Not all properties or borrowers will qualify. Equal Housing Opportunity.
  </div>
</div>
</body></html>"""


# ── 5. REALTOR / PARTNER INVITE ────────────────────────────────────────────────

def realtor_invite(merge_data: dict) -> str:
    realtor_name = merge_data.get("prospect_name", "Real Estate Professional")
    banker_name = merge_data.get("banker_name", "Your Local Mortgage Banker")
    banker_phone = merge_data.get("banker_phone", "")
    banker_nmls = merge_data.get("banker_nmls", _s.banker_nmls)
    service_states = merge_data.get("service_states", _s.service_states)
    hub_url = merge_data.get("hub_url", "")
    qr_url = merge_data.get("tracking_url", "")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
{BASE_CSS}
.outer {{ width: 650px; border: 2px solid #1a1a1a; background: #fff; }}
.header {{ background: #1a1a1a; padding: 16px 22px; }}
.tag {{ background: #f5c87a; color: #1a1a1a; font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; padding: 2px 8px; border-radius: 2px; display: inline-block; margin-bottom: 7px; }}
.header-title {{ font-size: 18px; font-weight: 900; color: #fff; line-height: 1.15; }}
.body {{ padding: 20px 22px; }}
.pitch {{ font-size: 12px; color: #333; line-height: 1.75; margin-bottom: 16px; }}
.feature-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }}
.feat-box {{ background: #f8f4ec; border-left: 3px solid #f5c87a; padding: 10px 12px; }}
.feat-title {{ font-size: 10px; font-weight: 700; color: #1a1a1a; margin-bottom: 3px; }}
.feat-desc {{ font-size: 9px; color: #666; line-height: 1.45; }}
.cta {{ background: #f5c87a; color: #1a1a1a; padding: 14px 18px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }}
.cta-text {{ font-size: 13px; font-weight: 900; }}
.cta-phone {{ font-size: 16px; font-weight: 900; display: block; margin-top: 3px; }}
</style>
</head>
<body>
<div class="outer">
  <div class="ad-label">ADVERTISEMENT</div>
  <div class="header">
    <div class="tag">Realtor Partnership Invite</div>
    <div class="header-title">Your buyers deserve a mortgage partner<br>who makes you look good.</div>
  </div>
  <div class="body">
    <div class="pitch">
      Hi {realtor_name.split()[0] if realtor_name != 'Real Estate Professional' else 'there'},<br><br>
      I built a free homebuyer intelligence hub — real rate data, local DPA programs,
      and mock payment calculators on real listings — that educates your buyers
      <em>before</em> they even call you.<br><br>
      I'd love to show you how it works and how we can use it together to close more deals.
    </div>

    <div class="feature-grid">
      {"".join(f'<div class="feat-box"><div class="feat-title">{t}</div><div class="feat-desc">{d}</div></div>' for t, d in [
          ("21-Day Close Guarantee", "Full underwriting pre-approval before contract — your offers compete like cash."),
          ("DPA Program Access", f"{service_states} down payment programs — I find money your buyers didn't know existed."),
          ("Live Rate Hub", "Public-facing rate dashboard your clients can check anytime. Builds trust before they call."),
          ("Same-Day Pre-Approvals", "Buyers calling on your listings get answers today, not in 3 days."),
      ])}
    </div>

    <div class="cta">
      <div>
        <div class="cta-text">Let's set up a 15-minute intro call</div>
        <span class="cta-phone">{banker_phone}</span>
        <div style="font-size:9px;margin-top:2px;">{banker_name} · NMLS #{banker_nmls}</div>
      </div>
      {_qr_img_tag(qr_url, width=54) if qr_url else ''}
    </div>
  </div>
  <div class="disclaimer">
    {banker_name} (NMLS #{banker_nmls}). Licensed in {service_states}.
    Equal Housing Opportunity. To opt out of future mailings, contact us at {banker_phone}.
  </div>
</div>
</body></html>"""


# ── Template registry ─────────────────────────────────────────────────────────

TEMPLATES = {
    "equity_voucher":        equity_voucher,
    "refi_certificate":      refi_certificate,
    "fha_streamline_notice": fha_streamline_notice,
    "dscr_investor_notice":  dscr_investor_notice,
    "realtor_invite":        realtor_invite,
    # Alias
    "payment_review_notice": refi_certificate,
    "heloc_invite":          equity_voucher,
}


def campaign_email_html(
    headline: str,
    body: str,
    cta_text: str,
    cta_url: str,
    subject: str = "",
    flyer_image_url: str = "",
    merge_data: dict = None,
) -> str:
    """
    General-purpose HTML email for AI-generated campaign sequences.
    If flyer_image_url is set, the flyer is displayed as a hero image
    at the top of the email — visually branded and clickable to the CTA URL.

    Used by outreach.py when sending campaign email sequences.
    """
    md = merge_data or {}
    banker_name  = md.get("banker_name",  _s.banker_name)
    banker_nmls  = md.get("banker_nmls",  _s.banker_nmls)
    banker_phone = md.get("banker_phone", "")
    unsubscribe  = md.get("unsubscribe_url", "#unsubscribe")

    flyer_block = f"""
      <div style="margin:0 0 24px;border-radius:10px;overflow:hidden;line-height:0;">
        <a href="{cta_url}" style="display:block;">
          <img src="{flyer_image_url}" alt="Campaign flyer"
               style="width:100%;max-width:600px;display:block;border-radius:10px;" />
        </a>
      </div>""" if flyer_image_url else ""

    body_paragraphs = "".join(
        f'<p style="margin:0 0 14px;line-height:1.7;color:#2a2a2a;">{p.strip()}</p>'
        for p in body.split("\n\n") if p.strip()
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{subject or headline}</title>
</head>
<body style="margin:0;padding:0;background:#f5f3ef;font-family:Inter,Arial,sans-serif;">

  <div style="max-width:600px;margin:32px auto;background:#fff;border-radius:12px;
              overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.07);">

    <!-- Ad label -->
    <div style="background:#1f1f1f;color:#f5c87a;font-size:9px;font-weight:700;
                letter-spacing:0.18em;text-align:center;padding:7px 0;text-transform:uppercase;">
      ADVERTISEMENT · {_s.app_name.upper()}
    </div>

    <div style="padding:28px 32px 20px;">

      {flyer_block}

      <!-- Headline -->
      <h1 style="margin:0 0 16px;font-size:1.4rem;font-weight:900;color:#1f1f1f;line-height:1.25;">
        {headline}
      </h1>

      <!-- Body copy -->
      <div style="font-size:0.9rem;">{body_paragraphs}</div>

      <!-- CTA button -->
      <div style="margin:24px 0 8px;">
        <a href="{cta_url}"
           style="display:inline-block;padding:14px 28px;background:#c8860a;color:#fff;
                  text-decoration:none;border-radius:8px;font-weight:700;font-size:0.9rem;">
          {cta_text}
        </a>
      </div>

    </div>

    <!-- Footer / compliance -->
    <div style="background:#f9f7f4;border-top:1px solid #e8e4dc;padding:16px 32px;
                font-size:0.68rem;color:#999;line-height:1.6;">
      <p style="margin:0 0 6px;">
        {banker_name} · NMLS #{banker_nmls}{f' · {banker_phone}' if banker_phone else ''} ·
        Equal Housing Opportunity
      </p>
      <p style="margin:0 0 4px;">
        This email is an advertisement. Not a loan approval, commitment to lend,
        or rate guarantee. Rates and terms subject to change. {_s.app_name} —
        licensed in {_s.service_states}.
      </p>
      <p style="margin:0;">
        <a href="{unsubscribe}" style="color:#c8860a;text-decoration:none;">Unsubscribe</a>
      </p>
    </div>

  </div>
</body></html>"""


def render_mail_template(template_key: str, merge_data: dict) -> str:
    """Render a direct mail HTML template with merge data. Returns HTML string."""
    fn = TEMPLATES.get(template_key)
    if not fn:
        raise ValueError(f"Unknown mail template: {template_key}. Available: {list(TEMPLATES)}")
    return fn(merge_data)


def list_templates() -> list[dict]:
    return [
        {"key": "equity_voucher",        "name": "Home Equity Opportunity Notice",   "channel": "direct_mail", "best_for": "Homeowners with 25%+ equity"},
        {"key": "refi_certificate",      "name": "Mortgage Rate Review Certificate", "channel": "direct_mail", "best_for": "Buyers from 2022+ high-rate window"},
        {"key": "fha_streamline_notice", "name": "FHA Streamline Watch Notice",      "channel": "direct_mail", "best_for": "FHA borrowers at elevated rates"},
        {"key": "dscr_investor_notice",  "name": "DSCR Investor Review Notice",      "channel": "direct_mail", "best_for": "Investment property owners"},
        {"key": "realtor_invite",        "name": "Realtor Partnership Invite",       "channel": "direct_mail", "best_for": "Realtors, listing agents, title agents"},
    ]
