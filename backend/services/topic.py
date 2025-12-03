import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, distinct, delete

from db import SessionLocal
from config import DEFAULT_MODEL, MAX_ACTIVE_RESEARCH_TOPICS_PER_USER
from services.logging_config import get_logger
from nodes.topic_extractor_node import topic_extractor_node
from exceptions import CommonError, NotFound, AlreadyExist
from models import Topic

logger = get_logger(__name__)


class TopicService:
    async def get_topics_by_user_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[Topic]:
        query = select(Topic).where(Topic.user_id == user_id).order_by(Topic.created_at.desc())

        res = await session.execute(query)

        return list(res.scalars().all())

    async def get_topics_by_chat_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        chat_id: uuid.UUID
    ) -> list[Topic]:
        query = select(Topic).where(
            and_(Topic.chat_id == chat_id, Topic.user_id == user_id)
        ).order_by(Topic.created_at.desc())

        res = await session.execute(query)

        return list(res.scalars().all())

    async def get_active_research_topics_by_user_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[Topic]:
        query = select(Topic).where(
            and_(Topic.user_id == user_id, Topic.is_active_research.is_(True))
        ).order_by(Topic.created_at.asc())

        res = await session.execute(query)

        return list(res.scalars().all())

    async def get_active_research_topics(
        self,
        session: AsyncSession,
    ) -> list[Topic]:
        query = (
            select(Topic)
            .where(Topic.is_active_research.is_(True))
            .order_by(Topic.created_at.asc())
        )

        res = await session.execute(query)

        return list(res.scalars().all())

    async def get_count_chats_by_user_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        query = select(func.count(distinct(Topic.chat_id))).where(
            and_(Topic.user_id == user_id, Topic.chat_id.is_not(None))
        )

        res = await session.execute(query)

        return int(res.scalar_one())

    async def get_user_topic_stats(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> tuple[int, int, float, int]:
        query = select(
            func.count(Topic.id),
            func.count(distinct(Topic.chat_id)),
            func.avg(Topic.confidence_score),
            func.min(Topic.created_at),
        ).where(Topic.user_id == user_id)

        res = await session.execute(query)

        total_topics, sessions_count, avg_score, min_created = res.one()

        if avg_score is None:
            avg_score = 0.0

        if min_created is None:
            oldest_age_days = 0
        else:
            now = datetime.now(timezone.utc)
            oldest_age_days = max(0, int((now - min_created).total_seconds() // 86400))

        return total_topics, sessions_count, avg_score, oldest_age_days

    async def get_top_topics_by_chat(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        chat_id: uuid.UUID,
        limit: int,
    ) -> tuple[int, list[Topic]]:
        query = select(func.count()).where(
            and_(Topic.user_id == user_id, Topic.chat_id == chat_id)
        )

        res = await session.execute(query)

        available_count = int(res.scalar_one())

        query = (
            select(Topic)
            .where(and_(Topic.user_id == user_id, Topic.chat_id == chat_id))
            .order_by(Topic.confidence_score.desc(), Topic.created_at.desc(), Topic.id.desc())
            .limit(limit)
        )

        res = await session.execute(query)

        topics = list(res.scalars().all())

        return available_count, topics

    async def create_topic(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        name: str,
        description: str,
        confidence_score: float,
        is_active_research: bool,
    ) -> Topic:
        if is_active_research:
            await self._check_limit_research_topics(session, user_id)

        topic = await self._create_topic(
            session, user_id, name, description, confidence_score, is_active_research=is_active_research
        )

        await session.commit()

        return topic

    async def update_active_research(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        topic_id: uuid.UUID,
        enable: bool,
    ) -> bool:
        query = select(Topic).where(
            and_(Topic.id == topic_id, Topic.user_id == user_id)
        )

        res = await session.execute(query)

        topic = res.scalar_one_or_none()

        if not topic:
            raise NotFound("Topic not found")

        if topic.is_active_research == enable:
            raise AlreadyExist("Topic is already in this state")

        if enable:
            await self._check_limit_research_topics(session, user_id)

        topic.is_active_research = enable

        await session.commit()

        return topic.is_active_research

    async def delete_topics_by_chat(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        chat_id: uuid.UUID,
    ) -> None:
        query = (
            delete(Topic)
            .where(and_(Topic.user_id == user_id, Topic.chat_id == chat_id))
            .returning(Topic.id)
        )

        res = await session.execute(query)

        deleted_ids = res.scalars().all()

        if not deleted_ids:
            raise NotFound("No topics found for this chat")

        await session.commit()

    async def delete_topic_by_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        topic_id: uuid.UUID,
    ) -> None:
        query = (
            delete(Topic)
            .where(and_(Topic.id == topic_id, Topic.user_id == user_id))
            .returning(Topic.id)
        )

        res = await session.execute(query)

        deleted_id = res.scalar_one_or_none()

        if deleted_id is None:
            raise NotFound("Topic not found")

        await session.commit()

    async def delete_non_activated_topics(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> None:
        query = (
            delete(Topic)
            .where(and_(Topic.user_id == user_id, Topic.is_active_research.is_(False)))
            .returning(Topic.id)
        )

        res = await session.execute(query)

        deleted_ids = res.scalars().all()

        if not deleted_ids:
            raise NotFound("No non-activated topics found")

        await session.commit()

    async def cleanup_topics(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        retention_days: int = 30,
    ) -> None:
        query = (
            delete(Topic)
            .where(
                and_(
                    Topic.user_id == user_id,
                    Topic.created_at < (func.now() - func.make_interval(0, 0, 0, retention_days)),
                )
            )
        )

        await session.execute(query)

        rn = func.row_number().over(
            partition_by=(Topic.user_id, Topic.chat_id, func.lower(Topic.name)),
            order_by=(Topic.created_at.desc(), Topic.id.desc()),
        ).label("rn")

        subquery = (
            select(Topic.id, rn)
            .where(Topic.user_id == user_id)
            .subquery()
        )

        query = (
            delete(Topic).where(
                Topic.id.in_(
                    select(subquery.c.id).where(subquery.c.rn > 1)
                )
            )
        )

        await session.execute(query)

        await session.commit()

    async def async_extract_and_store_topics(
        self,
        user_id: uuid.UUID,
        chat_id: uuid.UUID,
        state: dict,
        conversation_context: str,
    ):
        try:
            logger.info(f"🔍 Background: Starting topic extraction for chat {chat_id}")

            # Create a clean state for topic extraction that includes useful context
            # but avoids overwhelming information that could confuse the LLM
            clean_state = {
                "messages": state.get("messages", []),
                "user_id": user_id,
                "thread_id": chat_id,
                "model": state.get("model", DEFAULT_MODEL),
                "module_results": {},
                "workflow_context": {},
                # Include memory context but the prompt will ensure it's used appropriately
                "memory_context": state.get("memory_context")
            }

            logger.debug(f"🔍 Background: Using clean state with {len(clean_state['messages'])} messages")

            # Run topic extraction on the clean conversation state
            updated_state = topic_extractor_node(clean_state)

            # Check if topic extraction was successful
            topic_results = updated_state.get("module_results", {}).get("topic_extractor", {})

            if topic_results.get("success", False):
                raw_topics = topic_results.get("result", [])

                if raw_topics:
                    async with SessionLocal() as session:
                        for topic in raw_topics:
                            await self._create_topic(
                                session,
                                user_id,
                                topic.get("name"),
                                topic.get("description"),
                                topic.get("confidence_score"),
                                chat_id=chat_id,
                                conversation_context=conversation_context
                            )

                        await session.commit()

                else:
                    logger.info(f"🔍 Background: No topics extracted for chat {chat_id}")
            else:
                logger.warning(
                    f"🔍 Background: Topic extraction failed for chat {chat_id}: {topic_results.get('message', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(
                f"🔍 Background: Error in topic extraction for chat {chat_id}: {str(e)}",
                exc_info=True,
            )

    async def _create_topic(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        name: str,
        description: str,
        confidence_score: float,
        chat_id: uuid.UUID = None,
        conversation_context: str = "",
        is_active_research: bool = False,
    ) -> Topic:
        topic = Topic(
            user_id=user_id,
            chat_id=chat_id,
            name=name,
            description=description,
            confidence_score=confidence_score,
            conversation_context=conversation_context,
            is_active_research=is_active_research,
        )

        session.add(topic)

        return topic

    async def _check_limit_research_topics(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ):
        query = select(func.count()).select_from(Topic).where(
            and_(Topic.user_id == user_id, Topic.is_active_research == True)
        )

        res = await session.execute(query)

        count = int(res.scalar_one())

        if count >= MAX_ACTIVE_RESEARCH_TOPICS_PER_USER:
            raise CommonError(f"You have reached the maximum limit of {MAX_ACTIVE_RESEARCH_TOPICS_PER_USER} active research topics. Please disable some existing topics before adding new ones.")
