from uuid import UUID
from typing import Annotated
import asyncio
from fastapi import APIRouter, Request, Depends, Query
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from services.logging_config import get_logger
from dependencies import inject_user_id
from builders.chat import chat_graph
from services.status_manager import queue_status
from exceptions import CommonError
from schemas.chat import (
    ChatIn,
    ChatOut,
    ChatView,
    ChatHistoryItem,
)
from services.chat import ChatService
from services.user import UserService
from services.topic import TopicService

router = APIRouter(prefix="/chat", tags=["v2/chat"], dependencies=[Depends(inject_user_id)])

logger = get_logger(__name__)


@router.post("", response_model=ChatOut)
async def chat(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: ChatIn,
) -> ChatOut:
    user_id = str(request.state.user_id)

    user_message = body.messages[-1].content

    chat_service = ChatService()
    chat_id = await chat_service.get_or_create_chat_id(
        session, user_id, user_message, body.session_id if body.session_id else None
    )

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
        "thread_id": str(chat_id),
    }

    if body.personality:
        user_service = UserService()
        await user_service.update_personality(session, user_id, body.personality.model_dump())

    result = await chat_graph.ainvoke(state)

    if "error" in result:
        logger.error(f"Error in chat endpoint: {result['error']}")

        raise CommonError("Error in chat endpoint")

    assistant_message = result["messages"][-1].content

    await chat_service.save_history(chat_id, user_message, assistant_message)

    # Store conversation in ZEP for knowledge graph
    async def _store_conversation_with_error_handling():
        """Wrapper to ensure ZEP storage errors are logged."""
        try:
            from dependencies import zep_manager
            
            logger.debug(f"Starting ZEP storage for user {user_id}, thread {str(chat_id)}")
            success = await zep_manager.store_conversation_turn(
                user_id=user_id,
                user_message=user_message,
                ai_response=assistant_message,
                thread_id=str(chat_id),
            )
            if not success:
                logger.warning(f"ZEP storage returned False for user {user_id}, thread {str(chat_id)}")
        except Exception as e:
            logger.error(
                f"Failed to store conversation in Zep for user {user_id}: {str(e)}", 
                exc_info=True
            )
    
    # Create background task for ZEP storage
    try:
        asyncio.create_task(_store_conversation_with_error_handling())
    except Exception as e:
        logger.error(f"Failed to create ZEP storage task: {str(e)}", exc_info=True)

    topic_service = TopicService()
    asyncio.create_task(
        topic_service.async_extract_and_store_topics(
            user_id=user_id,
            chat_id=chat_id,
            state=result,
            conversation_context=body.messages[-1].content[:200]
            + ("..." if len(body.messages[-1].content) > 200 else ""),
        )
    )

    response_obj = ChatOut(
        response=assistant_message,
        model=body.model,
        usage={},
        module_used=result.get("current_module", "unknown"),
        routing_analysis=result.get("routing_analysis"),
        user_id=user_id,
        session_id=chat_id,
        suggested_topics=[],
        follow_up_questions=result.get("workflow_context", {}).get("follow_up_questions", []),
    )

    queue_status(result.get("thread_id"), "Complete")

    return response_obj


@router.get("", response_model=list[ChatView])
async def get_chats(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ChatView]:
    user_id = str(request.state.user_id)

    service = ChatService()
    chats = await service.get_chats(session, user_id)
    items: list[ChatView] = []

    for item in chats:
        items.append(
            ChatView(
                id=item.id,
                name=item.name,
                created_at=item.created_at,
            )
        )

    return items


@router.get("/{chat_id}", response_model=list[ChatHistoryItem])
async def get_chats(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    chat_id: UUID,
    limit: int = Query(10),
) -> list[ChatHistoryItem]:
    user_id = str(request.state.user_id)

    service = ChatService()
    history = await service.get_history(session, user_id, chat_id, limit)
    items: list[ChatHistoryItem] = []

    for item in history:
        items.append(
            ChatHistoryItem(
                question=item.get("question"),
                answer=item.get("answer"),
                created_at=item.get("created_at"),
            )
        )

    return items
