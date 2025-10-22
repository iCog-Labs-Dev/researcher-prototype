from __future__ import annotations
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from dependencies import get_current_user_id, get_current_admin_id
from schemas.user import (
    UserProfile,
    UserSummary,
    PreferencesConfig,
    PersonalityConfig,
    DisplayNameInOut,
    EmailInOut,
    RoleInOut,
)
from services.user import UserService

router = APIRouter(prefix="/v2/user", tags=["user"])


@router.get("", response_model=UserProfile)
async def get_me(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)]
):
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
    body: DisplayNameInOut,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)]
):
    service = UserService()
    name = await service.update_display_name(session, user_id, body.display_name)

    return DisplayNameInOut(display_name=name)


@router.post("/email", response_model=EmailInOut)  # фикс: правильная схема ответа
async def update_email(
    body: EmailInOut,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)]
):
    service = UserService()
    email = await service.update_email(session, user_id, str(body.email))

    return EmailInOut(email=email)


@router.post("/preferences", response_model=PreferencesConfig)
async def update_preferences(
    body: PreferencesConfig,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)]
):
    service = UserService()
    preferences = await service.update_preferences(session, user_id, body.model_dump())

    return PreferencesConfig.model_validate(preferences)


@router.post("/personality", response_model=PersonalityConfig)
async def update_personality(
    body: PersonalityConfig,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)]
) -> PersonalityConfig:
    service = UserService()
    personality = await service.update_personality(session, user_id, body.model_dump())

    return PersonalityConfig.model_validate(personality)


@router.get("/users", response_model=list[UserSummary])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    admin_id: Annotated[UUID, Depends(get_current_admin_id)],
    limit: int = 50,
    offset: int = 0,
):
    service = UserService()
    users = await service.list_users(session, limit=limit, offset=offset)
    items: list[UserSummary] = []

    for user in users:
        display_name = ""
        meta = user.meta_data or {}
        if isinstance(meta, dict):
            value = meta.get("display_name")
            if isinstance(value, str):
                display_name = value

        items.append(
            UserSummary(
                id=user.id,
                created_at=user.created_at,
                display_name=display_name,
                role=user.role,
                personality=PersonalityConfig.model_validate(user.additional_traits or {}),
            )
        )

    return items


@router.post("/users/{target_user_id}/role", response_model=RoleInOut)
async def update_user_role(
    target_user_id: UUID,
    body: RoleInOut,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin_id: Annotated[UUID, Depends(get_current_admin_id)],
):
    service = UserService()
    role = await service.update_role(session, target_user_id, body.role)

    return RoleInOut(role=role)
