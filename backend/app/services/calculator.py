"""
Mock closing cost calculator.
Generates FHA vs Conventional vs DSCR scenario estimates for a given listing.

These are EDUCATIONAL ESTIMATES ONLY.
All outputs must be shown with disclaimer:
"Example figures for educational purposes. Not a rate lock or commitment to lend.
Actual costs vary based on credit, lender, title, taxes, and other factors."
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CalcInput:
    purchase_price: float
    annual_taxes: Optional[float] = None       # if None, estimate at 1.1% of price
    annual_insurance: Optional[float] = None   # if None, estimate at 0.5% of price
    hoa_monthly: Optional[float] = 0
    rate_conventional: float = 7.00
    rate_fha: float = 6.75
    rate_dscr: float = 7.75
    down_pct_conventional: float = 5.0
    down_pct_fha: float = 3.5
    down_pct_dscr: float = 25.0
    loan_term_years: int = 30


@dataclass
class LoanScenario:
    loan_type: str
    down_payment: float
    down_pct: float
    loan_amount: float
    rate: float
    monthly_pi: float
    monthly_mip_pmi: float
    monthly_taxes: float
    monthly_insurance: float
    monthly_hoa: float
    total_monthly: float
    estimated_closing_costs: float
    cash_to_close: float
    seller_help_eligible: float
    notes: str


def monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    if annual_rate == 0:
        return principal / (years * 12)
    r = annual_rate / 100 / 12
    n = years * 12
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def calc_scenarios(inp: CalcInput) -> dict:
    price = inp.purchase_price
    taxes_monthly = (inp.annual_taxes or price * 0.011) / 12
    insurance_monthly = (inp.annual_insurance or price * 0.005) / 12
    hoa = inp.hoa_monthly or 0

    scenarios = []

    # ── Conventional 3% down ──────────────────────────────────────────────
    conv3_down = round(price * 0.03)
    conv3_loan = price - conv3_down
    conv3_pi = monthly_payment(conv3_loan, inp.rate_conventional, inp.loan_term_years)
    conv3_pmi = conv3_loan * 0.007 / 12   # PMI required (< 20% down)
    conv3_total = conv3_pi + conv3_pmi + taxes_monthly + insurance_monthly + hoa
    # Closing cost estimate: sale price × 0.065 (lower cash-in scenario)
    conv3_closing = round(price * 0.065)
    conv3_ctc = conv3_down + conv3_closing
    conv3_seller_help = round(price * 0.03)

    scenarios.append(LoanScenario(
        loan_type="Conventional 3%",
        down_payment=conv3_down,
        down_pct=3.0,
        loan_amount=conv3_loan,
        rate=inp.rate_conventional,
        monthly_pi=round(conv3_pi),
        monthly_mip_pmi=round(conv3_pmi),
        monthly_taxes=round(taxes_monthly),
        monthly_insurance=round(insurance_monthly),
        monthly_hoa=round(hoa),
        total_monthly=round(conv3_total),
        estimated_closing_costs=conv3_closing,
        cash_to_close=round(conv3_ctc),
        seller_help_eligible=conv3_seller_help,
        notes="3% down · PMI required until 20% equity"
    ))

    # ── Conventional 5% down ──────────────────────────────────────────────
    conv_down = round(price * (inp.down_pct_conventional / 100))
    conv_loan = price - conv_down
    conv_pi = monthly_payment(conv_loan, inp.rate_conventional, inp.loan_term_years)
    # PMI: ~0.7% annually if down < 20%, none if >= 20%
    conv_pmi = (conv_loan * 0.007 / 12) if inp.down_pct_conventional < 20 else 0
    conv_total = conv_pi + conv_pmi + taxes_monthly + insurance_monthly + hoa
    # Closing cost estimate: sale price × 0.085 for 5% down conventional
    # Higher multiplier reflects larger lender/escrow requirements at this tier
    conv_closing = round(price * 0.085)
    conv_ctc = conv_down + conv_closing
    conv_seller_help = round(price * 0.03)   # conventional: up to 3% seller concessions (< 10% down)

    scenarios.append(LoanScenario(
        loan_type="Conventional 5%",
        down_payment=conv_down,
        down_pct=inp.down_pct_conventional,
        loan_amount=conv_loan,
        rate=inp.rate_conventional,
        monthly_pi=round(conv_pi),
        monthly_mip_pmi=round(conv_pmi),
        monthly_taxes=round(taxes_monthly),
        monthly_insurance=round(insurance_monthly),
        monthly_hoa=round(hoa),
        total_monthly=round(conv_total),
        estimated_closing_costs=conv_closing,
        cash_to_close=round(conv_ctc),
        seller_help_eligible=conv_seller_help,
        notes=f"{inp.down_pct_conventional}% down · PMI {'required until 20% equity' if inp.down_pct_conventional < 20 else 'not required'}"
    ))

    # ── FHA ───────────────────────────────────────────────────────────────
    fha_down = round(price * (inp.down_pct_fha / 100))
    fha_base_loan = price - fha_down
    fha_ufmip = round(fha_base_loan * 0.0175)  # 1.75% upfront MIP
    fha_loan = fha_base_loan + fha_ufmip
    fha_pi = monthly_payment(fha_loan, inp.rate_fha, inp.loan_term_years)
    fha_mip = round(fha_base_loan * 0.0055 / 12)  # ~0.55% annual MIP monthly
    fha_total = fha_pi + fha_mip + taxes_monthly + insurance_monthly + hoa
    # Closing cost estimate: sale price × 0.07 for FHA
    # Includes upfront prepaids (county/insurance escrows), title/settlement, FHA-specific fees
    fha_closing = round(price * 0.07)
    fha_ctc = fha_down + fha_closing  # UFMIP rolled into loan
    fha_seller_help = round(price * 0.06)  # FHA: up to 6% seller concessions

    scenarios.append(LoanScenario(
        loan_type="FHA",
        down_payment=fha_down,
        down_pct=inp.down_pct_fha,
        loan_amount=fha_loan,
        rate=inp.rate_fha,
        monthly_pi=round(fha_pi),
        monthly_mip_pmi=fha_mip,
        monthly_taxes=round(taxes_monthly),
        monthly_insurance=round(insurance_monthly),
        monthly_hoa=round(hoa),
        total_monthly=round(fha_total),
        estimated_closing_costs=fha_closing,
        cash_to_close=round(fha_ctc),
        seller_help_eligible=fha_seller_help,
        notes=f"3.5% down · Upfront MIP ${fha_ufmip:,} rolled into loan · Monthly MIP ${fha_mip}/mo"
    ))

    # ── DSCR (investor) ───────────────────────────────────────────────────
    dscr_down = round(price * (inp.down_pct_dscr / 100))
    dscr_loan = price - dscr_down
    dscr_pi = monthly_payment(dscr_loan, inp.rate_dscr, inp.loan_term_years)
    dscr_total = dscr_pi + taxes_monthly + insurance_monthly + hoa
    dscr_closing = round(dscr_loan * 0.03)
    dscr_ctc = dscr_down + dscr_closing
    # Rough rent estimate: price / 160 rule
    rent_estimate = round(price / 160)
    dscr_ratio = round(dscr_pi / (dscr_pi + taxes_monthly + insurance_monthly + hoa), 2) if dscr_total > 0 else 0

    scenarios.append(LoanScenario(
        loan_type="DSCR (Investor)",
        down_payment=dscr_down,
        down_pct=inp.down_pct_dscr,
        loan_amount=dscr_loan,
        rate=inp.rate_dscr,
        monthly_pi=round(dscr_pi),
        monthly_mip_pmi=0,
        monthly_taxes=round(taxes_monthly),
        monthly_insurance=round(insurance_monthly),
        monthly_hoa=round(hoa),
        total_monthly=round(dscr_total),
        estimated_closing_costs=dscr_closing,
        cash_to_close=round(dscr_ctc),
        seller_help_eligible=round(price * 0.02),
        notes=f"25% down · Qualified on rental income · Est. rent needed: ~${rent_estimate:,}/mo to qualify"
    ))

    return {
        "purchase_price": price,
        "scenarios": [
            {
                "loan_type": s.loan_type,
                "down_payment": s.down_payment,
                "down_pct": s.down_pct,
                "loan_amount": s.loan_amount,
                "rate": s.rate,
                "monthly_breakdown": {
                    "principal_interest": s.monthly_pi,
                    "mip_pmi": s.monthly_mip_pmi,
                    "taxes": s.monthly_taxes,
                    "insurance": s.monthly_insurance,
                    "hoa": s.monthly_hoa,
                    "total": s.total_monthly,
                },
                "cash_to_close": s.cash_to_close,
                "estimated_closing_costs": s.estimated_closing_costs,
                "closing_cost_multiplier": 0.070 if s.loan_type == "FHA" else (0.085 if s.loan_type == "Conventional 5%" else (0.065 if s.loan_type == "Conventional 3%" else 0.030)),
                "seller_help_eligible": s.seller_help_eligible,
                "notes": s.notes,
            }
            for s in scenarios
        ],
        "disclaimer": (
            "Example figures for educational purposes only. Not a rate lock or commitment to lend. "
            "Monthly payment estimates assume example interest rates and may not reflect current market conditions. "
            "Closing cost estimates are calculated using a multiplier of the sale price (Conventional: 6.5%, FHA: 7.0%) "
            "to approximate county/insurance escrow prepaids, title and settlement fees, and lender origination costs. "
            "These are raw estimates and do NOT include specialized pricing, lender credits, seller concessions, "
            "or down payment assistance programs — all of which can significantly reduce your actual out-of-pocket costs. "
            "Actual payments and costs vary based on credit score, loan amount, lender, and other factors. "
            "Contact us for a real, personalized quote."
        ),
        "closing_cost_note": (
            "Closing cost estimates use sale price × multiplier "
            "(Conv 3%: 6.5% · Conv 5%: 8.5% · FHA: 7.0%). "
            "These are rough figures to give you a ballpark. Your actual costs will depend on your lender, "
            "county, title company, and any assistance programs you qualify for."
        ),
    }
