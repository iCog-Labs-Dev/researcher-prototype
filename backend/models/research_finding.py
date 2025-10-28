from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import String, Boolean, Float, UniqueConstraint, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ResearchFinding(Base):
    __tablename__ = "research_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Link to file-store finding id for cross-reference
    finding_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Engagement flags captured in DB for aggregation
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bookmarked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    integrated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Metrics
    research_time: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "finding_id", name="uq_research_finding_user_finding"),
        Index("ix_findings_user_topic", "user_id", "topic_name"),
        Index("ix_findings_time", "research_time"),
    )


