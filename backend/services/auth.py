from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from exceptions import AlreadyExist, PasswordError
from utils.password import hash_password, verify_password
from utils.helpers import normalize_provider_user_id
from models.user import User
from models.identity import Identity

PROVIDER_LOCAL  = "local"


class AuthService:
    def __init__(self):
        pass

    async def get_identity(
        self, session: AsyncSession, provider: str, provider_user_id: str,
    ) -> Optional[Identity]:
        pid = normalize_provider_user_id(provider, provider_user_id)
        query = select(Identity).where(
            and_(Identity.provider == provider, Identity.provider_user_id == pid)
        )

        res = await session.execute(query)

        return res.scalar_one_or_none()

    async def link_identity(
        self, session: AsyncSession, user_id: uuid.UUID, provider: str, provider_user_id: str, password_plain: Optional[str] = None,
    ) -> Identity:
        pid = normalize_provider_user_id(provider, provider_user_id)

        password_hash: Optional[str] = None
        if provider == PROVIDER_LOCAL:
            if not password_plain:
                raise PasswordError("Password is required for local provider")
            password_hash = hash_password(password_plain)
        else:
            if password_plain is not None:
                raise PasswordError("Password must not be provided for non-local providers")

        identity = Identity(
            user_id=user_id,
            provider=provider,
            provider_user_id=pid,
            password_hash=password_hash,
        )
        session.add(identity)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise AlreadyExist("This identity is already linked")
        except Exception:
            await session.rollback()
            raise

        return identity

    async def register_local_user(
            self, session: AsyncSession, email: str, password: str
    ) -> User:
        if await self.get_identity(session, PROVIDER_LOCAL, email):
            raise AlreadyExist("User with this email already exists")

        user = User()
        session.add(user)
        await session.flush()

        await self.link_identity(
            session, user.id, PROVIDER_LOCAL, email, password_plain=password
        )

        return user

    async def authenticate_local_user(self, session: AsyncSession, email: str, password: str) -> Optional[User]:
        identity = await self.get_identity(session, PROVIDER_LOCAL, email)
        if not identity or not identity.password_hash:
            return None
        if not verify_password(password, identity.password_hash):
            return None

        user = await session.get(User, identity.user_id)
        return user
