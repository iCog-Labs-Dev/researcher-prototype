from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from schemas.auth import AuthLocalIn, TokenOut
from exceptions import AuthError
from services.auth import AuthService
from utils.jwt import create_jwt_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenOut, status_code=201)
async def register(
    body: AuthLocalIn,
    session: Annotated[AsyncSession, Depends(get_session)]
) -> TokenOut:
    service = AuthService()
    user = await service.register_local_user(session, body.email, body.password)

    return TokenOut(access_token=create_jwt_token(str(user.id)))

@router.post("/login", response_model=TokenOut)
async def login(
    body: AuthLocalIn,
    session: Annotated[AsyncSession, Depends(get_session)]
) -> TokenOut:
    service = AuthService()
    user = await service.authenticate_local_user(session, body.email, body.password)
    if not user:
        raise AuthError("Invalid credentials")

    return TokenOut(access_token=create_jwt_token(str(user.id)))
