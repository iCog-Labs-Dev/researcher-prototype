from __future__ import annotations

import uuid
from sqlalchemy import ForeignKey, Text, Boolean, Float, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, CITEXT

from .base import Base


class ResearchTopic(Base):
    __tablename__ = "research_topics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chat_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_context: Mapped[str] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    is_active_research: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    research_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_researched: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    # Parent-child relationship for expansion topics
    is_child: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_topics.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_research_topics_user_name"),
    )
