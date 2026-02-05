"""
Research query generator node for creating optimized research queries for autonomous research.
"""

from datetime import datetime
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

import config
from .base import ChatState
from utils.helpers import get_current_datetime_str
from utils.error_handling import is_llm_error
from services.prompt_cache import PromptCache
from services.logging_config import get_logger

logger = get_logger(__name__)


def research_query_generator_node(state: ChatState) -> ChatState:
    """Generate an optimized research query based on topic metadata."""
    logger.info("🔍 Research Query Generator: Creating optimized research query")
    
    # Get research metadata
    research_metadata = state.get("workflow_context", {}).get("research_metadata", {})
    topic_name = research_metadata.get("topic_name", "Unknown Topic")
    topic_description = research_metadata.get("topic_description", "")
    
    # Get research context from workflow_context
    research_context = state["workflow_context"].get("research_context", {})
    last_researched = research_context.get("last_researched")
    
    # Format last research time
    if last_researched:
        last_research_time = last_researched
    else:
        last_research_time = "Never"
    
    logger.info(f"🔍 Research Query Generator: Generating query for '{topic_name}' (last researched: {last_research_time})")
    
    try:
        # Create the prompt for research query generation
        prompt = PromptCache.get("RESEARCH_QUERY_GENERATION_PROMPT").format(
            current_time=get_current_datetime_str(),
            topic_name=topic_name,
            topic_description=topic_description,
            last_research_time=last_research_time
        )
        
        # Initialize the LLM for query generation
        llm = ChatOpenAI(
            model=config.RESEARCH_MODEL,
            temperature=0.3,
            max_tokens=150,
            api_key=config.OPENAI_API_KEY
        )
        
        # Generate the research query
        messages = [SystemMessage(content=prompt)]
        response = llm.invoke(messages)
        research_query = response.content.strip()
        
        if not research_query:
            # Empty response is treated as an error in strict mode
            raise ValueError("Empty response from LLM for research query generation")
        
        # Store the generated query in workflow context
        state["workflow_context"]["refined_search_query"] = research_query
        
        # Update the synthetic messages with the generated query
        if state.get("messages") and len(state["messages"]) > 1:
            # Update the human message with the generated query
            state["messages"][-1].content = research_query
        
        logger.info(f"🔍 Research Query Generator: ✅ Generated query: '{research_query[:100]}...'")
        
        # Mark the query generation as successful
        state["module_results"]["research_query_generator"] = {
            "success": True,
            "query": research_query,
            "topic_name": topic_name
        }
        
    except Exception as e:
        if is_llm_error(e):
            logger.warning(f"🔍 Research Query Generator: LLM error, stopping research: {e}")
            state["error_llm"] = str(e)
            return state
        logger.warning(f"🔍 Research Query Generator: Non-LLM error, using topic as fallback query: {e}")
        fallback_query = research_metadata.get("topic_name", "Unknown Topic") or topic_name
        state["workflow_context"]["refined_search_query"] = fallback_query
        state.setdefault("module_results", {})["research_query_generator"] = {
            "success": True,
            "query": fallback_query,
            "topic_name": topic_name,
        }
    return state