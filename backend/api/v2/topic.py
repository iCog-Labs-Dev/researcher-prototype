from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Request, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from dependencies import inject_user_id
from schemas.topic import (
    CustomTopicIn,
    CustomTopicOut,
    TopicEnableOut,
    TopicSuggestionItem,
    TopicSuggestionsByChatOut,
    TopicSuggestionsOut,
    TopicStatusOut,
    ResearchTopicsByUserOut,
    TopicStatsOut,
    TopTopicsOut,
)
from services.logging_config import get_logger
from services.topic import TopicService

router = APIRouter(prefix="/topic", tags=["v2/topic"], dependencies=[Depends(inject_user_id)])

logger = get_logger(__name__)


@router.get("/suggestions/{session_id}", response_model=TopicSuggestionsByChatOut, response_model_exclude_none=True)
async def get_topic_suggestions(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    session_id: UUID,
) -> TopicSuggestionsByChatOut:
    user_id = str(request.state.user_id)

    service = TopicService()
    topics = await service.get_topics_by_chat_id(session, user_id, session_id)

    topic_suggestions: list[TopicSuggestionItem] = []
    for topic in topics:
        topic_suggestions.append(TopicSuggestionItem(
            topic_id=topic.id,
            name=topic.name,
            description=topic.description,
            confidence_score=topic.confidence_score,
            conversation_context=topic.conversation_context,
            is_active_research=topic.is_active_research,
            suggested_at=topic.created_at,
            is_child=topic.is_child,
            parent_id=topic.parent_id,
        ))

    return TopicSuggestionsByChatOut(
        total_count=len(topic_suggestions),
        topic_suggestions=topic_suggestions,
    )


@router.get("/suggestions", response_model=TopicSuggestionsOut, response_model_exclude_none=True)
async def get_all_topic_suggestions(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TopicSuggestionsOut:
    user_id = str(request.state.user_id)

    service = TopicService()
    topics = await service.get_topics_by_user_id(session, user_id)
    chats_count = await service.get_count_chats_by_user_id(session, user_id)

    topic_suggestions: list[TopicSuggestionItem] = []
    for topic in topics:
        topic_suggestions.append(TopicSuggestionItem(
            topic_id=topic.id,
            session_id=str(topic.chat_id) if topic.chat_id else "custom",
            name=topic.name,
            description=topic.description,
            confidence_score=topic.confidence_score,
            conversation_context=topic.conversation_context,
            is_active_research=topic.is_active_research,
            suggested_at=topic.created_at,
            is_child=topic.is_child,
            parent_id=topic.parent_id,
        ))

    return TopicSuggestionsOut(
        total_count=len(topic_suggestions),
        sessions_count=chats_count,
        topic_suggestions=topic_suggestions,
    )


@router.get("/status/{session_id}", response_model=TopicStatusOut)
async def get_status_by_chat_id(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    session_id: UUID,
) -> TopicStatusOut:
    user_id = str(request.state.user_id)

    service = TopicService()
    topics = await service.get_topics_by_chat_id(session, user_id, session_id)

    return TopicStatusOut(
        has_topics=len(topics) > 0,
        topic_count=len(topics),
    )


@router.get("/stats")
async def get_topic_statistics(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_id = request.state.user_id

    service = TopicService()
    total, sessions_count, avg_score, oldest_days = await service.get_user_topic_stats(session, user_id)

    return TopicStatsOut(
        total_topics=total,
        total_sessions=sessions_count,
        average_confidence_score=avg_score,
        oldest_topic_age_days=oldest_days,
    )


@router.delete("/session/{session_id}")
async def delete_topics_by_chat(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    session_id: UUID,
):
    user_id = str(request.state.user_id)

    service = TopicService()
    await service.delete_topics_by_chat(session, user_id, session_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/cleanup")
async def cleanup_topics(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_id = str(request.state.user_id)

    service = TopicService()
    await service.cleanup_topics(session, user_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/session/{session_id}/top", response_model=TopTopicsOut, response_model_exclude_none=True)
async def get_top_session_topics(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    session_id: UUID,
    limit: int = Query(default=3, ge=1, le=10),
):
    user_id = request.state.user_id

    service = TopicService()
    available_count, topics = await service.get_top_topics_by_chat(session, user_id, session_id, limit)

    items: list[TopicSuggestionItem] = []
    for t in topics:
        items.append(TopicSuggestionItem(
            topic_id=t.id,
            name=t.name,
            description=t.description,
            confidence_score=t.confidence_score,
            conversation_context=t.conversation_context,
            is_active_research=t.is_active_research,
            suggested_at=t.created_at,
            is_child=t.is_child,
            parent_id=t.parent_id,
        ))

    return TopTopicsOut(
        total_count=len(items),
        available_count=available_count,
        topics=items,
    )


@router.delete("/non-activated")
async def delete_non_activated_topics(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_id = str(request.state.user_id)

    service = TopicService()
    await service.delete_non_activated_topics(session, user_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{topic_id}")
async def delete_topic_by_id(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    topic_id: UUID,
):
    user_id = str(request.state.user_id)

    service = TopicService()
    await service.delete_topic_by_id(session, user_id, topic_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/custom", response_model=CustomTopicOut)
async def create_custom_topic(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: CustomTopicIn,
) -> CustomTopicOut:
    user_id = str(request.state.user_id)

    service = TopicService()
    topic = await service.create_topic(
        session,
        user_id,
        body.name,
        body.description,
        confidence_score=body.confidence_score,
        is_active_research=body.is_active_research,
    )

    return CustomTopicOut(
        topic_id=topic.id,
        user_id=topic.user_id,
        name=topic.name,
        description=topic.description,
        confidence_score=topic.confidence_score,
        is_active_research=topic.is_active_research,
        suggested_at=topic.created_at,
    )


@router.get("/user/research", response_model=ResearchTopicsByUserOut, response_model_exclude_none=True)
async def get_active_research_topics(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResearchTopicsByUserOut:
    user_id = str(request.state.user_id)

    service = TopicService()
    topics = await service.get_active_research_topics_by_user_id(session, user_id)

    result_topics: list[TopicSuggestionItem] = []
    for topic in topics:
        result_topics.append(TopicSuggestionItem(
            topic_id=topic.id,
            session_id=str(topic.chat_id) if topic.chat_id else "custom",
            name=topic.name,
            description=topic.description,
            confidence_score=topic.confidence_score,
            suggested_at=topic.created_at,
            last_researched=topic.last_researched,
            research_count=topic.research_count,
            is_child=topic.is_child,
            parent_id=topic.parent_id,
        ))

    return ResearchTopicsByUserOut(
        total_count=len(result_topics),
        active_research_topics=result_topics,
    )


@router.patch("/topic/{topic_id}/research", response_model=TopicEnableOut)
async def enable_disable_research_by_topic_id(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    topic_id: UUID,
    enable: bool = Query(True, description="True to enable, False to disable"),
) -> TopicEnableOut:
    user_id = request.state.user_id  # Keep as UUID, don't convert to string

    service = TopicService()
    result = await service.update_active_research(session, user_id, topic_id, enable)

    return TopicEnableOut(enabled=result)
