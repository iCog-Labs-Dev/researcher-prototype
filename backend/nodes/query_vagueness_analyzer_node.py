"""
Node for analyzing user queries for vagueness or ambiguity.
"""
import asyncio
from nodes.base import (
    ChatState,
    logger,
    ChatOpenAI,
    config,
    QueryVaguenessAnalysis,
    QUERY_VAGUENESS_ANALYSIS_PROMPT,
    HumanMessage,
    SystemMessage
)
from utils import get_last_user_message

async def query_vagueness_analyzer_node(state: ChatState) -> ChatState:
    """Checks for vagueness or ambiguity in the user's query"""
    logger.info("❓ Query Analysis: Analyzing query for vagueness or ambiguity")
    await asyncio.sleep(0.1) # Small delay to ensure status is visible
    
    # Get the last user message
    last_message = get_last_user_message(state.get("messages", []))

    if not last_message:
        state["intent"] = "chat"
        state["selected_sources"] = []
        ## ############state["routing_analysis"] =
    analyzer_llm = ChatOpenAI(
        model=config.ROUTER_MODEL,
        temperature=0.0, # Keep deterministic
        max_tokens=200,
        api_key=config.OPENAI_API_KEY,
    )

    # Create a structured output model
    structured_analyzer = analyzer_llm.with_structured_output(QueryVaguenessAnalysis)

    try:
        history_messages = state.get("messages", [])

        # Create the system prompt for analysis - include memory context if available
        memory_context = state.get("memory_context")
        memory_context_section = ""
        if memory_context:
            memory_context_section = f"CONVERSATION MEMORY:\n{memory_context}\n\nUse this context to maintain conversation continuity and reference previous topics when relevant."
            logger.debug("❓ Multi-Source Analyzer: Including memory context in analysis")
        else:
            logger.debug("❓ Multi-Source Analyzer: No memory context available")

        # Create system message with analysis instructions
        system_message = SystemMessage(
            content=QUERY_VAGUENESS_ANALYSIS_PROMPT.format(
                memory_context_section=memory_context_section
            )
        )

        # Build the complete message list for the analyzer
        analyzer_messages = [system_message] + history_messages

        # If no conversation history exists, add the current user message
        if not history_messages and last_message:
            analyzer_messages.append(HumanMessage(content=last_message))

        logger.debug(f"Query vagueness analyzer using {len(analyzer_messages)-1} context messages")

        # Invoke the structured analyzer
        analysis_result = structured_analyzer.invoke(analyzer_messages)

        # Extract results
        query_is_clear = not analysis_result.is_vague

        if query_is_clear:
            state["query_clarity"] = True
            logger.info("❓ Query Analysis: Query is clear and specific, skipping clarification")
        else:
            state["query_clarity"] = False
            logger.info("❓ Query Analysis: Query is vague or ambiguous, heading to clarifying node")
    except Exception as e:
        # Error handling with fallback to query_clarity = True
        logger.error(f"Error in query_vagueness_analyzer_node: {str(e)}")
        state["query_clarity"] = True
        logger.info("❓ Query Analysis: Exception occurred, defaulting to chat")
    
    return state