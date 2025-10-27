from typing import Dict, Literal
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from .user import PersonalityConfig


class PromptUpdateRequest(BaseModel):
    content: str


class PromptTestRequest(BaseModel):
    variables: Dict[str, str]


class RestorePromptRequest(BaseModel):
    backup_filename: str


# new schemas to work with users
class UserSummary(BaseModel):
    """Summary of a user profile for list views."""
    id: UUID
    created_at: datetime
    display_name: str
    role: str
    personality: PersonalityConfig


class RoleInOut(BaseModel):
    """Role input/output body for updating role."""
    role: Literal["user", "admin"]
