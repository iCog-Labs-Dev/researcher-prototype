from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional, List


class BookmarkUpdateInOut(BaseModel):
    """Toggle bookmark for a finding."""
    bookmarked: bool


class MotivationConfigUpdate(BaseModel):
    """Partial update for motivation config."""
    threshold: Optional[float] = None
    boredom_rate: Optional[float] = None
    curiosity_decay: Optional[float] = None
    tiredness_decay: Optional[float] = None
    satisfaction_decay: Optional[float] = None


class ExpansionIn(BaseModel):
    """Generate adjacent topics."""
    root_topic: Dict[str, Any]
    create_topics: Optional[bool] = False
    enable_research: Optional[bool] = False
    limit: Optional[int] = None


class ResearchFindingItemOut(BaseModel):
    """Output body for a research finding."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    topic_name: str
    read: bool
    bookmarked: bool
    quality_score: Optional[float] = None
    findings_content: Optional[str] = None
    formatted_content: Optional[str] = None
    findings_summary: Optional[str] = None
    research_query: Optional[str] = None
    source_urls: Optional[List[str]] = None
    citations: Optional[List[str]] = None
    key_insights: Optional[List[str]] = None
    created_at: datetime


class ResearchFindingsOut(BaseModel):
    """Output body for getting research findings."""
    total_findings: int
    findings: List[ResearchFindingItemOut]
