import time
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from db import SessionLocal
from services.logging_config import get_logger
from exceptions import NotFound, AlreadyExist
from models import ResearchFinding

logger = get_logger(__name__)


class ResearchService:
    async def get_findings(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        topic_id: uuid.UUID = None,
        unread_only: bool = False,
    ) -> list[ResearchFinding]:
        query = select(ResearchFinding).where(ResearchFinding.user_id == user_id).order_by(ResearchFinding.research_time.desc())

        if topic_id:
            query = query.where(ResearchFinding.topic_id == topic_id)

        if unread_only:
            query = query.where(ResearchFinding.read.is_(False))

        res = await session.execute(query)

        return list(res.scalars().all())

    async def cleanup_old_research_findings(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        retention_days: int,
    ) -> int:
        """Delete research findings older than retention_days for a user."""
        cutoff_time = time.time() - (retention_days * 24 * 3600)
        
        query = (
            delete(ResearchFinding)
            .where(
                and_(
                    ResearchFinding.user_id == user_id,
                    ResearchFinding.research_time < cutoff_time
                )
            )
            .returning(ResearchFinding.id)
        )
        
        res = await session.execute(query)
        deleted_ids = list(res.scalars().all())
        await session.commit()
        
        deleted_count = len(deleted_ids)
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old research findings for user {user_id}")
        
        return deleted_count

    async def async_get_findings(
        self,
        user_id: uuid.UUID,
        topic_name: str = None,
        unread_only: bool = False,
    ) -> list[dict]:
        """Async wrapper to get findings by user_id and optional topic_name (converts to dict format for compatibility)."""
        async with SessionLocal() as session:
            query = select(ResearchFinding).where(ResearchFinding.user_id == user_id)
            
            if topic_name:
                query = query.where(ResearchFinding.topic_name == topic_name)
            
            if unread_only:
                query = query.where(ResearchFinding.read.is_(False))
            
            query = query.order_by(ResearchFinding.research_time.desc())
            
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
                    "research_time": f.research_time,
                    "quality_score": f.quality_score,
                }
                for f in findings
            ]

    async def async_cleanup_old_research_findings(
        self,
        user_id: uuid.UUID,
        retention_days: int,
    ) -> int:
        """Async wrapper to cleanup old research findings (creates own session)."""
        async with SessionLocal.begin() as session:
            return await self.cleanup_old_research_findings(session, user_id, retention_days)

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
