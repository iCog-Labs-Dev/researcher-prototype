from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from config import DEFAULT_MODEL
from .user import PersonalityConfig


class Message(BaseModel):
    """A chat message."""
    role: str
    content: str


class TopicSuggestion(BaseModel):
    """A suggested research topic extracted from conversation."""
    name: str
    description: str
    confidence_score: float


class ChatIn(BaseModel):
    """Input model for chat endpoint."""
    messages: List[Message] = Field(min_length=1, description="At least one message required")
    model: str = DEFAULT_MODEL
    temperature: float = 0.7
    max_tokens: int = 1000
    personality: Optional[PersonalityConfig] = None
    chat_id: Optional[UUID] = None


class ChatOut(BaseModel):
    """Output model for chat endpoint."""
    response: str
    model: str
    usage: Dict[str, Any] = {}
    module_used: Optional[str] = None
    routing_analysis: Optional[Dict[str, Any]] = None
    user_id: UUID
    chat_id: UUID
    suggested_topics: List[TopicSuggestion] = []
    follow_up_questions: List[str] = []


class ChatView(BaseModel):
    """View model for chats getting endpoint."""
    id: UUID
    name: str
    created_at: datetime
