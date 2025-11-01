from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from schemas.auth import AuthLocalIn, TokenOut, GoogleLoginIn
from exceptions import AuthError
from services.auth import AuthService
from utils.jwt import create_jwt_token

router = APIRouter(prefix="/auth", tags=["v2/auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(
    session: Annotated[AsyncSession, Depends(get_session)],
    body: AuthLocalIn,
) -> TokenOut:
    service = AuthService()
    user = await service.register_local(session, str(body.email), body.password)

    return TokenOut(access_token=create_jwt_token(str(user.id)))


@router.post("/login", response_model=TokenOut)
async def login(
    session: Annotated[AsyncSession, Depends(get_session)],
    body: AuthLocalIn,
) -> TokenOut:
    service = AuthService()
    user = await service.login_local(session, str(body.email), body.password)

    return TokenOut(access_token=create_jwt_token(str(user.id)))


@router.post("/google", response_model=TokenOut)
async def google_login(
    session: Annotated[AsyncSession, Depends(get_session)],
    body: GoogleLoginIn,
):
    service = AuthService()
    user = await service.login_google(session, body.id_token)

    return TokenOut(access_token=create_jwt_token(str(user.id)))
