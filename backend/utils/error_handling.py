"""
Error handling utility for LangGraph nodes.
"""
from typing import Optional
import openai
from langgraph.graph import END
from services.logging_config import get_logger
from services.nodes.base import ChatState

logger = get_logger(__name__)

def check_error(state: ChatState) -> str:
    """
    Check if the state has an error.
    Returns END if error exists, else "continue".
    """
    if state.get("error"):
        logger.warning(f"🚨 Graph stopping due to error: {state['error']}")
        return END
    return "continue"

def handle_node_error(e: Exception, state: ChatState, node_name: str) -> ChatState:
    """
    Handle exceptions in LangGraph nodes by logging and setting the error state.
    
    Args:
        e: The exception that occurred
        state: The current ChatState
        node_name: The name of the node where the error occurred
        
    Returns:
        The updated ChatState with the error field set
    """
    error_msg = f"Error in {node_name}: {str(e)}"
    logger.error(f"❌ {error_msg}")
    
    # Check for specific OpenAI errors that should definitely stop execution
    if isinstance(e, (openai.APIConnectionError, openai.RateLimitError, openai.AuthenticationError)):
        logger.critical(f"🚨 Critical LLM API Error in {node_name}: {type(e).__name__}")
        
    # Always set the error flag in state to stop the graph execution
    # (assuming the graph is configured to check this flag)
    state["error"] = error_msg
    
    # Also mark the specific module result as failed if it exists
    if "module_results" not in state:
        state["module_results"] = {}
        
    # We try to map the node name to a module result key if possible
    # This is a best-effort mapping
    module_key = node_name.replace("_node", "")
    if module_key not in state["module_results"]:
         state["module_results"][module_key] = {}
         
    state["module_results"][module_key]["success"] = False
    state["module_results"][module_key]["error"] = str(e)
    
    return state
