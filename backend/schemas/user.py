from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, Literal, List
from datetime import datetime
from uuid import UUID


class PersonalityConfig(BaseModel):
    """Configuration for AI personality."""
    style: str = "helpful"
    tone: str = "friendly"
    additional_traits: Optional[Dict[str, Any]] = None


class ContentPreferences(BaseModel):
    """User content preferences."""
    research_depth: str = "balanced"  # quick, balanced, detailed
    source_types: Dict[str, float] = Field(
        default_factory=lambda: {
            "academic_papers": 0.7,
            "news_articles": 0.8,
            "expert_blogs": 0.7,
            "government_reports": 0.6,
            "industry_reports": 0.6,
        }
    )
    topic_categories: Dict[str, float] = Field(default_factory=dict)


class FormatPreferences(BaseModel):
    """User format preferences."""
    response_length: str = "medium"  # short, medium, long
    detail_level: str = "balanced"  # concise, balanced, comprehensive
    formatting_style: str = "structured"  # structured, natural, bullet_points
    include_key_insights: bool = True


class InteractionPreferences(BaseModel):
    """User interaction preferences."""
    notification_frequency: str = "moderate"  # low, moderate, high


class PreferencesConfig(BaseModel):
    """Complete user preferences configuration."""
    content_preferences: ContentPreferences = Field(default_factory=ContentPreferences)
    format_preferences: FormatPreferences = Field(default_factory=FormatPreferences)
    interaction_preferences: InteractionPreferences = Field(default_factory=InteractionPreferences)


class UserProfile(BaseModel):
    """Complete user profile information."""
    id: UUID
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    personality: PersonalityConfig = Field(default_factory=PersonalityConfig)
    preferences: Optional[PreferencesConfig] = None


class UserSummary(BaseModel):
    """Summary of a user profile for list views."""
    id: UUID
    created_at: datetime
    display_name: str
    role: str
    personality: PersonalityConfig


class DisplayNameInOut(BaseModel):
    """Display name input/output body for updating display name."""
    display_name: str


class EmailInOut(BaseModel):
    """Email input/output body for updating email."""
    email: EmailStr


class RoleInOut(BaseModel):
    """Role input/output body for updating role."""
    role: Literal["user", "admin"]


class FeedbackSignals(BaseModel):
    """User feedback signals."""
    thumbs_feedback: Dict[str, int] = Field(default_factory=lambda: {"up": 0, "down": 0})


class InteractionSignals(BaseModel):
    """User interaction signals."""
    most_engaged_source_types: List[str] = Field(default_factory=list)
    follow_up_question_frequency: float = 0.0


class LearnedAdaptations(BaseModel):
    """Learned user adaptations."""
    tone_adjustments: Dict[str, str] = Field(default_factory=dict)


class EngagementAnalytics(BaseModel):
    """User engagement analytics."""
    feedback_signals: FeedbackSignals = Field(default_factory=FeedbackSignals)
    interaction_signals: InteractionSignals = Field(default_factory=InteractionSignals)
    learned_adaptations: LearnedAdaptations = Field(default_factory=LearnedAdaptations)
    user_overrides: Dict[str, Any] = Field(default_factory=dict)
    reading_patterns: Dict[str, Any] = Field(default_factory=dict)
    bookmarked_findings: List[Any] = Field(default_factory=list)
    bookmarks_by_topic: Dict[str, Any] = Field(default_factory=dict)
    link_clicks_by_topic: Dict[str, Any] = Field(default_factory=dict)
    recent_link_domains: List[Any] = Field(default_factory=list)
    integrations_by_topic: Dict[str, Any] = Field(default_factory=dict)
    integrated_findings: List[Any] = Field(default_factory=list)


class AdaptationLogEntry(BaseModel):
    """Single adaptation log entry."""
    timestamp: float
    adaptation_type: str
    change_made: str
    changes_detail: Optional[Dict[str, Any]] = None
    user_feedback: Optional[str] = None
    effectiveness_score: Optional[float] = None


class PreferenceEvolution(BaseModel):
    """Preference evolution tracking."""
    source_type_preferences: List[Dict[str, Any]] = Field(default_factory=list)
    format_preferences: List[Dict[str, Any]] = Field(default_factory=list)
    content_preferences: List[Dict[str, Any]] = Field(default_factory=list)


class PersonalizationHistory(BaseModel):
    """User personalization history."""
    adaptation_log: List[AdaptationLogEntry] = Field(default_factory=list)
    preference_evolution: PreferenceEvolution = Field(default_factory=PreferenceEvolution)


class PreferenceOverride(BaseModel):
    """Request to override a learned preference."""
    preference_type: str
    override_value: Any
    disable_learning: bool = False


class PersonalizationContext(BaseModel):
    """Personalization context for request processing."""
    content_preferences: ContentPreferences
    format_preferences: FormatPreferences
    interaction_preferences: InteractionPreferences
    learned_adaptations: LearnedAdaptations
    engagement_patterns: Dict[str, Any]


class LearnedBehaviors(BaseModel):
    """Learned user behavior."""
    source_preferences: Dict[str, float] = Field(default_factory=dict)
    engagement_patterns: Dict[str, Any] = Field(default_factory=dict)
    interaction_signals: InteractionSignals = Field(default_factory=InteractionSignals)


class LearningStats(BaseModel):
    """Learning statistics."""
    total_adaptations: int
    recent_activity: int


class PersonalizationTransparency(BaseModel):
    """Personalization transparency payload."""
    explicit_preferences: PreferencesConfig
    learned_behaviors: LearnedBehaviors
    adaptation_history: List[AdaptationLogEntry] = Field(default_factory=list)
    user_overrides: Dict[str, Any] = Field(default_factory=dict)
    learning_stats: LearningStats
