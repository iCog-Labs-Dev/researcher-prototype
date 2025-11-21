from typing import Dict, Literal, Optional, List
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from .user import PersonalityConfig


class UserSummary(BaseModel):
    """Summary of a user profile for list views."""
    id: UUID
    created_at: datetime
    display_name: str
    role: str
    personality: PersonalityConfig


class RoleInOut(BaseModel):
    """Role input/output body for updating a role."""
    role: Literal["user", "admin"]


class PromptUpdateIn(BaseModel):
    """Input body for updating a prompt's content."""
    content: str


class PromptTestIn(BaseModel):
    """Input body for testing a prompt by supplying template variables."""
    variables: Dict[str, str]


class PromptRecord(BaseModel):
    """Prompt record (content and metadata)."""
    name: str
    content: str
    category: str
    description: str
    variables: List[str]


class PromptMeta(BaseModel):
    """Lightweight prompt metadata for listings/grouped views."""
    name: str
    description: str
    variables: List[str]
    content_length: int


class PromptHistoryEntry(BaseModel):
    """Single historical version of prompt history."""
    created_at: datetime
    user: str
    content: str
    variables: List[str]


class PromptListOut(BaseModel):
    """Output for listing all prompts with category grouping."""
    total_prompts: int
    categories: Dict[str, List[PromptMeta]]
    prompts: Dict[str, PromptRecord]


class PromptHistoryOut(BaseModel):
    """Output containing the version history for a prompt."""
    prompt_name: str
    total_versions: int
    history: List[PromptHistoryEntry]


class PromptTestResult(BaseModel):
    """Result of testing a prompt."""
    success: bool
    formatted_prompt: Optional[str] = None
    original_prompt: Optional[str] = None
    variables_used: Optional[Dict[str, str]] = None
    missing_variables: Optional[List[str]] = None
    required_variables: Optional[List[str]] = None
    provided_variables: Optional[List[str]] = None
    error: Optional[str] = None


class PromptTestOut(BaseModel):
    """Output for prompt test."""
    prompt_name: str
    test_result: PromptTestResult


class PromptStatusOut(BaseModel):
    """Status summary of prompts."""
    status: str
    timestamp: datetime
    prompts_loaded: int
    categories: List[str]
