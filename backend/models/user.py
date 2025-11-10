import uuid

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

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
