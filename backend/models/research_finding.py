from __future__ import annotations
import uuid
from typing import Optional
from sqlalchemy import String, Boolean, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TEXT
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.mutable import MutableList

from .base import Base


class ResearchFinding(Base):
    __tablename__ = "research_findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_topics.id", ondelete="CASCADE"), nullable=False, index=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Link to file-store finding id for cross-reference
    finding_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Engagement flags captured in DB for aggregation
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bookmarked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    integrated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Result data
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    findings_content: Mapped[Optional[str]] = mapped_column(Text)
    formatted_content: Mapped[Optional[str]] = mapped_column(Text)
    research_query: Mapped[Optional[str]] = mapped_column(Text)
    findings_summary: Mapped[Optional[str]] = mapped_column(Text)
    source_urls: Mapped[list[str]] = mapped_column(MutableList.as_mutable(ARRAY(TEXT)), nullable=True)
    citations: Mapped[list[str]] = mapped_column(MutableList.as_mutable(ARRAY(TEXT)), nullable=True)
    key_insights: Mapped[list[str]] = mapped_column(MutableList.as_mutable(ARRAY(TEXT)), nullable=True)
    search_sources: Mapped[list[dict]] = mapped_column(MutableList.as_mutable(JSONB), nullable=True)
