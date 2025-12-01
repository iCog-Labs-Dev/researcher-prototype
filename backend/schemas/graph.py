from pydantic import BaseModel
from typing import Dict, Any, List


class GraphIn(BaseModel):
    """Request model for graph data."""
    type: str  # "user" or "group"
    id: str    # user_id or group_id


class GraphOut(BaseModel):
    """Response model for graph data."""
    triplets: List[Dict[str, Any]]
