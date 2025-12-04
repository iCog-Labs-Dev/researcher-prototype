from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CustomTopicIn(BaseModel):
    """Input model for creating a custom research topic."""
    name: str = Field(..., min_length=1, max_length=100, description="Name of the research topic")
    description: str = Field(..., min_length=10, max_length=500, description="Description of what the topic covers")
    confidence_score: Optional[float] = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    is_active_research: Optional[bool] = Field(default=False, description="Whether to enable research immediately")


class CustomTopicOut(BaseModel):
    """Output model for topic getting."""
    topic_id: UUID
    user_id: UUID
    name: str
    description: str
    confidence_score: float
    is_active_research: bool
    suggested_at: datetime


class TopicOnOffResearchOut(BaseModel):
    """Output model for topic getting."""


class TopicEnableOut(BaseModel):
    """Output body for updating active research."""
    enabled: bool


class TopicSuggestionItem(BaseModel):
    """Single suggested topic."""
    topic_id: UUID
    session_id: Optional[str] = None
    name: str
    description: str
    confidence_score: float
    conversation_context: Optional[str] = None
    is_active_research: Optional[bool] = None
    suggested_at: datetime
    last_researched: Optional[datetime] = None
    research_count: Optional[int] = None


class TopicSuggestionsByChatOut(BaseModel):
    """Output body for getting topic suggestions by chat."""
    total_count: int
    topic_suggestions: List[TopicSuggestionItem]


class TopicSuggestionsOut(BaseModel):
    """Output body for getting topic suggestions."""
    total_count: int
    sessions_count: int
    topic_suggestions: List[TopicSuggestionItem]


class TopicStatusOut(BaseModel):
    """Output body for getting topic status."""
    has_topics: bool
    topic_count: int


class ResearchTopicsByUserOut(BaseModel):
    """Output body for getting research topics by user."""
    total_count: int
    active_research_topics: List[TopicSuggestionItem]


class TopicStatsOut(BaseModel):
    """Output body for getting topic statistics."""
    total_topics: int
    total_sessions: int
    average_confidence_score: float
    oldest_topic_age_days: int


class TopTopicsOut(BaseModel):
    """Output body for getting top topics."""
    total_count: int
    available_count: int
    topics: List[TopicSuggestionItem]
