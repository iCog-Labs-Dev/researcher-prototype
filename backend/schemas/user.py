from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from uuid import UUID


class PersonalityConfig(BaseModel):
    """Configuration for AI personality."""
    style: str = "helpful"
    tone: str = "friendly"
    additional_traits: Optional[Dict[str, Any]] = {}


class ContentPreferences(BaseModel):
    """User content preferences."""
    research_depth: str = "balanced"  # quick, balanced, detailed
    source_types: Dict[str, float] = {
        "academic_papers": 0.7,
        "news_articles": 0.8,
        "expert_blogs": 0.7,
        "government_reports": 0.6,
        "industry_reports": 0.6
    }
    topic_categories: Dict[str, float] = {}


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
    content_preferences: ContentPreferences = ContentPreferences()
    format_preferences: FormatPreferences = FormatPreferences()
    interaction_preferences: InteractionPreferences = InteractionPreferences()


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
