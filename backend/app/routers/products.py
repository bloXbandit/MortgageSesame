from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.product import Product, ProductDisclaimer, ProductType
from app.models.user import User
from app.middleware.auth import get_current_user
from app.middleware.audit import log_event

router = APIRouter(prefix="/products", tags=["products"])


class ProductCreate(BaseModel):
    name: str
    product_type: ProductType
    audience: Optional[str] = None
    basic_eligibility: Optional[str] = None
    benefits: Optional[str] = None
    risks_limitations: Optional[str] = None
    cta_language: Optional[str] = None
    prohibited_claims: Optional[str] = None
    source_notes: Optional[str] = None
    is_active: bool = True


class DisclaimerCreate(BaseModel):
    disclaimer_text: str
    channel: Optional[str] = None
    is_required: bool = True


@router.get("/")
async def list_products(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Product)
    if active_only:
        q = q.where(Product.is_active == True)
    result = await db.execute(q.order_by(Product.name))
    return [_serialize(p) for p in result.scalars().all()]


@router.get("/{product_id}")
async def get_product(product_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Product not found")
    return _serialize(p)


@router.post("/", status_code=201)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    p = Product(**data.model_dump(), created_by=current_user.id)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    await log_event(db, "product.create", actor_type="user", actor_id=current_user.id,
                    resource_type="product", resource_id=p.id)
    await db.commit()
    return _serialize(p)


@router.patch("/{product_id}")
async def update_product(product_id: str, data: ProductCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Product not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.commit()
    await db.refresh(p)
    await log_event(db, "product.update", actor_type="user", actor_id=current_user.id,
                    resource_type="product", resource_id=p.id)
    await db.commit()
    return _serialize(p)


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Product not found")
    await db.delete(p)
    await db.commit()


@router.post("/{product_id}/disclaimers", status_code=201)
async def add_disclaimer(product_id: str, data: DisclaimerCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    d = ProductDisclaimer(product_id=product_id, **data.model_dump())
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return {"id": d.id, "disclaimer_text": d.disclaimer_text}


def _serialize(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "product_type": p.product_type,
        "audience": p.audience,
        "basic_eligibility": p.basic_eligibility,
        "benefits": p.benefits,
        "risks_limitations": p.risks_limitations,
        "cta_language": p.cta_language,
        "prohibited_claims": p.prohibited_claims,
        "source_notes": p.source_notes,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
