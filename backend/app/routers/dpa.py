"""
Down Payment Assistance program endpoints.
- GET  /dpa/              — public list (filter by state/county)
- GET  /dpa/{id}          — public detail
- POST /dpa/              — admin create
- PATCH /dpa/{id}         — admin update
- DELETE /dpa/{id}        — admin delete
- POST /dpa/admin/seed-md-dc — seed Maryland + DC programs (idempotent)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.hub import DpaProgram, DpaType
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/dpa", tags=["dpa"])


def _dpa_dict(p: DpaProgram) -> dict:
    return {
        "id": p.id,
        "program_name": p.program_name,
        "administering_agency": p.administering_agency,
        "state": p.state,
        "county": p.county,
        "city": p.city,
        "dpa_type": p.dpa_type,
        "assistance_amount": p.assistance_amount,
        "assistance_amount_max": p.assistance_amount_max,
        "target_buyer": p.target_buyer,
        "income_limit_notes": p.income_limit_notes,
        "credit_score_min": p.credit_score_min,
        "property_location_notes": p.property_location_notes,
        "property_type_notes": p.property_type_notes,
        "eligible_loan_types": p.eligible_loan_types,
        "repayment_notes": p.repayment_notes,
        "education_required": p.education_required,
        "other_requirements": p.other_requirements,
        "program_url": p.program_url,
        "is_active": p.is_active,
        "is_featured": p.is_featured,
        "last_verified": p.last_verified,
        "notes": p.notes,
        "sort_order": p.sort_order,
    }


@router.get("/")
async def list_dpa(
    state: Optional[str] = Query(None, description="State abbreviation, e.g. MD or DC"),
    county: Optional[str] = Query(None, description="County name — returns statewide + county-specific"),
    active_only: bool = Query(True),
    featured_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    q = select(DpaProgram).order_by(
        DpaProgram.sort_order,
        DpaProgram.is_featured.desc(),
        DpaProgram.assistance_amount_max.desc().nulls_last(),
    )
    if state:
        q = q.where(DpaProgram.state == state.upper())
    if county:
        q = q.where(
            or_(DpaProgram.county == None, DpaProgram.county.ilike(f"%{county}%"))
        )
    if active_only:
        q = q.where(DpaProgram.is_active == True)
    if featured_only:
        q = q.where(DpaProgram.is_featured == True)

    result = await db.execute(q)
    return [_dpa_dict(p) for p in result.scalars().all()]


@router.get("/{program_id}")
async def get_dpa(program_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DpaProgram).where(DpaProgram.id == program_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Program not found")
    return _dpa_dict(p)


# ── Admin CRUD ────────────────────────────────────────────────────────────────

class DpaCreate(BaseModel):
    program_name: str
    administering_agency: Optional[str] = None
    state: str
    county: Optional[str] = None
    city: Optional[str] = None
    dpa_type: str
    assistance_amount: Optional[str] = None
    assistance_amount_max: Optional[float] = None
    target_buyer: Optional[str] = None
    income_limit_notes: Optional[str] = None
    credit_score_min: Optional[int] = None
    property_location_notes: Optional[str] = None
    property_type_notes: Optional[str] = None
    eligible_loan_types: Optional[str] = None
    repayment_notes: Optional[str] = None
    education_required: bool = False
    other_requirements: Optional[str] = None
    program_url: Optional[str] = None
    is_active: bool = True
    is_featured: bool = False
    sort_order: int = 0
    last_verified: Optional[str] = None
    notes: Optional[str] = None


class DpaUpdate(BaseModel):
    program_name: Optional[str] = None
    administering_agency: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None
    dpa_type: Optional[str] = None
    assistance_amount: Optional[str] = None
    assistance_amount_max: Optional[float] = None
    target_buyer: Optional[str] = None
    income_limit_notes: Optional[str] = None
    credit_score_min: Optional[int] = None
    property_location_notes: Optional[str] = None
    property_type_notes: Optional[str] = None
    eligible_loan_types: Optional[str] = None
    repayment_notes: Optional[str] = None
    education_required: Optional[bool] = None
    other_requirements: Optional[str] = None
    program_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None
    last_verified: Optional[str] = None
    notes: Optional[str] = None


@router.post("/", status_code=201)
async def create_dpa(
    data: DpaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        dpa_type = DpaType(data.dpa_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid dpa_type: {data.dpa_type}")

    program = DpaProgram(**{**data.model_dump(exclude={"dpa_type"}), "dpa_type": dpa_type})
    db.add(program)
    await db.commit()
    await db.refresh(program)
    return _dpa_dict(program)


@router.patch("/{program_id}")
async def update_dpa(
    program_id: str,
    data: DpaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(DpaProgram).where(DpaProgram.id == program_id))
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    update_data = data.model_dump(exclude_unset=True)
    if "dpa_type" in update_data:
        try:
            update_data["dpa_type"] = DpaType(update_data["dpa_type"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid dpa_type: {update_data['dpa_type']}")

    for k, v in update_data.items():
        setattr(program, k, v)

    await db.commit()
    await db.refresh(program)
    return _dpa_dict(program)


@router.delete("/{program_id}", status_code=204)
async def delete_dpa(
    program_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(DpaProgram).where(DpaProgram.id == program_id))
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    await db.delete(program)
    await db.commit()


# ── Seed MD/DC ────────────────────────────────────────────────────────────────

MD_DC_SEED = [
    # ── Maryland Statewide (Maryland Mortgage Program) ──────────────────────
    {
        "program_name": "MMP 1st Time Advantage 6000",
        "administering_agency": "Maryland Department of Housing & Community Development (DHCD)",
        "state": "MD", "county": None, "city": None,
        "dpa_type": "deferred",
        "assistance_amount": "$6,000 deferred loan",
        "assistance_amount_max": 6000,
        "target_buyer": "First-time homebuyers (3-year rule)",
        "income_limit_notes": "Income limits vary by household size and county. ~$92,500–$154,420 depending on area.",
        "credit_score_min": 640,
        "property_location_notes": "Property must be in Maryland",
        "property_type_notes": "Single family, condo, townhouse, PUD",
        "eligible_loan_types": "FHA, Conventional, VA, USDA",
        "repayment_notes": "0% deferred — no monthly payment. Due on sale, refi, or when home is no longer primary residence.",
        "education_required": True,
        "other_requirements": "Homebuyer education course required. Must use approved MMP lender.",
        "program_url": "https://mmp.maryland.gov/pages/1sta.aspx",
        "is_active": True, "is_featured": True, "sort_order": 1,
        "last_verified": "2025-12-01",
        "notes": "Most popular MD DPA program. Can stack with other MMP products.",
    },
    {
        "program_name": "MMP 1st Time Advantage 3% Loan",
        "administering_agency": "Maryland DHCD",
        "state": "MD", "county": None, "city": None,
        "dpa_type": "deferred",
        "assistance_amount": "3% of first mortgage as deferred second lien",
        "assistance_amount_max": None,
        "target_buyer": "First-time homebuyers (3-year rule)",
        "income_limit_notes": "Same income limits as MMP 6000 program.",
        "credit_score_min": 640,
        "property_location_notes": "Maryland only",
        "property_type_notes": "Single family, condo, townhouse",
        "eligible_loan_types": "FHA, Conventional, VA, USDA",
        "repayment_notes": "0% deferred. Due on sale, refi, or primary residence change.",
        "education_required": True,
        "other_requirements": "Homebuyer education required. MMP-approved lender.",
        "program_url": "https://mmp.maryland.gov",
        "is_active": True, "is_featured": False, "sort_order": 2,
        "last_verified": "2025-12-01",
        "notes": "Good alternative to the flat $6,000 product for higher-priced homes.",
    },
    {
        "program_name": "MMP SmartBuy 3.0",
        "administering_agency": "Maryland DHCD",
        "state": "MD", "county": None, "city": None,
        "dpa_type": "deferred",
        "assistance_amount": "Up to $20,000 toward student debt + DPA",
        "assistance_amount_max": 20000,
        "target_buyer": "First-time buyers WITH outstanding student loan debt",
        "income_limit_notes": "Income limits apply. Must have minimum $1,000 student loan balance.",
        "credit_score_min": 640,
        "property_location_notes": "Maryland only",
        "property_type_notes": "Single family, condo, townhouse",
        "eligible_loan_types": "FHA, Conventional, VA, USDA",
        "repayment_notes": "Student debt portion paid directly to loan servicer at closing. DPA is 0% deferred.",
        "education_required": True,
        "other_requirements": "Must have verifiable student loan debt. MMP-approved lender required.",
        "program_url": "https://mmp.maryland.gov/pages/smartbuy.aspx",
        "is_active": True, "is_featured": True, "sort_order": 3,
        "last_verified": "2025-12-01",
        "notes": "Unique program — pays off student debt at closing AND provides down payment help.",
    },
    {
        "program_name": "MMP HomeCredit (Mortgage Credit Certificate)",
        "administering_agency": "Maryland DHCD",
        "state": "MD", "county": None, "city": None,
        "dpa_type": "grant",
        "assistance_amount": "Annual federal tax credit — up to $2,000/year",
        "assistance_amount_max": 2000,
        "target_buyer": "First-time homebuyers",
        "income_limit_notes": "Income limits apply by county and household size.",
        "credit_score_min": 640,
        "property_location_notes": "Maryland only",
        "property_type_notes": "Single family, condo, townhouse",
        "eligible_loan_types": "FHA, Conventional, VA, USDA",
        "repayment_notes": "Not a loan — annual federal tax credit on mortgage interest paid. Keep as long as home is primary residence.",
        "education_required": True,
        "other_requirements": "MCC is a tax credit certificate — not cash at closing. Can be combined with DPA.",
        "program_url": "https://mmp.maryland.gov/pages/homecredit.aspx",
        "is_active": True, "is_featured": False, "sort_order": 4,
        "last_verified": "2025-12-01",
        "notes": "Not cash at closing — reduces federal tax bill by up to $2,000/yr for life of loan.",
    },
    {
        "program_name": "Maryland Homefront (Veterans DPA)",
        "administering_agency": "Maryland DHCD",
        "state": "MD", "county": None, "city": None,
        "dpa_type": "deferred",
        "assistance_amount": "$6,000–$10,000 deferred assistance",
        "assistance_amount_max": 10000,
        "target_buyer": "Active duty military, veterans, surviving spouses",
        "income_limit_notes": "Standard MMP income limits apply.",
        "credit_score_min": 620,
        "property_location_notes": "Maryland only",
        "property_type_notes": "Single family, condo, townhouse",
        "eligible_loan_types": "VA, FHA, Conventional",
        "repayment_notes": "0% deferred. Due on sale or refinance.",
        "education_required": True,
        "other_requirements": "Military service documentation required.",
        "program_url": "https://mmp.maryland.gov/pages/homefront.aspx",
        "is_active": True, "is_featured": False, "sort_order": 5,
        "last_verified": "2025-12-01",
        "notes": "Designed to work with VA loans — $0 down + deferred DPA is a powerful combo.",
    },
    # ── Maryland County Programs ──────────────────────────────────────────
    {
        "program_name": "Prince George's County Pathways to Homeownership",
        "administering_agency": "Prince George's County Department of Housing & Community Development",
        "state": "MD", "county": "Prince George's", "city": None,
        "dpa_type": "deferred",
        "assistance_amount": "Up to $10,000 deferred loan",
        "assistance_amount_max": 10000,
        "target_buyer": "First-time buyers purchasing in Prince George's County",
        "income_limit_notes": "Income at or below 80% AMI. Household income limits apply.",
        "credit_score_min": 620,
        "property_location_notes": "Must purchase in Prince George's County, MD",
        "property_type_notes": "Single family, townhouse, condo",
        "eligible_loan_types": "FHA, Conventional, VA",
        "repayment_notes": "0% interest deferred. Due on sale, refi, or non-owner-occupancy.",
        "education_required": True,
        "other_requirements": "Must complete county-approved homebuyer counseling.",
        "program_url": "https://www.princegeorgescountymd.gov/3052/Homeownership",
        "is_active": True, "is_featured": True, "sort_order": 10,
        "last_verified": "2025-12-01",
        "notes": "PG County is active MMP market — stacks well with MMP 6000.",
    },
    {
        "program_name": "Montgomery County Down Payment Assistance",
        "administering_agency": "Montgomery County Department of Housing & Community Affairs",
        "state": "MD", "county": "Montgomery", "city": None,
        "dpa_type": "deferred",
        "assistance_amount": "Up to $25,000 deferred second lien",
        "assistance_amount_max": 25000,
        "target_buyer": "First-time buyers or those not owning in past 3 years",
        "income_limit_notes": "Income limits: up to 80% AMI for Montgomery County. Exact limits updated annually.",
        "credit_score_min": 640,
        "property_location_notes": "Must purchase in Montgomery County, MD",
        "property_type_notes": "Single family, condo, townhouse",
        "eligible_loan_types": "FHA, Conventional",
        "repayment_notes": "0% deferred. Shared appreciation may apply on resale.",
        "education_required": True,
        "other_requirements": "Buyer must live in the home as primary residence.",
        "program_url": "https://www.montgomerycountymd.gov/DHCA/housing/homebuying/",
        "is_active": True, "is_featured": False, "sort_order": 11,
        "last_verified": "2025-12-01",
        "notes": "Montgomery County has some of the highest home prices in MD — this DPA can be critical.",
    },
    {
        "program_name": "Baltimore City Live Baltimore Settlement Expense Loan",
        "administering_agency": "Live Baltimore / Baltimore City",
        "state": "MD", "county": "Baltimore City", "city": "Baltimore",
        "dpa_type": "deferred",
        "assistance_amount": "Up to $10,000 for settlement expenses",
        "assistance_amount_max": 10000,
        "target_buyer": "Buyers purchasing in Baltimore City",
        "income_limit_notes": "Income limits apply. Varies by program year.",
        "credit_score_min": 620,
        "property_location_notes": "Must purchase within Baltimore City limits",
        "property_type_notes": "Single family, rowhouse, condo",
        "eligible_loan_types": "FHA, Conventional, VA",
        "repayment_notes": "Forgivable over time or deferred depending on specific program variant.",
        "education_required": True,
        "other_requirements": "Buyer must occupy as primary residence for required period.",
        "program_url": "https://livebaltimore.com/homebuying-assistance/",
        "is_active": True, "is_featured": False, "sort_order": 12,
        "last_verified": "2025-12-01",
        "notes": "Baltimore City Vacants to Value program may offer additional incentives in target blocks.",
    },
    {
        "program_name": "Anne Arundel County DPA Program",
        "administering_agency": "Anne Arundel County Office of Community Services",
        "state": "MD", "county": "Anne Arundel", "city": None,
        "dpa_type": "deferred",
        "assistance_amount": "Up to $12,500 deferred loan",
        "assistance_amount_max": 12500,
        "target_buyer": "First-time homebuyers in Anne Arundel County",
        "income_limit_notes": "Income at or below 80% AMI.",
        "credit_score_min": 620,
        "property_location_notes": "Must purchase in Anne Arundel County",
        "property_type_notes": "Single family, townhouse, condo",
        "eligible_loan_types": "FHA, Conventional",
        "repayment_notes": "0% interest deferred. Due on sale, refi, or vacancy.",
        "education_required": True,
        "program_url": "https://www.aacounty.org/departments/planning-and-zoning/housing/",
        "is_active": True, "is_featured": False, "sort_order": 13,
        "last_verified": "2025-12-01",
    },
    {
        "program_name": "Howard County DPA Program",
        "administering_agency": "Howard County Department of Housing and Community Development",
        "state": "MD", "county": "Howard", "city": None,
        "dpa_type": "deferred",
        "assistance_amount": "Up to $40,000 deferred second mortgage",
        "assistance_amount_max": 40000,
        "target_buyer": "First-time buyers in Howard County",
        "income_limit_notes": "Income limits at or below 80% AMI for Howard County.",
        "credit_score_min": 640,
        "property_location_notes": "Must purchase in Howard County, MD",
        "property_type_notes": "Single family, condo, townhouse",
        "eligible_loan_types": "FHA, Conventional",
        "repayment_notes": "0% deferred. Due on sale, refi, or change of occupancy.",
        "education_required": True,
        "program_url": "https://www.howardcountymd.gov/departments/planning-and-zoning/housing/homeownership",
        "is_active": True, "is_featured": False, "sort_order": 14,
        "last_verified": "2025-12-01",
        "notes": "Howard County has one of the largest county DPA amounts in Maryland.",
    },
    # ── Washington DC Programs ────────────────────────────────────────────────
    {
        "program_name": "HPAP — Home Purchase Assistance Program",
        "administering_agency": "DC Department of Housing and Community Development (DHCD)",
        "state": "DC", "county": None, "city": "Washington",
        "dpa_type": "deferred",
        "assistance_amount": "Up to $202,000+ in deferred financing",
        "assistance_amount_max": 202000,
        "target_buyer": "Low-to-moderate income DC residents, first-time buyers",
        "income_limit_notes": "Income limits based on DC AMI: Very Low (<50%), Low (<80%), Moderate (<110%). Larger amounts for lower income tiers.",
        "credit_score_min": 620,
        "property_location_notes": "Must purchase and reside in Washington DC",
        "property_type_notes": "Single family, condo, cooperative",
        "eligible_loan_types": "FHA, Conventional",
        "repayment_notes": "Deferred 5 years, then low monthly payments. Amount forgiven in many cases based on income tier.",
        "education_required": True,
        "other_requirements": "Must be DC resident for 12+ months. Cannot own other real property.",
        "program_url": "https://dhcd.dc.gov/service/hpap-home-purchase-assistance-program",
        "is_active": True, "is_featured": True, "sort_order": 20,
        "last_verified": "2025-12-01",
        "notes": "HPAP is the flagship DC DPA — amounts can cover entire down payment for income-qualified buyers.",
    },
    {
        "program_name": "DC Open Doors",
        "administering_agency": "DC Housing Finance Agency (DCHFA)",
        "state": "DC", "county": None, "city": "Washington",
        "dpa_type": "second_lien",
        "assistance_amount": "3%–3.5% of purchase price as deferred second trust",
        "assistance_amount_max": None,
        "target_buyer": "Moderate-to-middle income buyers; first-time and repeat buyers eligible",
        "income_limit_notes": "Income limits up to ~$132,360–$183,760 depending on household size (110%–130% AMI).",
        "credit_score_min": 640,
        "property_location_notes": "Must purchase in Washington DC",
        "property_type_notes": "Single family, condo, attached, PUD",
        "eligible_loan_types": "FHA, Conventional (DC Open Doors first mortgage required)",
        "repayment_notes": "Deferred — no payments while in first mortgage. Due at payoff, sale, or refi.",
        "education_required": False,
        "other_requirements": "Must use DCHFA-approved first mortgage product.",
        "program_url": "https://www.dchfa.org/homebuyers/dc-open-doors/",
        "is_active": True, "is_featured": True, "sort_order": 21,
        "last_verified": "2025-12-01",
        "notes": "Higher income limits than HPAP — good option for middle-income DC buyers.",
    },
    {
        "program_name": "EAHP — Employer-Assisted Housing Program",
        "administering_agency": "DC Department of Human Resources",
        "state": "DC", "county": None, "city": "Washington",
        "dpa_type": "deferred",
        "assistance_amount": "$10,000 forgivable loan + up to $5,000 closing cost assistance",
        "assistance_amount_max": 15000,
        "target_buyer": "DC government employees (full-time only)",
        "income_limit_notes": "Must be full-time DC government employee. Income limits may apply.",
        "credit_score_min": 620,
        "property_location_notes": "Must purchase in Washington DC",
        "property_type_notes": "Single family, condo, townhouse",
        "eligible_loan_types": "FHA, Conventional, VA",
        "repayment_notes": "$10,000 forgivable over 5 years. Closing cost portion is a deferred loan.",
        "education_required": False,
        "other_requirements": "Must be DC government employee for minimum period.",
        "program_url": "https://dchr.dc.gov/page/employer-assisted-housing-program",
        "is_active": True, "is_featured": False, "sort_order": 22,
        "last_verified": "2025-12-01",
        "notes": "Exclusive to DC government employees — teachers, police, fire, etc.",
    },
]


@router.post("/admin/seed-md-dc", status_code=201)
async def seed_md_dc(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Seed known Maryland and DC DPA programs.
    Idempotent — skips any program whose name already exists in the DB.
    """
    created = 0
    skipped = 0

    for entry in MD_DC_SEED:
        result = await db.execute(
            select(DpaProgram).where(DpaProgram.program_name == entry["program_name"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            skipped += 1
            continue

        entry_data = {k: v for k, v in entry.items() if k != "dpa_type"}
        dpa_type = DpaType(entry["dpa_type"])
        program = DpaProgram(**entry_data, dpa_type=dpa_type)
        db.add(program)
        created += 1

    await db.commit()
    return {
        "success": True,
        "created": created,
        "skipped": skipped,
        "message": f"Seeded {created} programs ({skipped} already existed).",
    }
