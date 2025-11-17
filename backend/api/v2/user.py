from __future__ import annotations
import time
from typing import Annotated, Any, Dict
from fastapi import APIRouter, Request, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import inject_user_id
from db import get_session
from schemas.user import (
    UserProfile,
    PreferencesConfig,
    PersonalityConfig,
    DisplayNameInOut,
    EmailInOut,
    EngagementAnalytics,
    PersonalizationHistory,
    PreferenceOverride,
    PersonalizationContext,
    AdaptationLogEntry,
    InteractionSignals,
    PersonalizationTransparency,
    LearnedBehaviors,
    LearningStats,
)
from exceptions import CommonError
from services.user import UserService

router = APIRouter(prefix="/user", tags=["v2/user"], dependencies=[Depends(inject_user_id)])


@router.get("", response_model=UserProfile)
async def get_me(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_id = str(request.state.user_id)

    service = UserService()
    user = await service.get_user(session, user_id, True)
    profile = user.profile

    return UserProfile(
        id=user.id,
        created_at=user.created_at,
        metadata=(profile.meta_data if profile and profile.meta_data else {}),
        personality=PersonalityConfig.model_validate(profile.personality or {}),
        preferences=PreferencesConfig.model_validate(profile.preferences or {}),
    )


@router.get("/engagement-analytics", response_model=EngagementAnalytics)
async def get_engagement_analytics(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_id = str(request.state.user_id)

    service = UserService()
    user = await service.get_user(session, user_id, True)
    profile = user.profile

    return EngagementAnalytics.model_validate(profile.engagement_analytics or {})


@router.get("/personalization-history", response_model=PersonalizationHistory)
async def get_user_personalization_history(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_id = str(request.state.user_id)

    service = UserService()
    user = await service.get_user(session, user_id, True)
    profile = user.profile

    return PersonalizationHistory.model_validate(profile.personalization_history or {})


@router.get("/personalization", response_model=PersonalizationTransparency)
async def get_user_personalization_data(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_id = str(request.state.user_id)

    user_service = UserService()
    user = await user_service.get_user(session, user_id, True)
    profile = user.profile

    preferences = PreferencesConfig.model_validate(profile.preferences or {})
    engagement_analytics = EngagementAnalytics.model_validate(profile.engagement_analytics or {})
    personalization_history = PersonalizationHistory.model_validate(profile.personalization_history or {})

    return PersonalizationTransparency(
        explicit_preferences=preferences,
        learned_behaviors=LearnedBehaviors(
            source_preferences=preferences.content_preferences.source_types or {},
            engagement_patterns=engagement_analytics.reading_patterns or {},
            interaction_signals=InteractionSignals(
                most_engaged_source_types=engagement_analytics.interaction_signals.most_engaged_source_types or [],
                follow_up_question_frequency=engagement_analytics.interaction_signals.follow_up_question_frequency or 0.0,
            ),
        ),
        adaptation_history=personalization_history.adaptation_log[-10:],
        user_overrides=engagement_analytics.user_overrides or {},
        learning_stats=LearningStats(
            total_adaptations=len(personalization_history.adaptation_log),
            recent_activity=len([e for e in personalization_history.adaptation_log if time.time() - e.timestamp < 604800]),
        ),
    )


@router.get("/personalization-context", response_model=PersonalizationContext)
async def get_personalization_context(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_id = str(request.state.user_id)

    user_service = UserService()
    user = await user_service.get_user(session, user_id, True)
    profile = user.profile

    preferences = PreferencesConfig.model_validate(profile.preferences or {})
    engagement_analytics = EngagementAnalytics.model_validate(profile.engagement_analytics or {})

    return PersonalizationContext(
        content_preferences=preferences.content_preferences,
        format_preferences=preferences.format_preferences,
        interaction_preferences=preferences.interaction_preferences,
        learned_adaptations=engagement_analytics.learned_adaptations,
        engagement_patterns={
            "preferred_sources": engagement_analytics.interaction_signals.most_engaged_source_types,
            "follow_up_frequency": engagement_analytics.interaction_signals.follow_up_question_frequency,
        },
    )


@router.post("/display-name", response_model=DisplayNameInOut)
async def update_display_name(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: DisplayNameInOut,
):
    user_id = str(request.state.user_id)

    service = UserService()
    name = await service.update_display_name(session, user_id, body.display_name)

    return DisplayNameInOut(display_name=name)


@router.post("/email", response_model=EmailInOut)
async def update_email(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: EmailInOut,
):
    user_id = str(request.state.user_id)

    service = UserService()
    email = await service.update_email(session, user_id, str(body.email))

    return EmailInOut(email=email)


@router.post("/preferences", response_model=PreferencesConfig)
async def update_preferences(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: PreferencesConfig,
):
    user_id = str(request.state.user_id)

    service = UserService()
    preferences = await service.update_preferences(session, user_id, body.model_dump())

    return PreferencesConfig.model_validate(preferences)


@router.post("/personality", response_model=PersonalityConfig)
async def update_personality(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: PersonalityConfig,
) -> PersonalityConfig:
    user_id = str(request.state.user_id)

    service = UserService()
    personality = await service.update_personality(session, user_id, body.model_dump())

    return PersonalityConfig.model_validate(personality)


@router.post("/personalization/override")
async def override_learned_behavior(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    override_request: PreferenceOverride,
):
    user_id = str(request.state.user_id)

    user_service = UserService()
    user = await user_service.get_user(session, user_id, True)
    profile = user.profile

    await user_service.apply_override(
        session,
        profile,
        override_request.preference_type,
        override_request.override_value,
        bool(override_request.disable_learning),
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/engagement/track")
async def track_user_engagement(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    interaction_data: Dict[str, Any],
):
    user_id = str(request.state.user_id)

    interaction_type = interaction_data.get("interaction_type")
    metadata = interaction_data.get("metadata", {})

    if not interaction_type:
        raise CommonError("Missing interaction_type")

    user_service = UserService()
    user = await user_service.get_user(session, user_id, True)
    profile = user.profile

    await user_service.track_user_engagement(session, profile, interaction_type, metadata)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/feedback")
async def submit_user_feedback(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    feedback_data: Dict[str, Any],
):
    user_id = str(request.state.user_id)

    feedback_type = feedback_data.get("type")
    message_id = feedback_data.get("messageId")
    feedback = feedback_data.get("feedback")

    if not all([feedback_type, message_id, feedback]):
        raise CommonError("Missing required feedback data")

    user_service = UserService()
    user = await user_service.get_user(session, user_id, True)
    profile = user.profile

    metadata = {
        "type": "feedback",
        "feedback_type": feedback_type,
        "message_id": message_id,
        "feedback": feedback,
        "timestamp": feedback_data.get("timestamp"),
    }
    await user_service.track_user_engagement(session, profile, "engagement_event", metadata)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/link-click")
async def track_link_click(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    click_data: Dict[str, Any],
):
    user_id = str(request.state.user_id)

    url = click_data.get("url")
    if not url:
        raise CommonError("Missing url")

    user_service = UserService()
    user = await user_service.get_user(session, user_id, True)
    profile = user.profile

    metadata = {
        "type": "link_click",
        "url": url,
        "context": click_data.get("context", {}),
        "timestamp": click_data.get("timestamp"),
    }
    await user_service.track_user_engagement(session, profile, "engagement_event", metadata)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
