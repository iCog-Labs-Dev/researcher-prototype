import uuid
from typing import Any, Optional, Union
from sqlalchemy import String, Text, Float, Boolean, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TopicScore(Base):
    """Stores per-topic motivation scores and metadata."""
    __tablename__ = "topic_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_topics.id", ondelete="CASCADE"), nullable=False, index=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    
    topic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Per-topic motivation scores
    motivation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    engagement_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    staleness_pressure: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Topic metadata
    last_researched: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    staleness_coefficient: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_active_research: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Research metadata
    total_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    read_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bookmarked_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    integrated_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Quality metrics
    average_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_quality_update: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Additional metadata
    meta_data: Mapped[Union[dict[str, Any], None]] = mapped_column(MutableDict.as_mutable(JSONB))

    __table_args__ = (
        UniqueConstraint('user_id', 'topic_name', name='uq_topic_score_user_topic'),
        Index('ix_topic_scores_user_active', 'user_id', 'is_active_research'),
        Index('ix_topic_scores_motivation', 'motivation_score'),
        Index('ix_topic_scores_last_researched', 'last_researched'),
    )


class MotivationConfig(Base):
    """Stores motivation system configuration parameters."""
    __tablename__ = "motivation_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Global motivation parameters
    boredom_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0002)
    curiosity_decay: Mapped[float] = mapped_column(Float, nullable=False, default=0.0002)
    tiredness_decay: Mapped[float] = mapped_column(Float, nullable=False, default=0.0002)
    satisfaction_decay: Mapped[float] = mapped_column(Float, nullable=False, default=0.0002)
    
    # Thresholds
    global_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=2.0)
    topic_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    
    # Topic-level parameters
    engagement_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    quality_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    staleness_scale: Mapped[float] = mapped_column(Float, nullable=False, default=0.0001)
    
    # Timing parameters
    check_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    
    # Configuration metadata
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Additional configuration
    config_data: Mapped[Union[dict[str, Any], None]] = mapped_column(MutableDict.as_mutable(JSONB))

    __table_args__ = (
        Index('ix_motivation_configs_default', 'is_default'),
    )
