from __future__ import annotations
from uuid import UUID
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from exceptions import NotFound, CommonError
from models.user import User


class UserService:
    async def get_user(
        self,
        session: AsyncSession,
        user_id: UUID
) -> User:
        user = await session.get(User, user_id)
        if not user:
            raise NotFound("User not found")
        return user

    async def update_display_name(
        self,
        session: AsyncSession,
        user_id: UUID,
        display_name: str,
    ) -> str:
        value = display_name.strip()
        if not value:
            raise CommonError("Display name cannot be empty")

        user = await self.get_user(session, user_id)

        if not isinstance(user.meta_data, dict):
            user.meta_data = {}

        user.meta_data["display_name"] = value
        await session.commit()

        return user.meta_data["display_name"]

    async def update_email(
        self,
        session: AsyncSession,
        user_id: UUID,
        email: str,
    ) -> str:
        value = email.strip().lower()
        if not value:
            raise CommonError("Email cannot be empty")

        user = await self.get_user(session, user_id)

        if not isinstance(user.meta_data, dict):
            user.meta_data = {}

        user.meta_data["email"] = value
        await session.commit()

        return user.meta_data["email"]

    async def update_preferences(
        self,
        session: AsyncSession,
        user_id: UUID,
        preferences: dict[str, Any],
    ) -> dict[str, Any]:
        user = await self.get_user(session, user_id)

        user.preferences = preferences
        await session.commit()

        return user.preferences

    async def update_personality(
        self,
        session: AsyncSession,
        user_id: UUID,
        personality: dict[str, Any],
    ) -> dict[str, Any]:
        user = await self.get_user(session, user_id)

        user.additional_traits = personality
        await session.commit()

        return user.additional_traits

    async def list_users(
        self,
        session: AsyncSession,
        limit: int,
        offset: int,
    ):
        res = await session.execute(
            select(User)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(res.scalars().all())

    async def update_role(
        self,
        session: AsyncSession,
        target_user_id: UUID,
        role: str,
    ) -> str:
        user = await self.get_user(session, target_user_id)

        user.role = role
        await session.commit()

        return user.role
