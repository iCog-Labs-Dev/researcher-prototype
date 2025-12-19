import time
import uuid
from datetime import datetime, timezone
from typing import TypedDict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete, func, exists

from db import SessionLocal
from services.logging_config import get_logger
from exceptions import NotFound, AlreadyExist
from models import ResearchFinding, ResearchTopic

logger = get_logger(__name__)


class FindingPayload(TypedDict, total=False):
    quality_score: Optional[float]
    findings_content: Optional[str]
    formatted_content: Optional[str]
    research_query: Optional[str]
    findings_summary: Optional[str]
    source_urls: Optional[list[str]]
    citations: Optional[list[str]]
    key_insights: Optional[list[str]]
    search_sources: Optional[list[dict[str, Any]]]


class ResearchService:
    async def get_findings(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        topic_id: uuid.UUID = None,
        unread_only: bool = False,
    ) -> list[ResearchFinding]:
        query = select(ResearchFinding).where(ResearchFinding.user_id == user_id).order_by(ResearchFinding.created_at.desc())

        if topic_id:
            query = query.where(ResearchFinding.topic_id == topic_id)

        if unread_only:
            query = query.where(ResearchFinding.read.is_(False))

        res = await session.execute(query)

        return list(res.scalars().all())

    async def async_get_findings(
        self,
        user_id: uuid.UUID,
        topic_id: uuid.UUID,
    ) -> list[dict]:
        """Async wrapper to get findings by user_id and topic_id (converts to dict format for compatibility)."""
        async with SessionLocal() as session:
            query = (
                select(ResearchFinding)
                .where(
                    and_(
                        ResearchFinding.user_id == user_id,
                        ResearchFinding.topic_id == topic_id
                    )
                )
                .order_by(ResearchFinding.created_at.desc())
            )
            
            res = await session.execute(query)
            findings = list(res.scalars().all())
            
            # Convert to dict format for compatibility with existing code
            return [
                {
                    "finding_id": str(f.id),
                    "topic_name": f.topic_name,
                    "read": f.read,
                    "bookmarked": f.bookmarked,
                    "integrated": f.integrated,
                    "research_time": f.created_at.timestamp() if f.created_at else None,
                    "quality_score": f.quality_score,
                }
                for f in findings
            ]

    async def async_store_research_finding(
        self,
        user_id: uuid.UUID,
        topic_id: uuid.UUID,
        topic_name: str,
        finding_data: FindingPayload,
    ) -> tuple[bool, Optional[str]]:
        try:
            async with SessionLocal.begin() as session:
                query = select(ResearchTopic.id).where(
                    and_(ResearchTopic.id == topic_id, ResearchTopic.user_id == user_id)
                )

                res = await session.execute(query)

                topic = res.scalar_one_or_none()

                if not topic:
                    logger.error(f"Error storing research finding for user {user_id}, topic '{topic_name}': topic not found")

                    return False, None

                finding = ResearchFinding(
                    user_id=user_id,
                    topic_id=topic_id,
                    topic_name=topic_name,
                    quality_score=finding_data.get("quality_score"),
                    findings_content=finding_data.get("findings_content"),
                    formatted_content=finding_data.get("formatted_content"),
                    research_query=finding_data.get("research_query"),
                    findings_summary=finding_data.get("findings_summary"),
                    source_urls=finding_data.get("source_urls"),
                    citations=finding_data.get("citations"),
                    key_insights=finding_data.get("key_insights"),
                    search_sources=finding_data.get("search_sources"),
                )

                session.add(finding)
                await session.flush()

            return True, str(finding.id)
        except Exception as e:
            logger.error(f"Error storing research finding for user {user_id}, topic '{topic_name}': {str(e)}")

        return False, None

    async def async_cleanup_old_research_findings(
        self,
        retention_days: int,
    ) -> bool:
        """Cleanup old research findings globally for all users."""
        try:
            async with SessionLocal.begin() as session:
                query = (
                    delete(ResearchFinding)
                    .where(ResearchFinding.created_at < (func.now() - func.make_interval(0, 0, 0, retention_days)))
                    .returning(ResearchFinding.topic_id)
                )

                res = await session.execute(query)

                deleted_topic_ids_list = res.scalars().all()
                deleted_findings = len(deleted_topic_ids_list)
                touched_topic_ids = set(deleted_topic_ids_list)

                deleted_topics = 0
                if touched_topic_ids:
                    has_findings = exists(
                        select(1).where(ResearchFinding.topic_id == ResearchTopic.id)
                    )
                    query = (
                        delete(ResearchTopic)
                        .where(and_(
                            ResearchTopic.id.in_(touched_topic_ids),
                            ResearchTopic.is_active_research.is_(False),
                            ~has_findings,
                        ))
                    )

                    res = await session.execute(query)

                    deleted_topics = res.rowcount

            logger.info(
                f"Cleanup done. Deleted findings: {deleted_findings}, deleted topics: {deleted_topics}, touched topics: {len(touched_topic_ids)}",
            )

            return True

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")

        return False

    async def mark_finding_as_read(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        finding_id: uuid.UUID,
    ):
        query = select(ResearchFinding).where(
            and_(ResearchFinding.id == finding_id, ResearchFinding.user_id == user_id)
        )

        res = await session.execute(query)

        finding = res.scalar_one_or_none()

        if not finding:
            raise NotFound("Research finding not found")

        if finding.read:
            raise AlreadyExist("Research finding is already in this state")

        finding.read = True

        await session.commit()

    async def mark_finding_bookmarked(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        finding_id: uuid.UUID,
        bookmarked: bool,
    ) -> bool:
        query = select(ResearchFinding).where(
            and_(ResearchFinding.id == finding_id, ResearchFinding.user_id == user_id)
        )

        res = await session.execute(query)

        finding = res.scalar_one_or_none()

        if not finding:
            raise NotFound("Research finding not found")

        if finding.bookmarked == bookmarked:
            raise AlreadyExist("Research finding is already in this state")

        finding.bookmarked = bookmarked

        await session.commit()

        return finding.bookmarked

    async def delete_research_finding(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        finding_id: uuid.UUID,
    ) -> None:
        query = (
            delete(ResearchFinding)
            .where(and_(ResearchFinding.id == finding_id, ResearchFinding.user_id == user_id))
            .returning(ResearchFinding.id)
        )

        res = await session.execute(query)

        deleted_id = res.scalar_one_or_none()

        if deleted_id is None:
            raise NotFound("Research finding not found")

        await session.commit()

    async def delete_all_topic_findings(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        topic_id: uuid.UUID,
    ) -> None:
        query = (
            delete(ResearchFinding)
            .where(and_(ResearchFinding.topic_id == topic_id, ResearchFinding.user_id == user_id))
            .returning(ResearchFinding.id)
        )

        res = await session.execute(query)

        deleted_id = res.scalar_one_or_none()

        if deleted_id is None:
            raise NotFound("Research finding not found")

        await session.commit()
