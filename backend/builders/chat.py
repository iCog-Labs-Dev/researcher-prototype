"""
Chat graph builder module that constructs the LangGraph for the conversation flow.
"""

import os
from langgraph.graph import StateGraph, END
from langsmith import Client

from services.nodes.base import ChatState
from config import (
    LANGCHAIN_TRACING_V2,
    LANGCHAIN_API_KEY,
    LANGCHAIN_ENDPOINT,
    LANGCHAIN_PROJECT
)
from utils.helpers import visualize_langgraph
from services.logging_config import get_logger
# Import all node functions
from services.nodes.initializer import initializer_node
from services.nodes.multi_source_analyzer import multi_source_analyzer_node
from services.nodes.search_prompt_optimizer import search_prompt_optimizer_node
from services.nodes.analysis_task_refiner import analysis_task_refiner_node
from services.nodes.analyzer import analyzer_node
from services.nodes.integrator import integrator_node
from services.nodes.response_renderer import response_renderer_node
# Import specialized nodes
from services.nodes.source_coordinator import source_coordinator_node
from services.nodes.search_results_reviewer import search_results_reviewer_node
from services.nodes.evidence_summarizer import evidence_summarizer_node

logger = get_logger(__name__)


def setup_tracing():
    """Configure LangSmith tracing based on environment variables."""
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
    logger.info(f"🔍 LangSmith tracing enabled for project: {LANGCHAIN_PROJECT}")


def create_chat_graph():
    """Create a LangGraph graph for orchestrating multi-source information gathering."""
    
    # Configure LangSmith tracing if enabled
    if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
        setup_tracing()
    
    # Define the intent router function
    def intent_router(state: ChatState) -> str:
        """Route based on intent: chat, search, or analysis."""
        intent = state.get("intent", "chat")
        sources = state.get("selected_sources", [])
        logger.info(f"⚡ Flow: Intent routing to '{intent}' (sources: {sources})")
        logger.debug(f"⚡ Flow: Full routing analysis: {state.get('routing_analysis', {})}")
        return intent
    
    # Build the graph
    builder = StateGraph(ChatState)
    
    # Add core nodes
    builder.add_node("initializer", initializer_node)
    builder.add_node("multi_source_analyzer", multi_source_analyzer_node)
    builder.add_node("integrator", integrator_node)
    builder.add_node("response_renderer", response_renderer_node)
    
    # Add search-related nodes
    builder.add_node("search_prompt_optimizer", search_prompt_optimizer_node)
    
    # Add analysis nodes  
    builder.add_node("analysis_task_refiner", analysis_task_refiner_node)
    builder.add_node("analyzer", analyzer_node)
    
    # Add source coordinator node for parallel execution
    builder.add_node("source_coordinator", source_coordinator_node)
    # Add results reviewer node to filter irrelevant items before integration
    builder.add_node("results_reviewer", search_results_reviewer_node)
    # Add evidence summarizer node to create concise summaries with citations
    builder.add_node("evidence_summarizer", evidence_summarizer_node)
    
    # Define the main workflow
    builder.set_entry_point("initializer")
    builder.add_edge("initializer", "multi_source_analyzer")
    
    # Route based on intent: chat, search, or analysis
    builder.add_conditional_edges(
        "multi_source_analyzer",
        intent_router,
        {
            "chat": "integrator",
            "search": "search_prompt_optimizer",
            "analysis": "analysis_task_refiner"
        }
    )
    
    # After query optimization, coordinate parallel searches
    builder.add_edge("search_prompt_optimizer", "source_coordinator")
    
    # After parallel execution, run a relevance review step
    builder.add_edge("source_coordinator", "results_reviewer")
    # After reviewing, create evidence summaries with proper citations
    builder.add_edge("results_reviewer", "evidence_summarizer")
    builder.add_edge("evidence_summarizer", "integrator")
    
    # Analysis path goes directly to integrator
    builder.add_edge("analysis_task_refiner", "analyzer")
    builder.add_edge("analyzer", "integrator")
    
    # Final processing
    builder.add_edge("integrator", "response_renderer")
    builder.add_edge("response_renderer", END)
    
    # Compile the graph
    graph = builder.compile()
    
    logger.info("🔗 Multi-source graph compiled successfully")
    return graph


# Create a singleton instance of the graph
chat_graph = create_chat_graph()


def visualize_graph(output_file="graph.png"):
    """
    Generate a PNG visualization of the main chat LangGraph.
    
    Args:
        output_file: Path where to save the PNG file.
    
    Returns:
        bool: True if visualization was successful, False otherwise.
    """
    return visualize_langgraph(chat_graph, output_file, "Main Chat LangGraph")


def get_langsmith_client():
    """Get a LangSmith client if tracing is enabled."""
    if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
        return Client(
            api_key=LANGCHAIN_API_KEY,
            api_url=LANGCHAIN_ENDPOINT
        )
    return None


# Automatically generate visualization whenever this module is run directly
if __name__ == "__main__":
    visualize_graph() 