"""
API endpoints for testing the database-backed motivation system.
"""

import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database.motivation_repository import MotivationRepository
from database.database_manager import DatabaseManager
from models.motivation import TopicScore, MotivationConfig
from services.logging_config import get_logger
from db import get_session

logger = get_logger(__name__)
router = APIRouter()


async def get_motivation_repository(session: AsyncSession = Depends(get_session)) -> MotivationRepository:
    """Dependency to get motivation repository."""
    return MotivationRepository(session)


async def get_database_manager(session: AsyncSession = Depends(get_session)) -> DatabaseManager:
    """Dependency to get database manager."""
    return DatabaseManager(session)


# TopicScore endpoints

@router.get("/motivation/topic-scores/{user_id}")
async def get_user_topic_scores(
    user_id: str,
    active_only: bool = False,
    limit: Optional[int] = None,
    order_by_motivation: bool = True,
    repo: MotivationRepository = Depends(get_motivation_repository)
):
    """Get topic scores for a user."""
    try:
        user_uuid = uuid.UUID(user_id)
        scores = await repo.get_user_topic_scores(
            user_uuid,
            active_only=active_only,
            limit=limit,
            order_by_motivation=order_by_motivation
        )
        
        return [
            {
                "id": str(score.id),
                "user_id": str(score.user_id),
                "topic_name": score.topic_name,
                "motivation_score": score.motivation_score,
                "engagement_score": score.engagement_score,
                "success_rate": score.success_rate,
                "staleness_pressure": score.staleness_pressure,
                "last_researched": score.last_researched,
                "staleness_coefficient": score.staleness_coefficient,
                "is_active_research": score.is_active_research,
                "total_findings": score.total_findings,
                "read_findings": score.read_findings,
                "bookmarked_findings": score.bookmarked_findings,
                "integrated_findings": score.integrated_findings,
                "average_quality": score.average_quality,
                "last_quality_update": score.last_quality_update,
                "meta_data": score.meta_data
            }
            for score in scores
        ]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except Exception as e:
        logger.error(f"Error getting topic scores: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting topic scores: {str(e)}")


@router.get("/motivation/topic-scores/{user_id}/{topic_name}")
async def get_topic_score(
    user_id: str,
    topic_name: str,
    repo: MotivationRepository = Depends(get_motivation_repository)
):
    """Get specific topic score."""
    try:
        user_uuid = uuid.UUID(user_id)
        score = await repo.get_topic_score(user_uuid, topic_name)
        
        if not score:
            raise HTTPException(status_code=404, detail="Topic score not found")
        
        return {
            "id": str(score.id),
            "user_id": str(score.user_id),
            "topic_name": score.topic_name,
            "motivation_score": score.motivation_score,
            "engagement_score": score.engagement_score,
            "success_rate": score.success_rate,
            "staleness_pressure": score.staleness_pressure,
            "last_researched": score.last_researched,
            "staleness_coefficient": score.staleness_coefficient,
            "is_active_research": score.is_active_research,
            "total_findings": score.total_findings,
            "read_findings": score.read_findings,
            "bookmarked_findings": score.bookmarked_findings,
            "integrated_findings": score.integrated_findings,
            "average_quality": score.average_quality,
            "last_quality_update": score.last_quality_update,
            "meta_data": score.meta_data
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except Exception as e:
        logger.error(f"Error getting topic score: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting topic score: {str(e)}")


@router.post("/motivation/topic-scores")
async def create_or_update_topic_score(
    request: Request,
    repo: MotivationRepository = Depends(get_motivation_repository)
):
    """Create or update topic score."""
    try:
        body = await request.json()
        user_uuid = uuid.UUID(body["user_id"])
        score = await repo.create_or_update_topic_score(
            user_id=user_uuid,
            topic_name=body["topic_name"],
            motivation_score=body.get("motivation_score"),
            engagement_score=body.get("engagement_score"),
            success_rate=body.get("success_rate"),
            staleness_pressure=body.get("staleness_pressure"),
            last_researched=body.get("last_researched"),
            staleness_coefficient=body.get("staleness_coefficient"),
            is_active_research=body.get("is_active_research"),
            total_findings=body.get("total_findings"),
            read_findings=body.get("read_findings"),
            bookmarked_findings=body.get("bookmarked_findings"),
            integrated_findings=body.get("integrated_findings"),
            average_quality=body.get("average_quality"),
            last_quality_update=body.get("last_quality_update"),
            meta_data=body.get("meta_data")
        )
        
        return {
            "id": str(score.id),
            "user_id": str(score.user_id),
            "topic_name": score.topic_name,
            "motivation_score": score.motivation_score,
            "engagement_score": score.engagement_score,
            "success_rate": score.success_rate,
            "staleness_pressure": score.staleness_pressure,
            "last_researched": score.last_researched,
            "staleness_coefficient": score.staleness_coefficient,
            "is_active_research": score.is_active_research,
            "total_findings": score.total_findings,
            "read_findings": score.read_findings,
            "bookmarked_findings": score.bookmarked_findings,
            "integrated_findings": score.integrated_findings,
            "average_quality": score.average_quality,
            "last_quality_update": score.last_quality_update,
            "meta_data": score.meta_data
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except Exception as e:
        logger.error(f"Error creating/updating topic score: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating/updating topic score: {str(e)}")


# Statistics and analytics endpoints

@router.get("/motivation/statistics/{user_id}")
async def get_motivation_statistics(
    user_id: str,
    repo: MotivationRepository = Depends(get_motivation_repository)
):
    """Get motivation statistics for a user."""
    try:
        user_uuid = uuid.UUID(user_id)
        stats = await repo.get_motivation_statistics(user_uuid)
        return stats
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except Exception as e:
        logger.error(f"Error getting motivation statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting motivation statistics: {str(e)}")


@router.get("/motivation/topics-needing-research/{user_id}")
async def get_topics_needing_research(
    user_id: str,
    threshold: float = 0.5,
    limit: Optional[int] = None,
    repo: MotivationRepository = Depends(get_motivation_repository)
):
    """Get topics that need research based on motivation scores."""
    try:
        user_uuid = uuid.UUID(user_id)
        topics = await repo.get_topics_needing_research(
            user_uuid,
            threshold=threshold,
            limit=limit
        )
        
        return [
            {
                "id": str(topic.id),
                "user_id": str(topic.user_id),
                "topic_name": topic.topic_name,
                "motivation_score": topic.motivation_score,
                "engagement_score": topic.engagement_score,
                "success_rate": topic.success_rate,
                "staleness_pressure": topic.staleness_pressure,
                "last_researched": topic.last_researched,
                "is_active_research": topic.is_active_research
            }
            for topic in topics
        ]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except Exception as e:
        logger.error(f"Error getting topics needing research: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting topics needing research: {str(e)}")


# MotivationConfig endpoints

@router.get("/motivation/config")
async def get_default_config(
    repo: MotivationRepository = Depends(get_motivation_repository)
):
    """Get default motivation configuration."""
    try:
        config = await repo.get_default_config()
        
        if not config:
            raise HTTPException(status_code=404, detail="Default configuration not found")
        
        return {
            "id": str(config.id),
            "boredom_rate": config.boredom_rate,
            "curiosity_decay": config.curiosity_decay,
            "tiredness_decay": config.tiredness_decay,
            "satisfaction_decay": config.satisfaction_decay,
            "global_threshold": config.global_threshold,
            "topic_threshold": config.topic_threshold,
            "engagement_weight": config.engagement_weight,
            "quality_weight": config.quality_weight,
            "staleness_scale": config.staleness_scale,
            "check_interval": config.check_interval,
            "is_default": config.is_default,
            "description": config.description,
            "config_data": config.config_data
        }
    except Exception as e:
        logger.error(f"Error getting default config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting default config: {str(e)}")


@router.post("/motivation/config")
async def create_default_config(
    request: Request,
    repo: MotivationRepository = Depends(get_motivation_repository)
):
    """Create default motivation configuration."""
    try:
        body = await request.json()
        config = await repo.create_default_config(
            boredom_rate=body.get("boredom_rate", 0.0002),
            curiosity_decay=body.get("curiosity_decay", 0.0002),
            tiredness_decay=body.get("tiredness_decay", 0.0002),
            satisfaction_decay=body.get("satisfaction_decay", 0.0002),
            global_threshold=body.get("global_threshold", 2.0),
            topic_threshold=body.get("topic_threshold", 0.5),
            engagement_weight=body.get("engagement_weight", 0.3),
            quality_weight=body.get("quality_weight", 0.2),
            staleness_scale=body.get("staleness_scale", 0.0001),
            check_interval=body.get("check_interval", 60),
            description=body.get("description"),
            config_data=body.get("config_data")
        )
        
        return {
            "id": str(config.id),
            "boredom_rate": config.boredom_rate,
            "curiosity_decay": config.curiosity_decay,
            "tiredness_decay": config.tiredness_decay,
            "satisfaction_decay": config.satisfaction_decay,
            "global_threshold": config.global_threshold,
            "topic_threshold": config.topic_threshold,
            "engagement_weight": config.engagement_weight,
            "quality_weight": config.quality_weight,
            "staleness_scale": config.staleness_scale,
            "check_interval": config.check_interval,
            "is_default": config.is_default,
            "description": config.description,
            "config_data": config.config_data
        }
    except Exception as e:
        logger.error(f"Error creating default config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating default config: {str(e)}")
