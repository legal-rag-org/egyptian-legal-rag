import uuid

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .insurance_rag_base import SQLAlchemyBase


class UserMemory(SQLAlchemyBase):
    __tablename__ = "user_memories"

    memory_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    memory_uuid = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )

    content = Column(
        Text,
        nullable=False,
    )

    embedding = Column(
        Vector(1024),
        nullable=False,
    )

    memory_type = Column(
        String(50),
        nullable=False,
    )

    importance = Column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    memory_user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    source_conversation_id = Column(
        Integer,
        ForeignKey(
            "conversations.conversation_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="memories",
    )

    source_conversation = relationship(
        "Conversation",
        back_populates="source_memories",
    )

    __table_args__ = (
        CheckConstraint(
            "importance BETWEEN 1 AND 5",
            name="ck_user_memory_importance",
        ),
        CheckConstraint(
            "memory_type IN ('preference', 'goal', 'project', 'fact', 'constraint')",
            name="ck_user_memory_type",
        ),
        Index(
            "ix_user_memories_user_active",
            "memory_user_id",
            "is_active",
        ),
    )
