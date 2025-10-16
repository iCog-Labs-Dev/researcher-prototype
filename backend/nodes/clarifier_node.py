"""
Node for clarifying vague or ambiguous user queries.
"""
import asyncio
from nodes.base import (
    ChatState,
    logger,
    ChatOpenAI,
    config,
    HumanMessage,
    AIMessage,
    SystemMessage,
    CLARIFICATION_PROMPT
)
from utils import get_last_user_message

async def clarifier_node(state: ChatState) -> ChatState:
    """Clarifies vague or ambiguous user queries"""
    logger.info("❓ Clarification Node: Checking if query needs clarification")
    await asyncio.sleep(0.1) #Small delay to ensure status is visible

    # Get the last user message
    last_message = get_last_user_message(state.get("messages", []))

    clarifying_llm = ChatOpenAI(
        model=config.ROUTER_MODEL,
        temperature=0.0, # Keep deterministic
        max_tokens=200,
        api_key=config.OPENAI_API_KEY,
    )

    try:
        history_messages = state.get("messages", [])

        # Create the system prompt for clarification - include memory context if available
        memory_context = state.get("memory_context")
        memory_context_section = ""
        if memory_context:
            memory_context_section = f"CONVERSATION MEMORY:\n{memory_context}\n\nUse this context to maintain conversation continuity and reference previous topics when relevant."
            logger.debug("❓ Clarification Node: Including memory context in analysis")
        else:
            logger.debug("❓ Clarification Node: No memory context available")

        # Create system message with clarification instructions
        system_message = SystemMessage(
            content=CLARIFICATION_PROMPT.format(
                memory_context_section=memory_context_section,
                last_message=last_message)
            )

        # Build the complete message list for the clarifier
        clarifier_messages = [system_message] + history_messages

        response = clarifying_llm.invoke(clarifier_messages)
        print(response.content)
        logger.info("❓ Clarification Node: Generated clarification response")
        state["workflow_context"]["clarifying_question"] = response.content
        ai_response = AIMessage(content=response.content)
        state["messages"].append(ai_response)
    except Exception as e:
        logger.error(f"Error in clarification_node: {str(e)}")

    return state