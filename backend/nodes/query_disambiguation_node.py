"""
Query disambiguation node for detecting vague queries and generating clarifying questions.
"""

from typing import Dict
from nodes.base import (
    ChatState,
    logger,
    ChatOpenAI,
    QUERY_DISAMBIGUATION_SYSTEM_PROMPT,
    config,
    get_current_datetime_str,
    queue_status,
)
from models import QueryDisambiguationAnalysis
from services.query_disambiguation_service import QueryDisambiguationService
from utils import get_last_user_message


def _build_context(state: ChatState) -> Dict:
    """Build a reusable LLM context from chat state."""
    return {
        "messages": state.get("messages", []),
        "user_id": state.get("user_id"),
        "memory_context": state.get("memory_context"),
        "thread_id": state.get("thread_id")
    }


async def query_disambiguation_node(state: ChatState) -> ChatState:
    """Analyze user query for vagueness and generate clarifying questions if needed."""
    logger.info("Query Disambiguation: analyzing query for vagueness")
    queue_status(state.get("thread_id"), "Analyzing query clarity...")

    last_message = get_last_user_message(state.get("messages", []))
    if not last_message:
        logger.warning("No user message found, skipping disambiguation")
        state.update({
            "disambiguation_analysis": None,
            "query_refinement_needed": False,
            "disambiguation_complete": True
        })
        return state

    display_msg = f"{last_message[:75]}..." if len(last_message) > 75 else last_message
    logger.info(f'Analyzing query: "{display_msg}"')

    try:
        disambiguation_service = QueryDisambiguationService()
        analysis = await disambiguation_service.analyze_query(last_message, _build_context(state))

        state["disambiguation_analysis"] = analysis
        state["suggested_refinements"] = analysis.suggested_refinements
        state["clarifying_questions"] = analysis.clarifying_questions if analysis.is_vague else []
        state["query_refinement_needed"] = analysis.is_vague and analysis.confidence_score >= 0.5
        state["disambiguation_complete"] = not state["query_refinement_needed"]

        status = "vague" if analysis.is_vague else "clear"
        logger.info(f"Query is {status} (confidence: {analysis.confidence_score:.2f})")
        logger.info(f"Analysis complete - vague indicators: {analysis.vague_indicators}")

    except Exception as e:
        logger.error(f"Error in disambiguation analysis: {str(e)}")
        state.update({
            "disambiguation_analysis": QueryDisambiguationAnalysis(
                is_vague=False,
                confidence_score=0.0,
                vague_indicators=[],
                clarifying_questions=[],
                suggested_refinements=[],
                context_analysis=f"Error in analysis: {str(e)}"
            ),
            "clarifying_questions": [],
            "query_refinement_needed": False,
            "disambiguation_complete": True,
            "suggested_refinements": []
        })

    return state

