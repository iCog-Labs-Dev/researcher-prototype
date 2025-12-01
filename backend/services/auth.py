from __future__ import annotations
import uuid
from typing import Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

from exceptions import (
    CommonError,
    AlreadyExist,
    AuthError,
)
from utils.password import hash_password, verify_password
from utils.helpers import normalize_provider_user_id, generate_display_name_from_user_id
from models.user import User
from models.user import UserProfile
from models.identity import Identity
from config import GOOGLE_CLIENT_ID

PROVIDER_LOCAL  = "local"
PROVIDER_GOOGLE  = "google"


class AuthService:
    def __init__(self):
        pass

    async def register_local(
        self,
        session: AsyncSession,
        email: str,
        password: str,
    ) -> User:
        if await self._get_identity(session, PROVIDER_LOCAL, email):
            raise AlreadyExist("A user with this email already exists. Please log in instead.")

        user = User()
        session.add(user)
        await session.flush()

        profile = UserProfile(
            user_id=user.id,
            meta_data={
                "display_name": generate_display_name_from_user_id(str(user.id)),
                "email": email,
            },
        )
        session.add(profile)

        await self._link_identity(
            session, user.id, PROVIDER_LOCAL, email, password_plain=password
        )

        await session.commit()

        return user

    async def login_local(
        self,
        session: AsyncSession,
        email: str,
        password: str,
    ) -> User:
        identity = await self._get_identity(session, PROVIDER_LOCAL, email)
        if not identity or not identity.password_hash:
            raise AuthError("Invalid credentials")
        if not verify_password(password, identity.password_hash):
            raise AuthError("Invalid credentials")

        user = await session.get(User, identity.user_id)
        if not user:
            raise AuthError("Invalid credentials")

        return user

    async def login_google(
        self,
        session: AsyncSession,
        raw_id_token: str,
    ) -> User:
        google_info = await self._verify_google_id_token(raw_id_token)

        google_sub = google_info.get("sub")
        google_email = google_info.get("email")
        is_verified = google_info.get("email_verified")
        google_name = google_info.get("name")

        if not is_verified:
            raise AuthError("Google account email is not verified")

        identity = await self._get_identity(session, PROVIDER_GOOGLE, google_sub)
        if identity:
            user = await session.get(User, identity.user_id)

            return user

        local_identity = await self._get_identity(session, PROVIDER_LOCAL, google_email)
        if local_identity:
            user = await session.get(User, local_identity.user_id)

            await self._link_identity(
                session, user.id, PROVIDER_GOOGLE, google_sub
            )

            await session.commit()

            return user

        user = User()
        session.add(user)
        await session.flush()

        profile = UserProfile(
            user_id=user.id,
            meta_data={
                "display_name": google_name if google_name else generate_display_name_from_user_id(str(user.id)),
                "email": google_email,
            },
        )
        session.add(profile)

        await self._link_identity(
            session, user.id, PROVIDER_GOOGLE, google_sub
        )

        await session.commit()

        return user

    async def _get_identity(
        self,
        session: AsyncSession,
        provider: str,
        provider_user_id: str,
    ) -> Optional[Identity]:
        pid = normalize_provider_user_id(provider, provider_user_id)
        query = select(Identity).where(
            and_(Identity.provider == provider, Identity.provider_user_id == pid)
        )

        res = await session.execute(query)

        return res.scalar_one_or_none()

    async def _link_identity(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        provider: str,
        provider_user_id: str,
        password_plain: Optional[str] = None,
    ) -> Identity:
        pid = normalize_provider_user_id(provider, provider_user_id)

        password_hash: Optional[str] = None
        if provider == PROVIDER_LOCAL:
            if not password_plain:
                raise CommonError("Password is required for local provider")
            password_hash = hash_password(password_plain)
        else:
            if password_plain is not None:
                raise CommonError("Password must not be provided for non-local providers")

        identity = Identity(
            user_id=user_id,
            provider=provider,
            provider_user_id=pid,
            password_hash=password_hash,
        )
        session.add(identity)

        return identity

    async def _verify_google_id_token(
        self,
        raw_id_token: str
    ) -> Dict[str, Any]:
        try:
            request = grequests.Request()
            payload = id_token.verify_oauth2_token(raw_id_token, request, GOOGLE_CLIENT_ID)
        except Exception as e:
            raise AuthError("Invalid Google token") from e

        sub = payload.get("sub")
        email = payload.get("email", "").lower().strip()
        email_verified = bool(payload.get("email_verified", False))
        name = payload.get("name", "").strip()

        if not sub or not email:
            raise AuthError("Google token missing required claims")

        return {
            "sub": sub,
            "email": email,
            "email_verified": email_verified,
            "name": name,
        }
