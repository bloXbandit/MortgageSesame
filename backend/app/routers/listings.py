"""
Property listings endpoints.
- GET  /listings/           — public list (filter by status, featured)
- GET  /listings/{id}       — public detail
- GET  /listings/{id}/calculate — run mock closing cost calculator (public)
- POST /listings/           — admin create
- PATCH /listings/{id}      — admin update
- DELETE /listings/{id}     — admin delete
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.hub import Listing, ListingStatus
from app.models.contact import Contact, ContactType
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.calculator import calc_scenarios, CalcInput

router = APIRouter(prefix="/listings", tags=["listings"])


def _listing_dict(l: Listing) -> dict:
    return {
        "id": l.id,
        "address": l.address,
        "city": l.city,
        "state": l.state,
        "county": l.county,
        "zip_code": l.zip_code,
        "list_price": l.list_price,
        "bedrooms": l.bedrooms,
        "bathrooms": l.bathrooms,
        "sqft": l.sqft,
        "property_type": l.property_type,
        "photo_url": l.photo_url,
        "zillow_url": l.zillow_url,
        "zillow_id": l.zillow_id,
        "description": l.description,
        "status": l.status,
        "is_featured": l.is_featured,
        "hoa_monthly": l.hoa_monthly,
        "annual_taxes": l.annual_taxes,
        "annual_insurance": l.annual_insurance,
        "listing_agent_contact_id": l.listing_agent_contact_id,
        "listing_agent_name": l.listing_agent_name,
        "listing_agent_phone": l.listing_agent_phone,
        "listing_agent_email": l.listing_agent_email,
        "tags": l.tags or [],
        "created_at": l.created_at.isoformat() if l.created_at else None,
        "updated_at": l.updated_at.isoformat() if l.updated_at else None,
    }


@router.get("/")
async def list_listings(
    status: Optional[str] = Query(None, description="Filter by status: active, under_contract, sold, coming_soon"),
    featured_only: bool = Query(False),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Listing).order_by(desc(Listing.is_featured), desc(Listing.created_at))
    if status:
        try:
            q = q.where(Listing.status == ListingStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    else:
        # Default: exclude sold listings from public view
        q = q.where(Listing.status != ListingStatus.SOLD)
    if featured_only:
        q = q.where(Listing.is_featured == True)
    if city:
        q = q.where(Listing.city.ilike(f"%{city}%"))
    if state:
        q = q.where(Listing.state.ilike(state))

    result = await db.execute(q)
    return [_listing_dict(l) for l in result.scalars().all()]


@router.get("/{listing_id}")
async def get_listing(listing_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_dict(listing)


@router.get("/{listing_id}/calculate")
async def calculate_listing(
    listing_id: str,
    rate_conventional: float = Query(7.00, description="30yr conventional rate %"),
    rate_fha: float = Query(6.75, description="30yr FHA rate %"),
    rate_dscr: float = Query(7.75, description="DSCR rate %"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate FHA / Conventional / DSCR mock closing cost scenarios for a listing.
    Uses listing's stored tax/insurance/HOA data when available; estimates otherwise.
    PUBLIC endpoint — no auth required.
    """
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    inp = CalcInput(
        purchase_price=listing.list_price,
        annual_taxes=listing.annual_taxes,
        annual_insurance=listing.annual_insurance,
        hoa_monthly=listing.hoa_monthly or 0,
        rate_conventional=rate_conventional,
        rate_fha=rate_fha,
        rate_dscr=rate_dscr,
        down_pct_conventional=listing.override_down_pct_conventional or 5.0,
        down_pct_fha=listing.override_down_pct_fha or 3.5,
    )
    result_data = calc_scenarios(inp)
    # Attach listing context
    result_data["listing"] = {
        "id": listing.id,
        "address": listing.address,
        "city": listing.city,
        "state": listing.state,
        "list_price": listing.list_price,
    }
    return result_data


# ── Realtor contact picker (admin) ───────────────────────────────────────────

@router.get("/realtors")
async def list_realtors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all realtor contacts for the listing agent picker dropdown.
    Sorted alphabetically by last name then first name.
    """
    result = await db.execute(
        select(Contact)
        .where(Contact.contact_type == ContactType.REALTOR)
        .order_by(Contact.last_name, Contact.first_name)
    )
    realtors = result.scalars().all()
    return [
        {
            "id":      r.id,
            "name":    f"{r.first_name or ''} {r.last_name or ''}".strip() or r.email or "—",
            "phone":   r.phone,
            "email":   r.email,
            "company": r.company,
        }
        for r in realtors
    ]


# ── Admin CRUD ────────────────────────────────────────────────────────────────

class ListingCreate(BaseModel):
    address: str
    city: str
    state: str = "MD"
    county: Optional[str] = None
    zip_code: Optional[str] = None
    list_price: float
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    sqft: Optional[int] = None
    property_type: Optional[str] = None  # single family, condo, townhouse, multi-family
    photo_url: Optional[str] = None
    zillow_url: Optional[str] = None
    zillow_id: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"
    is_featured: bool = True
    hoa_monthly: Optional[float] = None
    annual_taxes: Optional[float] = None
    annual_insurance: Optional[float] = None
    listing_agent_contact_id: Optional[str] = None
    listing_agent_name: Optional[str] = None
    listing_agent_phone: Optional[str] = None
    listing_agent_email: Optional[str] = None
    override_down_pct_conventional: Optional[float] = None
    override_down_pct_fha: Optional[float] = None
    tags: Optional[list] = None


class ListingUpdate(BaseModel):
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    zip_code: Optional[str] = None
    list_price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    sqft: Optional[int] = None
    property_type: Optional[str] = None
    photo_url: Optional[str] = None
    zillow_url: Optional[str] = None
    zillow_id: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    is_featured: Optional[bool] = None
    hoa_monthly: Optional[float] = None
    annual_taxes: Optional[float] = None
    annual_insurance: Optional[float] = None
    listing_agent_contact_id: Optional[str] = None
    listing_agent_name: Optional[str] = None
    listing_agent_phone: Optional[str] = None
    listing_agent_email: Optional[str] = None
    override_down_pct_conventional: Optional[float] = None
    override_down_pct_fha: Optional[float] = None
    tags: Optional[list] = None


@router.post("/", status_code=201)
async def create_listing(
    data: ListingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = Listing(**data.model_dump(), created_by=current_user.id)
    db.add(listing)
    await db.commit()
    await db.refresh(listing)
    return _listing_dict(listing)


@router.patch("/{listing_id}")
async def update_listing(
    listing_id: str,
    data: ListingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(listing, k, v)

    await db.commit()
    await db.refresh(listing)
    return _listing_dict(listing)


@router.delete("/{listing_id}", status_code=204)
async def delete_listing(
    listing_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    await db.delete(listing)
    await db.commit()
