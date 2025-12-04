import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from exceptions import NotFound
from models.chat import Chat
from services.user import UserService


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
    ):
        # TODO save chat history
        pass
