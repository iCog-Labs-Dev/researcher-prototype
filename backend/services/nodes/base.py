"""
Base definitions and imports for all node modules.
"""

import os
from typing import Dict, List, Annotated, TypedDict, Optional, Any
from langchain_core.messages import BaseMessage

# Import our storage components
from storage.zep_manager import ZepManager
# Import our services
from services.user import UserService
from services.research import ResearchService, FindingPayload
from services.topic import TopicService

# Initialize storage components
zep_manager = ZepManager()

# Initialize services
user_service = UserService()
research_service = ResearchService()
topic_service = TopicService()


class ChatState(TypedDict):
    """Type definition for the chat state that flows through the graph."""

    messages: Annotated[List[BaseMessage], "The messages in the conversation using LangChain core message types"]
    model: Annotated[str, "The model to use for the conversation"]
    temperature: Annotated[float, "The temperature to use for generation"]
    max_tokens: Annotated[int, "The maximum number of tokens to generate"]
    personality: Annotated[Optional[Dict[str, Any]], "User's personality configuration"]
    current_module: Annotated[Optional[str], "The current active module"]
    module_results: Annotated[Dict[str, Any], "Results from different modules"]
    workflow_context: Annotated[Dict[str, Any], "Contextual data for the current workflow execution."]
    user_id: Annotated[Optional[str], "The ID of the current user"]
    routing_analysis: Annotated[Optional[Dict[str, Any]], "Analysis from the router"]
    thread_id: Annotated[Optional[str], "The thread ID for memory management"]
    memory_context: Annotated[Optional[str], "Memory context retrieved from Zep"]
    intent: Annotated[Optional[str], "The routing intent: chat, search, or analysis"]
    selected_sources: Annotated[Optional[List[str]], "Selected sources for search intent"]
    error: Annotated[Optional[str], "Error message if the pipeline failed"]
    error_llm: Annotated[Optional[str], "LLM/API error in research flow; routes to END when set"]
