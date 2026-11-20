import uuid

from .insurance_rag_base import SQLAlchemyBase

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB



from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Index



class AgentStep(SQLAlchemyBase):

    __tablename__ = "agent_steps"

    agent_step_id = Column(Integer, primary_key=True, autoincrement=True)
    agent_step_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4,  unique=True, nullable=False)


    step_execution_id = Column(
        Integer,
        ForeignKey("agent_executions.agent_execution_id"),
        nullable = False,
    )

    iteration = Column(Integer, nullable=False)

    step_type = Column(String(50), nullable=False)

    tool_name = Column(String(100), nullable=True)

    tool_call_id = Column(String(255), nullable=True)

    input_data = Column(JSONB, nullable=True)

    output_data = Column(JSONB, nullable=True)

    status = Column(String(30), nullable=False)

    duration_ms = Column(Integer, nullable=True)

    error = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    execution = relationship(
        "AgentExecution",
        back_populates="steps"
    )

    __table_args__ = (
        Index("ix_step_execution_id", step_execution_id),
    )

