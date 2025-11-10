from __future__ import annotations
from uuid import UUID
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from exceptions import NotFound, CommonError
from models.user import User
from models.user_profile import UserProfile


class UserService:
    async def get_user(
        self,
        session: AsyncSession,
        user_id: UUID,
        with_profile: bool = False,
    ) -> User:
        if with_profile:
            query = (
                select(User)
                .options(selectinload(User.profile))
                .where(User.id == user_id)
            )
            res = await session.execute(query)
            user = res.scalar_one_or_none()
        else:
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

        user = await self.get_user(session, user_id, True)
        profile = self._ensure_profile(session, user)

        meta = profile.meta_data or {}
        if not isinstance(meta, dict):
            meta = {}

        meta["display_name"] = value
        profile.meta_data = meta

        await session.commit()

        return user.profile.meta_data["display_name"]

    async def update_email(
        self,
        session: AsyncSession,
        user_id: UUID,
        email: str,
    ) -> str:
        value = email.strip().lower()
        if not value:
            raise CommonError("Email cannot be empty")

        user = await self.get_user(session, user_id, True)
        profile = self._ensure_profile(session, user)

        meta = profile.meta_data or {}
        if not isinstance(meta, dict):
            meta = {}

        meta["email"] = value
        profile.meta_data = meta

        await session.commit()

        return user.profile.meta_data["email"]

    async def update_preferences(
        self,
        session: AsyncSession,
        user_id: UUID,
        preferences: dict[str, Any],
    ) -> dict[str, Any]:
        user = await self.get_user(session, user_id, True)
        profile = self._ensure_profile(session, user)

        profile.preferences = preferences
        await session.commit()

        return user.profile.preferences or {}

    async def update_personality(
        self,
        session: AsyncSession,
        user_id: UUID,
        personality: dict[str, Any],
    ) -> dict[str, Any]:
        user = await self.get_user(session, user_id, True)
        profile = self._ensure_profile(session, user)

        profile.personality = personality
        await session.commit()

        return user.profile.personality or {}

    async def list_users(
        self,
        session: AsyncSession,
        limit: int,
        offset: int,
    ) -> list[User]:
        res = await session.execute(
            select(User)
            .options(selectinload(User.profile))
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

    def _ensure_profile(
        self,
        session: AsyncSession,
        user: User,
    ) -> UserProfile:
        if user.profile is not None:
            return user.profile

        profile = UserProfile(user_id=user.id, meta_data={})
        session.add(profile)

        return profile
