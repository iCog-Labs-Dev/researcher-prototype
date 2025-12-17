import asyncio
from typing import Dict, List

from db import SessionLocal
from .prompt import PromptService


class PromptCache:
    _prompts: Dict[str, str] = {}
    _vars: Dict[str, List[str]] = {}
    _lock = asyncio.Lock()

    @classmethod
    def get(cls, name: str, default: str = "") -> str:
        return cls._prompts.get(name, default)

    @classmethod
    async def refresh_one(cls, name: str) -> None:
        service = PromptService()

        async with SessionLocal() as session:
            prompt = await service.get_prompt(session, name)

            async with cls._lock:
                cls._prompts[name] = prompt.content
                cls._vars[name] = prompt.variables or []

    @classmethod
    async def refresh_all(cls) -> None:
        service = PromptService()

        async with SessionLocal() as session:
            prompts = await service.get_all_prompts(session)

            async with cls._lock:
                cls._prompts = {p.name: p.content for p in prompts}
                cls._vars = {p.name: (p.variables or []) for p in prompts}
