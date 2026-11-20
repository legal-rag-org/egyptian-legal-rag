import uuid

from .insurance_rag_base import SQLAlchemyBase

from sqlalchemy import  Column, Integer, String, DateTime, Text, ForeignKey, func

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import Index



class AgentExecution(SQLAlchemyBase):

    __tablename__ = "agent_executions"

    agent_execution_id = Column(Integer, primary_key=True, autoincrement=True)
    agent_execution_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4,  unique=True, nullable=False)


    execution_conversation_id = Column(Integer, ForeignKey("conversations.conversation_id"), nullable=False)

    user_message_id = Column(Integer, ForeignKey("messages.message_id"), nullable=True)

    assistant_message_id = Column(Integer, ForeignKey("messages.message_id"), nullable=True)

    status = Column(String(30), nullable=False, default="running")

    total_iterations = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    completed_at = Column(DateTime(timezone=True), nullable=True)

    error = Column(Text, nullable=True)

    conversation = relationship(
        "Conversation",
        back_populates="agent_executions"
    )

    user_message = relationship(
        "Message",
        foreign_keys=[user_message_id]
    )

    assistant_message = relationship(
        "Message",
        foreign_keys=[assistant_message_id]
    )

    steps = relationship(
        "AgentStep",
        back_populates="execution",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_execution_conversation_id", execution_conversation_id),
    )