import uuid
import httpx
from typing import Optional, TypedDict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from config import CHAT_MEMORY_URL, CHAT_MEMORY_TIMEOUT
from exceptions import NotFound, CommonError
from services.logging_config import get_logger
from models.chat import Chat

logger = get_logger(__name__)


class SaveHistoryPayload(TypedDict):
    question: str
    answer: str
    user_id: str


class GetHistoryPayload(TypedDict):
    user_id: str
    limit: int


class ChatService:
    async def get_chats(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[Chat]:
        query = select(Chat).where(Chat.user_id == user_id).order_by(Chat.created_at.desc())

        res = await session.execute(query)

        return list(res.scalars().all())

    async def get_or_create_chat_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        message: str,
        chat_id: Optional[uuid.UUID] = None
    ) -> uuid.UUID:
        if chat_id:
            query = select(Chat).where(
                and_(Chat.id ==  chat_id, Chat.user_id == user_id)
            )

            res = await session.execute(query)

            chat = res.scalar_one_or_none()
            if chat:
                return chat.id
            else:
                raise NotFound("Chat not found")

        chat = Chat(user_id=user_id, name=message)

        session.add(chat)

        await session.flush()

        return chat.id

    async def save_history(
        self,
        chat_id: uuid.UUID,
        user_text: str,
        assistant_text: str,
    ) -> None:
        try:
            async with httpx.AsyncClient(timeout=CHAT_MEMORY_TIMEOUT) as client:
                result = await client.post(
                    url=f"{CHAT_MEMORY_URL}/pairs",
                    json=SaveHistoryPayload(
                        question=user_text, answer=assistant_text, user_id=str(chat_id),
                    )
                )

                result.raise_for_status()
        except (httpx.TimeoutException, httpx.HTTPError) as e:
            logger.error(f"Chat memory request failed: {str(e)}")

            raise CommonError("Chat memory request failed")

    async def get_history(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        chat_id: uuid.UUID,
        limit: int,
    ) -> list[dict[str, Any]]:
        query = select(Chat).where(
            and_(Chat.id == chat_id, Chat.user_id == user_id)
        )

        res = await session.execute(query)

        chat = res.scalar_one_or_none()
        if not chat:
            raise NotFound("Chat not found")

        try:
            async with httpx.AsyncClient(timeout=CHAT_MEMORY_TIMEOUT) as client:
                result = await client.post(
                    url=f"{CHAT_MEMORY_URL}/pairs/last",
                    json=GetHistoryPayload(
                        user_id=str(chat_id), limit=limit,
                    )
                )

                result.raise_for_status()

                data = result.json()
                if not isinstance(data, list):
                    logger.error(f"Chat memory returned unexpected payload: {data}")

                    raise CommonError("Chat memory returned unexpected payload")

                return data
        except (httpx.TimeoutException, httpx.HTTPError) as e:
            logger.error(f"Chat memory request failed: {str(e)}")

            raise CommonError("Chat memory request failed")
