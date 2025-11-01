from fastapi import APIRouter, Request, Depends, HTTPException
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import asyncio

from schemas.schemas import ChatRequest, ChatResponse
from graph_builder import chat_graph
from dependencies import profile_manager, zep_manager, inject_user_id
from services.chat_service import extract_and_store_topics_async
from services.logging_config import get_logger
from services.status_manager import queue_status

router = APIRouter(prefix="/chat", tags=["v2/chat"], dependencies=[Depends(inject_user_id)])

logger = get_logger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(
    request: Request,
    body: ChatRequest,
):
    user_id = str(request.state.user_id)

    try:
        logger.debug(f"Chat request: {body}")

        messages_for_state = []
        for m in body.messages:
            if m.role == "user":
                messages_for_state.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                messages_for_state.append(AIMessage(content=m.content))
            elif m.role == "system":
                messages_for_state.append(SystemMessage(content=m.content))

        state = {
            "messages": messages_for_state,
            "model": body.model,
            "temperature": body.temperature,
            "max_tokens": body.max_tokens,
            "personality": body.personality.model_dump() if body.personality else None,
            "current_module": None,
            "module_results": {},
            "workflow_context": {},
            "user_id": user_id,
            "thread_id": body.session_id,
        }

        if body.personality:
            profile_manager.update_personality(user_id, body.personality.model_dump())

        try:
            # Motivation system
            pass  # activity triggered from main app if available
        except Exception as e:
            logger.warning(f"Failed to trigger user activity for motivation system: {str(e)}")

        result = await chat_graph.ainvoke(state)

        if "error" in result:
            raise Exception(result["error"])

        assistant_message = result["messages"][-1]

        if len(body.messages) > 0:
            user_message = body.messages[-1].content
            try:
                asyncio.create_task(
                    zep_manager.store_conversation_turn(
                        user_id=user_id,
                        user_message=user_message,
                        ai_response=assistant_message.content,
                        thread_id=result.get("thread_id"),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to store conversation in Zep: {str(e)}")

        if result.get("thread_id") and len(body.messages) > 0:
            try:
                asyncio.create_task(
                    extract_and_store_topics_async(
                        state=result,
                        user_id=user_id,
                        thread_id=result["thread_id"],
                        conversation_context=body.messages[-1].content[:200]
                        + ("..." if len(body.messages[-1].content) > 200 else ""),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to start background topic extraction: {str(e)}")

        response_obj = ChatResponse(
            response=assistant_message.content,
            model=body.model,
            usage={},
            module_used=result.get("current_module", "unknown"),
            routing_analysis=result.get("routing_analysis"),
            user_id=user_id,
            session_id=result.get("thread_id"),
            suggested_topics=[],
            follow_up_questions=result.get("workflow_context", {}).get("follow_up_questions", []),
        )
        queue_status(result.get("thread_id"), "Complete")
        return response_obj
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
