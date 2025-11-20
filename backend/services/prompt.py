from __future__ import annotations
from string import Formatter
from typing import Any, Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.prompt import Prompt, PromptHistory
from exceptions import NotFound
from models.user import UserProfile


class PromptService:
    async def get_all_prompts(self, session: AsyncSession) -> List[Prompt]:
        res = await session.execute(select(Prompt))
        items: list[Prompt] = list(res.scalars().all())

        return items

    async def get_prompt(self, session: AsyncSession, name: str) -> Optional[Prompt]:
        prompt = await session.scalar(select(Prompt).where(Prompt.name == name))

        if not prompt:
            raise NotFound(f"Prompt '{name}' not found")

        return prompt

    async def update_prompt(self, session: AsyncSession, name: str, new_content: str, admin_user_id: UUID) -> bool:
        prompt = await session.scalar(select(Prompt).where(Prompt.name == name).with_for_update())

        if not prompt:
            raise NotFound(f"Prompt '{name}' not found")

        prompt.content = new_content
        variables = sorted({field for _, field, _, _ in Formatter().parse(new_content) if field})
        prompt.variables = sorted(set(variables))
        prompt.updated_by_user_id = admin_user_id

        await session.commit()

        return prompt

    async def get_prompt_history(self, session: AsyncSession, name: str) -> list[PromptHistory]:
        prompt = await session.scalar(select(Prompt).where(Prompt.name == name))

        if not prompt:
            raise NotFound(f"Prompt '{name}' not found")

        result = await session.execute(
            select(PromptHistory)
            .where(PromptHistory.prompt_id == prompt.id)
            .order_by(PromptHistory.created_at.desc())
            .options(
                selectinload(PromptHistory.updated_by_profile).load_only(UserProfile.user_id, UserProfile.meta_data)
            )
        )

        return list(result.scalars().all())

    async def test_prompt(self, session: AsyncSession, name: str, variables: dict[str, str]) -> dict[str, Any]:
        prompt = await session.scalar(select(Prompt).where(Prompt.name == name))

        if not prompt:
            raise NotFound(f"Prompt '{name}' not found")

        try:
            formatted = prompt.content.format(**variables)
            return {
                "success": True,
                "formatted_prompt": formatted,
                "original_prompt": prompt.content,
                "variables_used": variables,
                "missing_variables": [],
            }
        except KeyError as e:
            missing = str(e).strip("'\"")
            required = prompt.variables or []
            provided = list(variables.keys())
            missing_vars = [v for v in required if v not in provided]
            return {
                "success": False,
                "error": f"Missing required variable: {missing}",
                "required_variables": required,
                "provided_variables": provided,
                "missing_variables": missing_vars,
            }

    async def restore_prompt(self, session: AsyncSession, name: str, admin_user_id: str) -> Prompt:
        prompt = await session.scalar(select(Prompt).where(Prompt.name == name).with_for_update())

        if not prompt:
            raise NotFound(f"Prompt '{name}' not found")

        history = await session.scalar(
            select(PromptHistory)
            .where(PromptHistory.prompt_id == prompt.id)
            .order_by(PromptHistory.created_at.desc())
            .limit(1)
        )

        if not history:
            raise NotFound(f"History for '{name}' prompt not found")

        prompt.content = history.content
        prompt.variables = history.variables
        prompt.updated_by_user_id = admin_user_id

        await session.commit()

        return prompt
