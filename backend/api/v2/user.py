from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import inject_user_id
from db import get_session
from schemas.user import (
    UserProfile,
    PreferencesConfig,
    PersonalityConfig,
    DisplayNameInOut,
    EmailInOut,
)
from services.user import UserService

router = APIRouter(prefix="/user", tags=["v2/user"], dependencies=[Depends(inject_user_id)])


@router.get("", response_model=UserProfile)
async def get_me(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user_id = str(request.state.user_id)

    service = UserService()
    user = await service.get_user(session, user_id)

    return UserProfile(
        id=user.id,
        created_at=user.created_at,
        metadata=user.meta_data or {},
        personality=PersonalityConfig.model_validate(user.additional_traits or {}),
        preferences=(
            PreferencesConfig.model_validate(user.preferences)
            if user.preferences is not None
            else None
        ),
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


@router.post("/email", response_model=EmailInOut)  # фикс: правильная схема ответа
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
