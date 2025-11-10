import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

from .base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    personality: Mapped[dict[str, Any] | None] = mapped_column(MutableDict.as_mutable(JSONB))
    preferences: Mapped[dict[str, Any] | None] = mapped_column(MutableDict.as_mutable(JSONB))
    meta_data: Mapped[dict[str, Any] | None] = mapped_column(MutableDict.as_mutable(JSONB))
