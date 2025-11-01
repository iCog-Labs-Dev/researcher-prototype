from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from services.user import UserService
from schemas.user import (
    UserSummary,
    RoleInOut,
    PersonalityConfig,
)

router = APIRouter(prefix="/user")


@router.get("", response_model=list[UserSummary])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
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


@router.post("/{target_user_id}/role", response_model=RoleInOut)
async def update_user_role(
    session: Annotated[AsyncSession, Depends(get_session)],
    body: RoleInOut,
    target_user_id: UUID,
):
    service = UserService()
    role = await service.update_role(session, target_user_id, body.role)

    return RoleInOut(role=role)
