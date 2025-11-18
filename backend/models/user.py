import uuid
from typing import Any
from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.mutable import MutableDict

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    role: Mapped[str] = mapped_column(
        Enum("user", "admin", name="user_role"),
        default="user",
        nullable=False
    )

    profile = relationship("UserProfile", uselist=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    personality: Mapped[dict[str, Any] | None] = mapped_column(MutableDict.as_mutable(JSONB))
    preferences: Mapped[dict[str, Any] | None] = mapped_column(MutableDict.as_mutable(JSONB))
    meta_data: Mapped[dict[str, Any] | None] = mapped_column(MutableDict.as_mutable(JSONB))

    engagement_analytics: Mapped[dict[str, Any] | None] = mapped_column(MutableDict.as_mutable(JSONB))
    personalization_history: Mapped[dict[str, Any] | None] = mapped_column(MutableDict.as_mutable(JSONB))
