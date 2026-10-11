from .insurance_rag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, func, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid


class User(SQLAlchemyBase):

    __tablename__ = "users"

    user_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_uuid = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )

    username = Column(
        String(100),
        unique=True,
        nullable=False,
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
    )

    password_hash = Column(
        String(255),
        nullable=False,
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

    conversations = relationship(
        "Conversation",
        back_populates="user"
    )