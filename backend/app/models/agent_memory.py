"""
Agent Memory — persistent logs and ask-queue for Clawdbot / Hermes.

AgentMemoryLog  — one row per agent run. Gives the agent memory between sessions.
AgentAsk        — questions/requests the agent posts to the operator (Kenneth).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from app.database import Base


class AgentMemoryLog(Base):
    __tablename__ = "agent_memory_logs"

    id         = Column(Integer, primary_key=True)
    run_id     = Column(String, index=True)          # UUID — ties to a specific agent session
    run_type   = Column(String, index=True)          # daily_check | weekly_audit | campaign_build | lead_review | custom
    summary    = Column(Text)                        # Plain-English summary of what the agent did
    actions_taken    = Column(JSON, default=list)    # [{action, result, timestamp}, ...]
    results          = Column(JSON, default=dict)    # Key metrics: leads_reviewed, campaigns_built, etc.
    needs_from_operator = Column(JSON, default=list) # Items the agent couldn't resolve alone
    status     = Column(String, default="completed") # completed | needs_input | failed
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentAsk(Base):
    __tablename__ = "agent_asks"

    id          = Column(Integer, primary_key=True)
    question    = Column(Text)                       # What the agent is asking
    context     = Column(Text)                       # Why it needs this
    urgency     = Column(String, default="normal")   # low | normal | high
    category    = Column(String, default="general")  # budget | content | access | decision | other
    is_resolved = Column(Boolean, default=False)
    resolution  = Column(Text, nullable=True)        # Operator's answer / action taken
    created_at  = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
