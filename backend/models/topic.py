import uuid
from sqlalchemy import ForeignKey, Text, Boolean, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chat_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_context: Mapped[str] = mapped_column(Text)

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    research_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active_research: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
