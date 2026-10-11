from .insurance_rag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, func, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

class Conversation(SQLAlchemyBase):

    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4,  unique=True, nullable=False)

    title = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    summary = Column(Text, nullable=True)

    conversation_project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    conversation_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    project = relationship(
        "Project",
        back_populates="conversations"
    )

    messages = relationship(
        "Message",
        back_populates="conversation"
    )

    user = relationship(
        "User",
        back_populates="conversations"
    )


