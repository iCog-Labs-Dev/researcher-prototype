"""
Motivation repository providing comprehensive CRUD operations for motivation system models.
"""

import time
import uuid
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload

from models.motivation import TopicScore, MotivationConfig
from .base_repository import BaseRepository
from services.logging_config import get_logger

logger = get_logger(__name__)


class MotivationRepository:
    """
    Comprehensive repository for motivation system operations.
    
    This repository provides all CRUD operations for TopicScore and MotivationConfig models,
    replacing the scattered database logic in services/motivation_db_service.py.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.topic_score_repo = BaseRepository(session, TopicScore)
        self.motivation_config_repo = BaseRepository(session, MotivationConfig)
    
    # TopicScore CRUD operations
    
    async def get_topic_score(self, user_id: uuid.UUID, topic_name: str) -> Optional[TopicScore]:
        """Get topic score for a specific user and topic."""
        result = await self.session.execute(
            select(TopicScore).where(
                and_(TopicScore.user_id == user_id, TopicScore.topic_name == topic_name)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_topic_scores(
        self, 
        user_id: uuid.UUID, 
        active_only: bool = False,
        limit: Optional[int] = None,
        order_by_motivation: bool = True
    ) -> List[TopicScore]:
        """Get all topic scores for a user."""
        query = select(TopicScore).where(TopicScore.user_id == user_id)
        
        if active_only:
            query = query.where(TopicScore.is_active_research == True)
        
        if order_by_motivation:
            query = query.order_by(TopicScore.motivation_score.desc())
        else:
            query = query.order_by(TopicScore.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def create_topic_score(
        self,
        user_id: uuid.UUID,
        topic_id: uuid.UUID,
        topic_name: str,
        motivation_score: float = 0.0,
        engagement_score: float = 0.0,
        success_rate: float = 0.5,
        staleness_pressure: float = 0.0,
        last_researched: Optional[float] = None,
        staleness_coefficient: float = 1.0,
        is_active_research: bool = False,
        total_findings: int = 0,
        read_findings: int = 0,
        bookmarked_findings: int = 0,
        integrated_findings: int = 0,
        average_quality: Optional[float] = None,
        last_quality_update: Optional[float] = None,
        meta_data: Optional[Dict[str, Any]] = None
    ) -> TopicScore:
        """Create a new topic score."""
        topic_score = TopicScore(
            user_id=user_id,
            topic_id=topic_id,
            topic_name=topic_name,
            motivation_score=motivation_score,
            engagement_score=engagement_score,
            success_rate=success_rate,
            staleness_pressure=staleness_pressure,
            last_researched=last_researched,
            staleness_coefficient=staleness_coefficient,
            is_active_research=is_active_research,
            total_findings=total_findings,
            read_findings=read_findings,
            bookmarked_findings=bookmarked_findings,
            integrated_findings=integrated_findings,
            average_quality=average_quality,
            last_quality_update=last_quality_update,
            meta_data=meta_data or {}
        )
        
        self.session.add(topic_score)
        await self.session.commit()
        await self.session.refresh(topic_score)
        
        logger.info(f"Created topic score for {topic_name} (user: {user_id})")
        return topic_score
    
    async def update_topic_score(
        self,
        user_id: uuid.UUID,
        topic_name: str,
        motivation_score: Optional[float] = None,
        engagement_score: Optional[float] = None,
        success_rate: Optional[float] = None,
        staleness_pressure: Optional[float] = None,
        last_researched: Optional[float] = None,
        staleness_coefficient: Optional[float] = None,
        is_active_research: Optional[bool] = None,
        total_findings: Optional[int] = None,
        read_findings: Optional[int] = None,
        bookmarked_findings: Optional[int] = None,
        integrated_findings: Optional[int] = None,
        average_quality: Optional[float] = None,
        last_quality_update: Optional[float] = None,
        meta_data: Optional[Dict[str, Any]] = None,
        topic_id: Optional[uuid.UUID] = None,
    ) -> Optional[TopicScore]:
        """Update topic score."""
        existing = await self.get_topic_score(user_id, topic_name)
        
        if not existing:
            logger.warning(f"Topic score not found for {topic_name} (user: {user_id})")
            return None
        
        update_data = {}
        if topic_id is not None:
            update_data['topic_id'] = topic_id
        if motivation_score is not None:
            update_data['motivation_score'] = motivation_score
        if engagement_score is not None:
            update_data['engagement_score'] = engagement_score
        if success_rate is not None:
            update_data['success_rate'] = success_rate
        if staleness_pressure is not None:
            update_data['staleness_pressure'] = staleness_pressure
        if last_researched is not None:
            update_data['last_researched'] = last_researched
        if staleness_coefficient is not None:
            update_data['staleness_coefficient'] = staleness_coefficient
        if is_active_research is not None:
            update_data['is_active_research'] = is_active_research
        if total_findings is not None:
            update_data['total_findings'] = total_findings
        if read_findings is not None:
            update_data['read_findings'] = read_findings
        if bookmarked_findings is not None:
            update_data['bookmarked_findings'] = bookmarked_findings
        if integrated_findings is not None:
            update_data['integrated_findings'] = integrated_findings
        if average_quality is not None:
            update_data['average_quality'] = average_quality
        if last_quality_update is not None:
            update_data['last_quality_update'] = last_quality_update
        if meta_data is not None:
            update_data['meta_data'] = meta_data
        
        if not update_data:
            return existing
        
        return await self.topic_score_repo.update(existing.id, **update_data)
    
    async def create_or_update_topic_score(
        self,
        user_id: uuid.UUID,
        topic_name: str,
        topic_id: Optional[uuid.UUID] = None,
        motivation_score: Optional[float] = None,
        engagement_score: Optional[float] = None,
        success_rate: Optional[float] = None,
        staleness_pressure: Optional[float] = None,
        last_researched: Optional[float] = None,
        staleness_coefficient: Optional[float] = None,
        is_active_research: Optional[bool] = None,
        total_findings: Optional[int] = None,
        read_findings: Optional[int] = None,
        bookmarked_findings: Optional[int] = None,
        integrated_findings: Optional[int] = None,
        average_quality: Optional[float] = None,
        last_quality_update: Optional[float] = None,
        meta_data: Optional[Dict[str, Any]] = None
    ) -> TopicScore:
        """Create or update topic score."""
        existing = await self.get_topic_score(user_id, topic_name)
        
        if existing:
            # Update existing
            updated = await self.update_topic_score(
                user_id, topic_name,
                motivation_score=motivation_score,
                engagement_score=engagement_score,
                success_rate=success_rate,
                staleness_pressure=staleness_pressure,
                last_researched=last_researched,
                staleness_coefficient=staleness_coefficient,
                is_active_research=is_active_research,
                total_findings=total_findings,
                read_findings=read_findings,
                bookmarked_findings=bookmarked_findings,
                integrated_findings=integrated_findings,
                average_quality=average_quality,
                last_quality_update=last_quality_update,
                meta_data=meta_data
            )
            return updated or existing
        else:
            # Create new
            if not topic_id:
                raise ValueError("topic_id is required when creating a topic score")
            return await self.create_topic_score(
                user_id=user_id,
                topic_id=topic_id,
                topic_name=topic_name,
                motivation_score=motivation_score or 0.0,
                engagement_score=engagement_score or 0.0,
                success_rate=success_rate or 0.5,
                staleness_pressure=staleness_pressure or 0.0,
                last_researched=last_researched,
                staleness_coefficient=staleness_coefficient or 1.0,
                is_active_research=is_active_research or False,
                total_findings=total_findings or 0,
                read_findings=read_findings or 0,
                bookmarked_findings=bookmarked_findings or 0,
                integrated_findings=integrated_findings or 0,
                average_quality=average_quality,
                last_quality_update=last_quality_update,
                meta_data=meta_data
            )
    
    async def update_topic_engagement_metrics(
        self,
        user_id: uuid.UUID,
        topic_name: str,
        total_findings: Optional[int] = None,
        read_findings: Optional[int] = None,
        bookmarked_findings: Optional[int] = None,
        integrated_findings: Optional[int] = None
    ) -> Optional[TopicScore]:
        """Update engagement metrics for a topic."""
        return await self.update_topic_score(
            user_id, topic_name,
            total_findings=total_findings,
            read_findings=read_findings,
            bookmarked_findings=bookmarked_findings,
            integrated_findings=integrated_findings
        )
    
    async def delete_topic_score(self, user_id: uuid.UUID, topic_name: str) -> bool:
        """Delete topic score."""
        result = await self.session.execute(
            delete(TopicScore).where(
                and_(TopicScore.user_id == user_id, TopicScore.topic_name == topic_name)
            )
        )
        await self.session.commit()
        
        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(f"Deleted topic score for {topic_name} (user: {user_id})")
        
        return deleted_count > 0
    
    async def delete_user_topic_scores(self, user_id: uuid.UUID) -> int:
        """Delete all topic scores for a user."""
        result = await self.session.execute(
            delete(TopicScore).where(TopicScore.user_id == user_id)
        )
        await self.session.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} topic scores for user {user_id}")
        return deleted_count
    
    # MotivationConfig CRUD operations
    
    async def get_default_config(self) -> Optional[MotivationConfig]:
        """Get the default motivation configuration."""
        result = await self.session.execute(
            select(MotivationConfig).where(MotivationConfig.is_default == True).limit(1)
        )
        return result.scalar_one_or_none()
    
    async def create_default_config(
        self,
        boredom_rate: float = 0.0002,
        curiosity_decay: float = 0.0002,
        tiredness_decay: float = 0.0002,
        satisfaction_decay: float = 0.0002,
        global_threshold: float = 2.0,
        topic_threshold: float = 0.5,
        engagement_weight: float = 0.3,
        quality_weight: float = 0.2,
        staleness_scale: float = 0.0001,
        check_interval: int = 60,
        description: Optional[str] = None,
        config_data: Optional[Dict[str, Any]] = None
    ) -> MotivationConfig:
        """Create default motivation configuration."""
        config = MotivationConfig(
            boredom_rate=boredom_rate,
            curiosity_decay=curiosity_decay,
            tiredness_decay=tiredness_decay,
            satisfaction_decay=satisfaction_decay,
            global_threshold=global_threshold,
            topic_threshold=topic_threshold,
            engagement_weight=engagement_weight,
            quality_weight=quality_weight,
            staleness_scale=staleness_scale,
            check_interval=check_interval,
            is_default=True,
            description=description or "Default motivation configuration",
            config_data=config_data or {}
        )
        
        self.session.add(config)
        await self.session.commit()
        await self.session.refresh(config)
        
        logger.info(f"Created default motivation config: {config.id}")
        return config
    
    async def get_all_configs(self, limit: Optional[int] = None, offset: int = 0) -> List[MotivationConfig]:
        """Get all motivation configurations."""
        return await self.motivation_config_repo.get_all(limit=limit, offset=offset)
    
    async def delete_config(self, config_id: uuid.UUID) -> bool:
        """Delete a motivation configuration."""
        return await self.motivation_config_repo.delete(config_id)
    
    # Utility and query methods
    
    async def get_topics_needing_research(
        self, 
        user_id: uuid.UUID, 
        threshold: float = 0.5,
        limit: Optional[int] = None
    ) -> List[TopicScore]:
        """Get topics that need research based on motivation score."""
        query = select(TopicScore).where(
            and_(
                TopicScore.user_id == user_id,
                TopicScore.is_active_research == True,
                TopicScore.motivation_score >= threshold
            )
        ).order_by(TopicScore.motivation_score.desc())
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_motivation_statistics(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get motivation statistics for a user."""
        # Get topic score statistics
        topic_stats = await self.session.execute(
            select(
                func.count(TopicScore.id).label('total_topics'),
                func.count(TopicScore.id).filter(TopicScore.is_active_research == True).label('active_topics'),
                func.avg(TopicScore.motivation_score).label('avg_motivation'),
                func.avg(TopicScore.engagement_score).label('avg_engagement'),
                func.avg(TopicScore.success_rate).label('avg_success_rate'),
                func.sum(TopicScore.total_findings).label('total_findings'),
                func.sum(TopicScore.read_findings).label('read_findings')
            ).where(TopicScore.user_id == user_id)
        )
        
        stats = topic_stats.first()
        
        return {
            'total_topics': stats.total_topics or 0,
            'active_topics': stats.active_topics or 0,
            'average_motivation_score': float(stats.avg_motivation or 0.0),
            'average_engagement_score': float(stats.avg_engagement or 0.0),
            'average_success_rate': float(stats.avg_success_rate or 0.0),
            'total_findings': stats.total_findings or 0,
            'read_findings': stats.read_findings or 0,
            'engagement_rate': (
                float(stats.read_findings or 0) / float(stats.total_findings or 1)
                if stats.total_findings and stats.total_findings > 0 else 0.0
            )
        }
    
    async def get_topics_by_engagement(
        self, 
        user_id: uuid.UUID, 
        min_engagement: float = 0.0,
        limit: Optional[int] = None
    ) -> List[TopicScore]:
        """Get topics by minimum engagement score."""
        query = select(TopicScore).where(
            and_(
                TopicScore.user_id == user_id,
                TopicScore.engagement_score >= min_engagement
            )
        ).order_by(TopicScore.engagement_score.desc())
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_topics_by_quality(
        self, 
        user_id: uuid.UUID, 
        min_quality: float = 0.0,
        limit: Optional[int] = None
    ) -> List[TopicScore]:
        """Get topics by minimum quality score."""
        query = select(TopicScore).where(
            and_(
                TopicScore.user_id == user_id,
                TopicScore.average_quality >= min_quality
            )
        ).order_by(TopicScore.average_quality.desc())
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_active_topics_count(self, user_id: uuid.UUID) -> int:
        """Get count of active research topics for a user."""
        result = await self.session.execute(
            select(func.count(TopicScore.id)).where(
                and_(
                    TopicScore.user_id == user_id,
                    TopicScore.is_active_research == True
                )
            )
        )
        return result.scalar() or 0
    
    async def get_user_topic_count(self, user_id: uuid.UUID) -> int:
        """Get total count of topics for a user."""
        result = await self.session.execute(
            select(func.count(TopicScore.id)).where(TopicScore.user_id == user_id)
        )
        return result.scalar() or 0


