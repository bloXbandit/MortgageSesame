import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Enum as SAEnum, ForeignKey, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum
from typing import Optional


class AgentActionType(str, enum.Enum):
    READ_PRODUCTS = "read_products"
    READ_CAMPAIGNS = "read_campaigns"
    READ_CONTACTS = "read_contacts"
    RESEARCH_TARGET = "research_target"
    GENERATE_OUTREACH = "generate_outreach"
    GENERATE_CONTENT = "generate_content"
    SCORE_LEAD = "score_lead"
    CREATE_TASK = "create_task"
    QUEUE_ACTION = "queue_action"
    COMPLIANCE_CHECK = "compliance_check"
    REPORT_RUN = "report_run"
    LOG_EVENT = "log_event"
    VOICE_GENERATE = "voice_generate"


class AgentActionStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    APPROVED = "approved"


class ApprovalItemType(str, enum.Enum):
    OUTREACH_MESSAGE = "outreach_message"
    SOCIAL_POST = "social_post"
    CAMPAIGN_STEP = "campaign_step"
    AGENT_ACTION = "agent_action"
    CONTENT_ITEM = "content_item"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    run_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[AgentActionStatus] = mapped_column(SAEnum(AgentActionStatus), default=AgentActionStatus.PENDING)
    input_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    output_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    actions_count: Mapped[Optional[int]] = mapped_column()
    duration_ms: Mapped[Optional[float]] = mapped_column(Float)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    actions: Mapped[list["AgentAction"]] = relationship("AgentAction", back_populates="run", cascade="all, delete-orphan")


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String, ForeignKey("agent_runs.id"), nullable=False)
    action_type: Mapped[AgentActionType] = mapped_column(SAEnum(AgentActionType), nullable=False)
    status: Mapped[AgentActionStatus] = mapped_column(SAEnum(AgentActionStatus), default=AgentActionStatus.PENDING)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped["AgentRun"] = relationship("AgentRun", back_populates="actions")


class ApprovalQueue(Base):
    __tablename__ = "approval_queue"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    item_type: Mapped[ApprovalItemType] = mapped_column(SAEnum(ApprovalItemType), nullable=False)
    item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(500))
    preview: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    priority: Mapped[int] = mapped_column(default=0)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    reviewed_by: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    task_type: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default="open")
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    contact_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("contacts.id"))
    campaign_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("campaigns.id"))
    assigned_to: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"))
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
