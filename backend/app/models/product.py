import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class ProductType(str, enum.Enum):
    DPA = "dpa"
    FHA = "fha"
    CONVENTIONAL = "conventional"
    VA = "va"
    USDA = "usda"
    DSCR = "dscr"
    HELOC = "heloc"
    CASHOUT_REFI = "cashout_refi"
    RATE_TERM_REFI = "rate_term_refi"
    BANK_STATEMENT = "bank_statement"
    ITIN = "itin"
    INVESTOR = "investor"
    JUMBO = "jumbo"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_type: Mapped[ProductType] = mapped_column(SAEnum(ProductType), nullable=False)
    audience: Mapped[str | None] = mapped_column(Text)
    basic_eligibility: Mapped[str | None] = mapped_column(Text)
    benefits: Mapped[str | None] = mapped_column(Text)
    risks_limitations: Mapped[str | None] = mapped_column(Text)
    cta_language: Mapped[str | None] = mapped_column(Text)
    prohibited_claims: Mapped[str | None] = mapped_column(Text)
    source_notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    disclaimers: Mapped[list["ProductDisclaimer"]] = relationship("ProductDisclaimer", back_populates="product", cascade="all, delete-orphan")


class ProductDisclaimer(Base):
    __tablename__ = "product_disclaimers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(String, ForeignKey("products.id"), nullable=False)
    disclaimer_text: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str | None] = mapped_column(String(100))
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped["Product"] = relationship("Product", back_populates="disclaimers")
