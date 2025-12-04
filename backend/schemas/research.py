from pydantic import BaseModel
from typing import Dict, Any, Optional


class BookmarkUpdate(BaseModel):
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
