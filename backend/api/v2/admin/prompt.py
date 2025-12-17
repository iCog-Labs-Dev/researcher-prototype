from __future__ import annotations
from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from dependencies import inject_user_id
from services.prompt import PromptService
from services.prompt_cache import PromptCache
from schemas.admin import (
    PromptUpdateIn,
    PromptTestIn,
    PromptListOut,
    PromptHistoryOut,
    PromptTestOut,
    PromptStatusOut,
    PromptRecord,
    PromptMeta,
    PromptHistoryEntry,
    PromptTestResult,
)

router = APIRouter(prefix="/prompt")


@router.get("", response_model=PromptListOut)
async def get_all_prompts(
    session: Annotated[AsyncSession, Depends(get_session)]
):
    service = PromptService()
    prompts = await service.get_all_prompts(session)

    categories_map: dict[str, list[PromptMeta]] = {}
    prompts_map: dict[str, PromptRecord] = {}

    for prompt in prompts:
        if prompt.category not in categories_map:
            categories_map[prompt.category] = []

        categories_map[prompt.category].append(PromptMeta(
            name=prompt.name, description=prompt.description, variables=prompt.variables, content_length=len(prompt.content)
        ))
        prompts_map[prompt.name] = PromptRecord(
            name=prompt.name,
            content=prompt.content,
            category=prompt.category,
            description=prompt.description,
            variables=prompt.variables,
        )

    return PromptListOut(
        total_prompts=len(prompts),
        categories=categories_map,
        prompts=prompts_map,
    )


@router.get("/{prompt_name}", response_model=PromptRecord)
async def get_prompt(
    session: Annotated[AsyncSession, Depends(get_session)],
    prompt_name: str,
):
    service = PromptService()
    prompt = await service.get_prompt(session, prompt_name)

    return PromptRecord(
        name=prompt.name,
        content=prompt.content,
        category=prompt.category,
        description=prompt.description,
        variables=prompt.variables,
    )


@router.post("/{prompt_name}", response_model=PromptRecord)
async def update_prompt(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: PromptUpdateIn,
    prompt_name: str,
):
    admin_id = request.state.user_id

    service = PromptService()
    prompt = await service.update_prompt(session, prompt_name, body.content, admin_id)

    await PromptCache.refresh_one(prompt_name)

    return PromptRecord(
        name=prompt.name,
        content=prompt.content,
        category=prompt.category,
        description=prompt.description,
        variables=prompt.variables,
    )


@router.get("/{prompt_name}/history", response_model=PromptHistoryOut)
async def get_prompt_history(
    session: Annotated[AsyncSession, Depends(get_session)],
    prompt_name: str,
):
    service = PromptService()
    history = await service.get_prompt_history(session, prompt_name)

    return PromptHistoryOut(
        prompt_name=prompt_name,
        total_versions=len(history),
        history=[
            PromptHistoryEntry(
                created_at=item.created_at,
                user=item.user,
                content=item.content,
                variables=item.variables,
            )
            for item in history
        ]
    )


@router.post("/{prompt_name}/test", response_model=PromptTestOut)
async def test_prompt(
    session: Annotated[AsyncSession, Depends(get_session)],
    body: PromptTestIn,
    prompt_name: str,
):
    service = PromptService()
    result = await service.test_prompt(session, prompt_name, body.variables)

    return PromptTestOut(prompt_name=prompt_name, test_result=PromptTestResult(**result))


@router.get("/status", response_model=PromptStatusOut)
async def get_admin_status(
    session: Annotated[AsyncSession, Depends(get_session)]
):
    service = PromptService()
    prompts = await service.get_all_prompts(session)

    return PromptStatusOut(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        prompts_loaded=len(prompts),
        categories=list(set([p["category"] for p in prompts.values()])),
    )


@router.post("/{prompt_name}/restore", response_model=PromptRecord)
async def restore_prompt(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    prompt_name: str,
):
    admin_id = request.state.user_id

    service = PromptService()
    prompt = await service.restore_prompt(session, prompt_name, admin_id)

    await PromptCache.refresh_one(prompt_name)

    return PromptRecord(
        name=prompt.name,
        content=prompt.content,
        category=prompt.category,
        description=prompt.description,
        variables=prompt.variables,
    )
