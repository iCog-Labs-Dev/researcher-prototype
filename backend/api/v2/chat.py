from typing import Annotated
from fastapi import APIRouter, Request, Depends
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from db import get_session
from services.logging_config import get_logger
from dependencies import inject_user_id
from graph_builder import chat_graph
from services.status_manager import queue_status
from exceptions import CommonError
from schemas.chat import (
    ChatIn,
    ChatOut,
    ChatView,
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
        session, user_id, user_message, body.chat_id if body.chat_id else None
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
        raise CommonError(f"Error in chat endpoint: {result["error"]}")

    assistant_message = result["messages"][-1].content

    await chat_service.save_history(chat_id, user_message, assistant_message)

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
        chat_id=chat_id,
        suggested_topics=[],
        follow_up_questions=result.get("workflow_context", {}).get("follow_up_questions", []),
    )

    queue_status(result.get("thread_id"), "Complete")

    return response_obj


@router.get("", response_model=ChatView)
async def get_chats(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ChatView:
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
