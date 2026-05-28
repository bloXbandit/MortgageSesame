import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Enum as SAEnum, ForeignKey, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class LoanInterestType(str, enum.Enum):
    PURCHASE = "purchase"
    REFINANCE = "refinance"
    HELOC = "heloc"
    DSCR_INVESTOR = "dscr_investor"
    DPA = "dpa"
    FHA = "fha"
    CONVENTIONAL = "conventional"
    VA = "va"
    USDA = "usda"


class PropertyGoal(str, enum.Enum):
    PRIMARY_RESIDENCE = "primary_residence"
    INVESTMENT = "investment"
    VACATION = "vacation"
    REFINANCE_EXISTING = "refinance_existing"


class CreditScoreRange(str, enum.Enum):
    BELOW_580 = "below_580"
    R580_619 = "580_619"
    R620_659 = "620_659"
    R660_699 = "660_699"
    R700_739 = "700_739"
    R740_PLUS = "740_plus"
    UNKNOWN = "unknown"


class IncomeRange(str, enum.Enum):
    BELOW_30K = "below_30k"
    R30K_50K = "30k_50k"
    R50K_75K = "50k_75k"
    R75K_100K = "75k_100k"
    R100K_150K = "100k_150k"
    R150K_PLUS = "150k_plus"
    UNKNOWN = "unknown"


class Timeline(str, enum.Enum):
    ASAP = "asap"
    WITHIN_30_DAYS = "within_30_days"
    WITHIN_90_DAYS = "within_90_days"
    WITHIN_6_MONTHS = "within_6_months"
    WITHIN_1_YEAR = "within_1_year"
    JUST_EXPLORING = "just_exploring"


class LeadIntake(Base):
    __tablename__ = "lead_intakes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    state: Mapped[str | None] = mapped_column(String(50))
    county: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    loan_interest_type: Mapped[LoanInterestType | None] = mapped_column(SAEnum(LoanInterestType))
    timeline: Mapped[Timeline | None] = mapped_column(SAEnum(Timeline))
    credit_score_range: Mapped[CreditScoreRange | None] = mapped_column(SAEnum(CreditScoreRange))
    income_range: Mapped[IncomeRange | None] = mapped_column(SAEnum(IncomeRange))
    current_rent_mortgage: Mapped[str | None] = mapped_column(String(100))
    cash_available: Mapped[str | None] = mapped_column(String(100))
    property_goal: Mapped[PropertyGoal | None] = mapped_column(SAEnum(PropertyGoal))
    consent_email: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_sms: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_call: Mapped[bool] = mapped_column(Boolean, default=False)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(500))
    utm_source: Mapped[str | None] = mapped_column(String(100))
    utm_campaign: Mapped[str | None] = mapped_column(String(100))
    raw_answers: Mapped[dict | None] = mapped_column(JSON)
    contact_id: Mapped[str | None] = mapped_column(String, ForeignKey("contacts.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    score: Mapped["LeadScore"] = relationship("LeadScore", back_populates="intake", uselist=False, cascade="all, delete-orphan")


class LeadScore(Base):
    __tablename__ = "lead_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    intake_id: Mapped[str] = mapped_column(String, ForeignKey("lead_intakes.id"), unique=True, nullable=False)
    score_value: Mapped[float | None] = mapped_column(Float)
    score_label: Mapped[str | None] = mapped_column(String(50))
    recommended_product: Mapped[str | None] = mapped_column(String(255))
    readiness_score: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)
    questions_for_call: Mapped[list | None] = mapped_column(JSON)
    recommended_cta: Mapped[str | None] = mapped_column(String(500))
    compliance_response: Mapped[str | None] = mapped_column(Text)
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scored_by: Mapped[str] = mapped_column(String(50), default="ai")

    intake: Mapped["LeadIntake"] = relationship("LeadIntake", back_populates="score")
