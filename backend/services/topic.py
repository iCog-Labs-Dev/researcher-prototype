import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, distinct, delete, update
from sqlalchemy.dialects.postgresql import insert

from db import SessionLocal
from config import DEFAULT_MODEL, MAX_ACTIVE_RESEARCH_TOPICS_PER_USER
from services.logging_config import get_logger
from nodes.topic_extractor_node import topic_extractor_node
from exceptions import CommonError, NotFound, AlreadyExist
from models import ResearchTopic

logger = get_logger(__name__)


class TopicService:
    async def get_topics_by_user_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[ResearchTopic]:
        query = select(ResearchTopic).where(ResearchTopic.user_id == user_id).order_by(ResearchTopic.created_at.desc())

        res = await session.execute(query)

        return list(res.scalars().all())

    async def get_topics_by_chat_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        chat_id: uuid.UUID
    ) -> list[ResearchTopic]:
        query = select(ResearchTopic).where(
            and_(ResearchTopic.chat_id == chat_id, ResearchTopic.user_id == user_id)
        ).order_by(ResearchTopic.created_at.desc())

        res = await session.execute(query)

        return list(res.scalars().all())

    async def get_active_research_topics_by_user_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[ResearchTopic]:
        query = select(ResearchTopic).where(
            and_(ResearchTopic.user_id == user_id, ResearchTopic.is_active_research.is_(True))
        ).order_by(ResearchTopic.created_at.asc())

        res = await session.execute(query)

        return list(res.scalars().all())

    async def async_get_active_research_topics(
        self,
        user_id: Optional[str] = None,
    ) -> tuple[bool, list[ResearchTopic]]:
        try:
            async with SessionLocal() as session:
                query = select(ResearchTopic).where(ResearchTopic.is_active_research.is_(True)).order_by(ResearchTopic.created_at.asc())

                if user_id is not None:
                    query = query.where(ResearchTopic.user_id == user_id)

                res = await session.execute(query)

                topics = list(res.scalars().all())

            return True, topics
        except Exception as e:
            logger.error(f"Error getting active research topics: {str(e)}")

            return False, []

    async def async_create_topic(
        self,
        user_id: str,
        name: str,
        description: str,
        confidence_score: float,
        is_active_research: bool,
        conversation_context: str = "",
        strict: bool = False,
    ) -> ResearchTopic:
        async with SessionLocal.begin() as session:
            user_uuid = uuid.UUID(user_id)

            if is_active_research:
                await self._check_limit_research_topics(session, user_uuid)
            
            topic = await self._create_topic(
                session,
                user_uuid,
                name,
                description,
                confidence_score,
                is_active_research=is_active_research,
                conversation_context=conversation_context,
                strict=strict,
            )

        return topic

    async def get_count_chats_by_user_id(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        query = select(func.count(distinct(ResearchTopic.chat_id))).where(
            and_(ResearchTopic.user_id == user_id, ResearchTopic.chat_id.is_not(None))
        )

        res = await session.execute(query)

        return int(res.scalar_one())

    async def get_user_topic_stats(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> tuple[int, int, float, int]:
        query = select(
            func.count(ResearchTopic.id),
            func.count(distinct(ResearchTopic.chat_id)),
            func.avg(ResearchTopic.confidence_score),
            func.min(ResearchTopic.created_at),
        ).where(ResearchTopic.user_id == user_id)

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
    ) -> tuple[int, list[ResearchTopic]]:
        query = select(func.count()).where(
            and_(ResearchTopic.user_id == user_id, ResearchTopic.chat_id == chat_id)
        )

        res = await session.execute(query)

        available_count = int(res.scalar_one())

        query = (
            select(ResearchTopic)
            .where(and_(ResearchTopic.user_id == user_id, ResearchTopic.chat_id == chat_id))
            .order_by(ResearchTopic.confidence_score.desc(), ResearchTopic.created_at.desc(), ResearchTopic.id.desc())
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
    ) -> ResearchTopic:
        if is_active_research:
            await self._check_limit_research_topics(session, user_id)

        topic = await self._create_topic(
            session,
            user_id,
            name,
            description,
            confidence_score,
            is_active_research=is_active_research,
            strict=True,
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
        query = select(ResearchTopic).where(
            and_(ResearchTopic.id == topic_id, ResearchTopic.user_id == user_id)
        )

        res = await session.execute(query)

        topic = res.scalar_one_or_none()

        if not topic:
            raise NotFound("Research topic not found")

        if topic.is_active_research == enable:
            raise AlreadyExist("Research topic is already in this state")

        if enable:
            await self._check_limit_research_topics(session, user_id)

        topic.is_active_research = enable

        # Also create/update TopicScore record for motivation system
        from database.motivation_repository import MotivationRepository
        from models.motivation import TopicScore
        motivation_repo = MotivationRepository(session)
        
        # For newly enabled topics, set high motivation score (1.0) since they've never been researched
        # This ensures they're immediately eligible for research
        # For disabled topics, reset motivation score to 0 to prevent them from being picked up
        motivation_score = None
        if enable:
            # Check if this is a new topic (never researched)
            existing_score = await motivation_repo.get_topic_score(user_id, topic.name)
            if not existing_score or existing_score.last_researched is None:
                motivation_score = 1.0  # High priority for new topics
            logger.info(f"✅ Enabled research for topic '{topic.name}' (user: {user_id})")
        else:
            # When disabling, reset motivation score to 0 to ensure it's not picked up by research cycle
            motivation_score = 0.0
            logger.info(f"🛑 Disabled research for topic '{topic.name}' (user: {user_id})")
        
        # Update TopicScore directly in the same transaction (don't use repository.update which commits)
        existing_score = await motivation_repo.get_topic_score(user_id, topic.name)
        if existing_score:
            # Update existing TopicScore in the same transaction
            existing_score.is_active_research = enable
            if motivation_score is not None:
                existing_score.motivation_score = motivation_score
            session.add(existing_score)
            logger.info(f"📊 Updated TopicScore for '{topic.name}': is_active_research={enable}, motivation_score={motivation_score}")
        else:
            # Create new TopicScore if it doesn't exist
            if not topic_id:
                raise ValueError("topic_id is required when creating a topic score")
            new_score = TopicScore(
                user_id=user_id,
                topic_id=topic_id,
                topic_name=topic.name,
                is_active_research=enable,
                motivation_score=motivation_score or 0.0,
                engagement_score=0.0,
                success_rate=0.5,
                staleness_pressure=0.0,
                staleness_coefficient=1.0,
                total_findings=0,
                read_findings=0,
                bookmarked_findings=0,
                integrated_findings=0,
                meta_data={}
            )
            session.add(new_score)
            logger.info(f"📊 Created TopicScore for '{topic.name}': is_active_research={enable}, motivation_score={motivation_score or 0.0}")

        await session.commit()
        
        # Refresh topic to ensure we have latest state
        await session.refresh(topic)

        return topic.is_active_research

    async def delete_topics_by_chat(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        chat_id: uuid.UUID,
    ) -> None:
        query = (
            delete(ResearchTopic)
            .where(and_(ResearchTopic.user_id == user_id, ResearchTopic.chat_id == chat_id))
            .returning(ResearchTopic.id)
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
            delete(ResearchTopic)
            .where(and_(ResearchTopic.id == topic_id, ResearchTopic.user_id == user_id))
            .returning(ResearchTopic.id)
        )

        res = await session.execute(query)

        deleted_id = res.scalar_one_or_none()

        if deleted_id is None:
            raise NotFound("Research topic not found")

        await session.commit()

    async def delete_non_activated_topics(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> None:
        query = (
            delete(ResearchTopic)
            .where(and_(ResearchTopic.user_id == user_id, ResearchTopic.is_active_research.is_(False)))
            .returning(ResearchTopic.id)
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
            delete(ResearchTopic)
            .where(
                and_(
                    ResearchTopic.user_id == user_id,
                    ResearchTopic.created_at < (func.now() - func.make_interval(0, 0, 0, retention_days)),
                )
            )
        )

        await session.execute(query)

        await session.commit()

    async def async_update_topic_last_researched(
        self,
        topic_id: str,
    ) -> bool:
        try:
            async with SessionLocal.begin() as session:
                query = (
                    update(ResearchTopic)
                    .where(ResearchTopic.id == topic_id)
                    .values(
                        last_researched=func.now(),
                        research_count=ResearchTopic.research_count + 1,
                    )
                )

                await session.execute(query)

            return True
        except Exception as e:
            logger.error(f"Error updating topic '{topic_id} last researched time': {str(e)}")

            return False

    async def async_extract_and_store_topics(
        self,
        user_id: str,
        chat_id: str,
        state: dict,
        conversation_context: str,
    ) -> bool:
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
                    async with SessionLocal.begin() as session:
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

                else:
                    logger.warning(f"🔍 Background: No topics extracted for chat {chat_id}")

                return True
            else:
                logger.warning(
                    f"🔍 Background: Topic extraction failed for chat {chat_id}: {topic_results.get('message', 'Unknown error')}"
                )


        except Exception as e:
            logger.error(
                f"🔍 Background: Error in topic extraction for chat {chat_id}: {str(e)}",
                exc_info=True,
            )

        return False

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
        strict: bool = False,
    ) -> Optional[ResearchTopic]:
        norm_name = name.strip()

        query = insert(ResearchTopic).values(
            user_id=user_id,
            chat_id=chat_id,
            name=norm_name,
            description=description,
            confidence_score=confidence_score,
            conversation_context=conversation_context,
            is_active_research=is_active_research,
        ).on_conflict_do_nothing(
            constraint="uq_research_topics_user_name"
        ).returning(ResearchTopic)

        res = await session.execute(query)

        topic = res.scalar_one_or_none()
        if topic:
            if strict:
                return topic
            else:
                return None

        if strict:
            raise AlreadyExist(f"Topic '{norm_name}' already exists")
        else:
            return None

    async def _check_limit_research_topics(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ):
        query = select(func.count()).select_from(ResearchTopic).where(
            and_(ResearchTopic.user_id == user_id, ResearchTopic.is_active_research == True)
        )

        res = await session.execute(query)

        count = int(res.scalar_one())

        if count >= MAX_ACTIVE_RESEARCH_TOPICS_PER_USER:
            raise CommonError(f"You have reached the maximum limit of {MAX_ACTIVE_RESEARCH_TOPICS_PER_USER} active research topics. Please disable some existing topics before adding new ones.")
