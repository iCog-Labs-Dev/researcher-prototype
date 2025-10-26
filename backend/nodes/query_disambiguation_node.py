"""
Query disambiguation node for detecting vague queries and generating clarifying questions.
"""

import asyncio
from typing import Dict, Any
from nodes.base import (
    ChatState,
    logger,
    HumanMessage,
    SystemMessage,
    ChatOpenAI,
    QUERY_DISAMBIGUATION_SYSTEM_PROMPT,
    config,
    get_current_datetime_str,
    queue_status,
)
from models import QueryDisambiguationAnalysis
from services.query_disambiguation_service import QueryDisambiguationService
from utils import get_last_user_message


async def query_disambiguation_node(state: ChatState) -> ChatState:
    """
    Analyze user query for vagueness and generate clarifying questions if needed.
    
    This node runs before the multi-source analyzer to ensure queries are specific
    enough to yield high-quality search results.
    """
    logger.info("🔍 Query Disambiguation: Analyzing query for vagueness")
    queue_status(state.get("thread_id"), "Analyzing query clarity...")
    await asyncio.sleep(0.1)  # Small delay to ensure status is visible
    
    # Get the last user message
    last_message = get_last_user_message(state.get("messages", []))
    
    if not last_message:
        logger.warning("🔍 Query Disambiguation: No user message found, skipping disambiguation")
        state["disambiguation_analysis"] = None
        state["query_refinement_needed"] = False
        state["disambiguation_complete"] = True
        return state
    
    # Log the user message for traceability
    display_msg = last_message[:75] + "..." if len(last_message) > 75 else last_message
    logger.info(f'🔍 Query Disambiguation: Analyzing query: "{display_msg}"')
    
    try:
        # Initialize the disambiguation service
        disambiguation_service = QueryDisambiguationService()
        
        # Prepare context for analysis
        context = {
            "messages": state.get("messages", []),
            "user_id": state.get("user_id"),
            "memory_context": state.get("memory_context"),
            "thread_id": state.get("thread_id")
        }
        
        # Analyze the query for vagueness
        analysis = await disambiguation_service.analyze_query(last_message, context)
        
        # Store the analysis in state
        state["disambiguation_analysis"] = analysis
        
        # Check if disambiguation is needed
        if analysis.is_vague and analysis.confidence_score >= 0.5:
            logger.info(f"🔍 Query Disambiguation: Query is vague (confidence: {analysis.confidence_score:.2f})")
            logger.info(f"🔍 Query Disambiguation: Vague indicators: {analysis.vague_indicators}")
            
            # Store clarifying questions for potential use
            state["clarifying_questions"] = analysis.clarifying_questions
            state["query_refinement_needed"] = True
            state["disambiguation_complete"] = False
            
            # For now, we'll proceed with the original query but log the analysis
            # TODO: In future iterations, we could pause here and ask for clarification
            logger.info("🔍 Query Disambiguation: Proceeding with original query (clarification not yet implemented)")
            
        else:
            logger.info(f"🔍 Query Disambiguation: Query is clear (confidence: {analysis.confidence_score:.2f})")
            state["clarifying_questions"] = []
            state["query_refinement_needed"] = False
            state["disambiguation_complete"] = True
        
        # Store suggested refinements for potential use
        state["suggested_refinements"] = analysis.suggested_refinements
        
        logger.info(f"🔍 Query Disambiguation: Analysis complete - vague: {analysis.is_vague}, confidence: {analysis.confidence_score:.2f}")
        
    except Exception as e:
        logger.error(f"🔍 Query Disambiguation: Error in disambiguation analysis: {str(e)}")
        
        # Store error state but continue processing
        state["disambiguation_analysis"] = QueryDisambiguationAnalysis(
            is_vague=False,
            confidence_score=0.0,
            vague_indicators=[],
            clarifying_questions=[],
            suggested_refinements=[],
            context_analysis=f"Error in analysis: {str(e)}"
        )
        state["clarifying_questions"] = []
        state["query_refinement_needed"] = False
        state["disambiguation_complete"] = True
        state["suggested_refinements"] = []
    
    return state


async def process_clarification_response(state: ChatState, clarification: str) -> ChatState:
    """
    Process a user's clarification response and refine the original query.
    
    This function can be called when a user provides clarification to a vague query.
    """
    logger.info("🔍 Query Disambiguation: Processing clarification response")
    
    try:
        # Get the original query
        original_query = get_last_user_message(state.get("messages", []))
        
        if not original_query:
            logger.warning("🔍 Query Disambiguation: No original query found for clarification")
            return state
        
        # Initialize the disambiguation service
        disambiguation_service = QueryDisambiguationService()
        
        # Prepare context
        context = {
            "messages": state.get("messages", []),
            "user_id": state.get("user_id"),
            "memory_context": state.get("memory_context"),
            "thread_id": state.get("thread_id")
        }
        
        # Refine the query with the clarification
        refinement = await disambiguation_service.refine_query_with_clarification(
            original_query, clarification, context
        )
        
        # Store the refined query in workflow context
        if "workflow_context" not in state:
            state["workflow_context"] = {}
        
        state["workflow_context"]["refined_search_query"] = refinement.refined_query
        state["workflow_context"]["query_refinement"] = refinement
        
        # Mark disambiguation as complete
        state["disambiguation_complete"] = True
        state["query_refinement_needed"] = False
        
        logger.info(f"🔍 Query Disambiguation: Query refined from '{original_query}' to '{refinement.refined_query}'")
        
    except Exception as e:
        logger.error(f"🔍 Query Disambiguation: Error processing clarification: {str(e)}")
        # Continue with original query if refinement fails
        state["disambiguation_complete"] = True
        state["query_refinement_needed"] = False
    
    return state
