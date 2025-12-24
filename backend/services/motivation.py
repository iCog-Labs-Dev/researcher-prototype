"""
Motivation System with database persistence and main research loop.
"""

import asyncio
import time
import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, func, select
import sqlalchemy as sa
from services.logging_config import get_logger
from database.motivation_repository import MotivationRepository
from storage.profile_manager import ProfileManager
from storage.research_manager import ResearchManager
from services.personalization_manager import PersonalizationManager
from services.topic_expansion_service import TopicExpansionService
from services.topic import TopicService
from services.research import ResearchService
from models.motivation import TopicScore
from models.research_finding import ResearchFinding
import config

logger = get_logger(__name__)


class MotivationSystem:
    """
    Motivation system with database persistence and integrated research loop.
    
    Features:
    - Database persistence for motivation state and topic scores
    - Integrated main research loop
    - Per-topic scoring with database updates
    - Engagement-based motivation tracking
    """

    def __init__(
        self, 
        session: AsyncSession,
        profile_manager: ProfileManager,
        research_manager: ResearchManager,
        personalization_manager: Optional[PersonalizationManager] = None
    ):
        """Initialize the enhanced motivation system."""
        self.session = session
        self.db_service = MotivationRepository(session)
        self.profile_manager = profile_manager
        self.research_manager = research_manager
        self.personalization_manager = personalization_manager
        
        # Research loop state
        self.is_running = False
        self.research_task = None
        self.check_interval = config.MOTIVATION_CHECK_INTERVAL
        
        # Research parameters
        self.quality_threshold = config.RESEARCH_QUALITY_THRESHOLD
        
        # Initialize topic expansion service
        try:
            from dependencies import zep_manager as _zep_manager_singleton
            self.topic_expansion_service = TopicExpansionService(_zep_manager_singleton, self.research_manager)
        except Exception:
            self.topic_expansion_service = TopicExpansionService(None, self.research_manager)
        
        # Concurrency control
        self._expansion_semaphore = asyncio.Semaphore(max(1, config.EXPANSION_MAX_PARALLEL))
        
        # Configuration
        self._config = None
        self.topic_service = TopicService()
        self.research_service = ResearchService()
        
        # Research graph decoupled; execution delegated to Research Engine
        
        logger.info("🎯 Motivation System initialized")

    async def initialize(self) -> None:
        """Initialize the motivation system with default configuration if needed."""
        try:
            # Get or create default configuration
            self._config = await self.db_service.get_default_config()
            if not self._config:
                logger.info("Creating default motivation configuration...")
                self._config = await self.db_service.create_default_config()
            
            logger.info(f"🎯 Motivation system initialized with config: {self._config.id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize motivation system: {str(e)}", exc_info=True)
            raise

    async def start(self) -> None:
        """Start the motivation-driven research loop."""
        if self.is_running:
            logger.warning("🎯 Motivation system is already running")
            return
        
        await self.initialize()
        
        self.is_running = True
        logger.info("🎯 Starting motivation-driven research loop...")
        
        # Start the main research loop
        self.research_task = asyncio.create_task(self._motivation_research_loop())

    async def stop(self) -> None:
        """Stop the motivation-driven research loop."""
        if not self.is_running:
            return
        
        logger.info("🎯 Stopping motivation-driven research loop...")
        self.is_running = False
        
        if self.research_task:
            self.research_task.cancel()
            try:
                await self.research_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🎯 Motivation-driven research loop stopped")

    async def _motivation_research_loop(self) -> None:
        """Main motivation-driven research loop."""
        while self.is_running:
            try:
                await asyncio.sleep(self.check_interval)
                
                if not self.is_running:
                    break
                
                # Update motivation scores for all topics
                await self.update_scores()

                logger.info("🎯 Starting research cycle")
                result = await self._conduct_research_cycle()

                # Check if research is needed
                research_needed = await self.check_for_research_needed()

                if research_needed:
                    logger.info("🎯 Research needed")

                    # Update motivation based on research results
                    topics_researched = result.get("topics_researched", 0)
                    if topics_researched > 0:
                        avg_quality = result.get("average_quality", 0.0)
                        await self._on_research_completed(avg_quality)
                        logger.info(f"🎯 Research cycle completed: {topics_researched} topics, quality: {avg_quality:.2f}")
                    else:
                        logger.info("🎯 Research cycle completed with no qualified topics")
                
            except asyncio.CancelledError:
                logger.info("🎯 Motivation research loop cancelled")
                break
            except Exception as e:
                logger.error(f"🎯 Error in motivation research loop: {str(e)}", exc_info=True)
                await asyncio.sleep(config.RESEARCH_CYCLE_SLEEP_INTERVAL)

    async def update_scores(self) -> None:
        """
        Update motivation scores for all active topics using optimized bulk query.
        
        This function:
        1. Updates all topic scores in a single database query
        2. Calculates motivation scores based on:
           - Staleness pressure (time since last research)
           - User engagement with research findings
           - Research success rate
        """
        try:
            if not self._config:
                return
            
            # Optimized: Single query to update all topic scores at once
            
            # Compute engagement and success via DB aggregates from research_findings
            now_epoch = func.extract('epoch', func.now())

            # Build a CTE that aggregates findings per user/topic
            findings_agg = (
                select(
                    ResearchFinding.user_id.label('user_id'),
                    ResearchFinding.topic_name.label('topic_name'),
                    func.avg(func.cast(ResearchFinding.read, sa.Integer)).label('engagement_reads'),
                    func.avg(ResearchFinding.quality_score).label('avg_quality'),
                    func.sum(func.cast(ResearchFinding.bookmarked, sa.Integer)).label('bookmarks'),
                    func.sum(func.cast(ResearchFinding.integrated, sa.Integer)).label('integrations'),
                    func.count().label('total'),
                )
                .group_by(ResearchFinding.user_id, ResearchFinding.topic_name)
                .cte('findings_agg')
            )

            # Derive engagement and success on the DB side using the CTE
            staleness = (now_epoch - func.coalesce(TopicScore.last_researched, 0.0))
            reads_pct = func.coalesce(findings_agg.c.engagement_reads, 0.0)
            volume_bonus = func.least(
                findings_agg.c.total * config.ENGAGEMENT_VOLUME_BONUS_RATE,
                config.ENGAGEMENT_VOLUME_BONUS_MAX,
            )
            bookmark_bonus = func.least(
                findings_agg.c.bookmarks * config.ENGAGEMENT_BOOKMARK_BONUS_RATE,
                config.ENGAGEMENT_BOOKMARK_BONUS_MAX,
            )
            integration_bonus = func.least(
                findings_agg.c.integrations * config.ENGAGEMENT_INTEGRATION_BONUS_RATE,
                config.ENGAGEMENT_INTEGRATION_BONUS_MAX,
            )
            engagement_expr = func.least(
                reads_pct + volume_bonus + bookmark_bonus + integration_bonus,
                config.ENGAGEMENT_SCORE_MAX,
            )
            success_expr = 0.3 + engagement_expr * 0.4

            result = await self.session.execute(
                update(TopicScore)
                .where(TopicScore.is_active_research == True)
                .values(
                    staleness_pressure=(staleness * TopicScore.staleness_coefficient * self._config.staleness_scale),
                    engagement_score=engagement_expr,
                    success_rate=func.coalesce(findings_agg.c.avg_quality, success_expr),
                    motivation_score=(
                        staleness * TopicScore.staleness_coefficient * self._config.staleness_scale +
                        engagement_expr * self._config.engagement_weight +
                        func.coalesce(findings_agg.c.avg_quality, success_expr) * self._config.quality_weight
                    ),
                )
                .where(TopicScore.user_id == findings_agg.c.user_id)
                .where(TopicScore.topic_name == findings_agg.c.topic_name)
            )
            
            updated_count = result.rowcount
            logger.debug(f"🎯 Updated motivation scores for {updated_count} topics")
            
        except Exception as e:
            try:
                await self.session.rollback()
            except Exception:
                pass
            logger.error(f"Error in update_scores: {str(e)}", exc_info=True)

    async def check_for_research_needed(self) -> bool:
        """
        Check if research is needed based on topic motivation scores.
        
        Returns:
            True if there are topics with motivation scores above threshold
        """
        try:
            if not self._config:
                return False
            
            _, active_topics = await self.topic_service.async_get_active_research_topics()
            if not active_topics:
                return False

            unique_users: set = set()
            for topic in active_topics:
                unique_users.add(topic.user_id)

            for user_uuid in unique_users:
                try:
                    topics_needing_research = await self.db_service.get_topics_needing_research(
                        user_uuid,
                        threshold=self._config.topic_threshold,
                        limit=1,
                    )

                    if topics_needing_research:
                        logger.debug(f"🎯 Found {len(topics_needing_research)} topics needing research for user {user_uuid}")
                        return True

                except Exception as e:
                    logger.error(f"Error checking research need for user {user_uuid}: {str(e)}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error in check_for_research_needed: {str(e)}", exc_info=True)
            return False

    async def _calculate_topic_motivation_score(
        self, 
        user_id: str, 
        topic: Dict[str, Any]
    ) -> float:
        """Calculate motivation score for a specific topic."""
        try:
            last_researched = topic.get('last_researched', 0)
            
            # NEW TOPICS GET PRIORITY: Never researched topics should be researched immediately
            if last_researched == 0:
                return 1.0  # Always above any reasonable threshold
            
            # For previously researched topics, calculate based on multiple factors
            now = time.time()
            staleness_time = now - last_researched
            staleness_coefficient = topic.get('staleness_coefficient', 1.0)
            staleness_pressure = staleness_time * staleness_coefficient * self._config.staleness_scale
            
            # Get engagement-based factors
            # Get topic_id from topic dict or look it up by name
            topic_id = None
            if topic.get('topic_id'):
                topic_id = uuid.UUID(topic.get('topic_id'))
            else:
                # Look up topic_id from topic_name
                user_uuid = uuid.UUID(user_id)
                _, active_topics = await self.topic_service.async_get_active_research_topics(user_id=user_uuid)
                topic_obj = next((t for t in active_topics if t.name == topic.get('topic_name', '')), None)
                if topic_obj:
                    topic_id = topic_obj.id
            
            if not topic_id:
                engagement_score = 0.0
                success_rate = 0.5
            else:
                engagement_score = await self._get_topic_engagement_score(user_id, topic_id)
                success_rate = await self._get_topic_success_rate(user_id, topic_id)
            
            # Calculate final motivation score
            motivation_score = (
                staleness_pressure + 
                engagement_score * self._config.engagement_weight +
                success_rate * self._config.quality_weight
            )
            
            return motivation_score
            
        except Exception as e:
            logger.error(f"Error calculating motivation score for topic {topic.get('topic_name')}: {str(e)}")
            return 0.0

    async def _get_topic_engagement_score(self, user_id: str, topic_id: uuid.UUID) -> float:
        """Get engagement score for a topic based on research findings interactions."""
        try:
            # Get all findings for this user and topic from DB
            success, all_findings = await self.research_service.async_get_findings(user_id, str(topic_id))
            if not success or not all_findings:
                return 0.0
            
            total_findings = len(all_findings)
            read_findings = sum(1 for f in all_findings if f.read)
            bookmarked_findings = sum(1 for f in all_findings if f.bookmarked)
            integrated_findings = sum(1 for f in all_findings if f.integrated)
            
            # Base engagement: percentage of findings read
            read_percentage = read_findings / total_findings if total_findings > 0 else 0.0
            
            # Bonus for recent reads (findings read in last 7 days get extra weight)
            recent_threshold = time.time() - (7 * 24 * 3600)  # 7 days ago
            recent_reads = sum(1 for f in all_findings 
                             if f.read and 
                             f.created_at and f.created_at.timestamp() > recent_threshold)
            
            recent_bonus = min(recent_reads * config.ENGAGEMENT_RECENT_BONUS_RATE, config.ENGAGEMENT_RECENT_BONUS_MAX)
            
            # Total findings bonus (more findings = more research value demonstrated)
            volume_bonus = min(total_findings * config.ENGAGEMENT_VOLUME_BONUS_RATE, config.ENGAGEMENT_VOLUME_BONUS_MAX)
            
            # Bookmarks indicate strong interest in a topic
            bookmark_bonus = min(bookmarked_findings * config.ENGAGEMENT_BOOKMARK_BONUS_RATE, config.ENGAGEMENT_BOOKMARK_BONUS_MAX)
            # Integrations are a strong signal of value
            integration_bonus = min(integrated_findings * config.ENGAGEMENT_INTEGRATION_BONUS_RATE, config.ENGAGEMENT_INTEGRATION_BONUS_MAX)

            total_score = read_percentage + recent_bonus + volume_bonus + bookmark_bonus + integration_bonus
            
            return min(total_score, config.ENGAGEMENT_SCORE_MAX)
            
        except Exception as e:
            logger.debug(f"Error calculating engagement score for topic {topic_id}: {str(e)}")
            return 0.0

    async def _get_topic_success_rate(self, user_id: str, topic_id: uuid.UUID) -> float:
        """Calculate research success rate from user engagement patterns."""
        try:
            if not self.personalization_manager:
                return 0.5  # Default neutral success rate
            
            # Use engagement as proxy for success rate
            engagement_score = await self._get_topic_engagement_score(user_id, topic_id)
            success_rate = 0.3 + (engagement_score * 0.4)  # Range: 0.3-0.7
            
            return success_rate
            
        except Exception as e:
            logger.debug(f"Error getting success rate for topic {topic_id}: {str(e)}")
            return 0.5

    async def _conduct_research_cycle(self) -> Dict[str, Any]:
        """Conduct a complete research cycle for all users with motivated topics."""

        # need attention:
        # result of get_topics_needing_research is empty
        # need only analyze async_get_active_research_topics
        # and only run run_langgraph_research
        """
        try:
            _, active_topics = await self.topic_service.async_get_active_research_topics()
            if not active_topics:
                logger.info("🎯 No active research topics found in database")
                return {
                    "topics_researched": 0,
                    "findings_stored": 0,
                    "average_quality": 0.0,
                }

            # Build lookup map: (user_id, topic_name) -> ResearchTopic
            topic_lookup: Dict[tuple, Any] = {}
            unique_users: set = set()
            for topic in active_topics:
                topic_lookup[(topic.user_id, topic.name)] = topic
                unique_users.add(topic.user_id)

            logger.info(f"🎯 Processing {len(active_topics)} active topics across {len(unique_users)} users...")
            
            total_topics_researched = 0
            total_findings_stored = 0
            quality_scores: List[float] = []
            
            for user_uuid in unique_users:
                user_id = str(user_uuid)
                try:
                    topics_needing_research = await self.db_service.get_topics_needing_research(
                        user_uuid,
                        threshold=self._config.topic_threshold,
                        limit=None,  # No limit - already limited by MAX_ACTIVE_RESEARCH_TOPICS_PER_USER
                    )

                    if not topics_needing_research:
                        continue

                    logger.info(f"🎯 User {user_id} has {len(topics_needing_research)} motivated topics")
                    
                    for topic_score in topics_needing_research:
                        try:
                            topic_name = topic_score.topic_name
                            research_topic = topic_lookup.get((user_uuid, topic_name))
                            if not research_topic:
                                logger.debug(f"Topic '{topic_name}' missing from active topics lookup; skipping")
                                continue
                            logger.info(f"🎯 Researching motivated topic: {topic_name} for user {user_id}")

                            topic_data = {
                                "topic_id": str(research_topic.id),
                                "topic_name": research_topic.name,
                                "description": research_topic.description,
                                "last_researched": research_topic.last_researched.astimezone(timezone.utc).strftime("%Y-%m-%d") if research_topic.last_researched else None,
                                "is_active_research": research_topic.is_active_research,
                            }
                            
                            # Research the topic via research engine instance
                            from services.autonomous_research_engine import get_autonomous_researcher
                            researcher = get_autonomous_researcher()
                            if not researcher:
                                logger.warning("Autonomous researcher not initialized; skipping research")
                                continue
                            result = await researcher.run_langgraph_research(user_id, topic_data)
                            
                            total_topics_researched += 1
                            if result and result.get("stored", False):
                                total_findings_stored += 1
                            if result and result.get("quality_score"):
                                quality_scores.append(result.get("quality_score"))
                            
                            # Update last_researched timestamp
                            await self.db_service.create_or_update_topic_score(
                                user_id=user_uuid,
                                topic_id=research_topic.id,
                                topic_name=topic_name,
                                last_researched=time.time()
                            )

                            # --- Topic expansion wiring ---
                            try:
                                from services.autonomous_research_engine import get_autonomous_researcher
                                researcher = get_autonomous_researcher()
                                if not researcher:
                                    logger.warning("Autonomous researcher not initialized; skipping expansions")
                                    child_runs = []
                                else:
                                    child_runs = await researcher.process_expansions_for_root(user_id, topic_data)
                                if child_runs:
                                    for cr in child_runs:
                                        child = cr.get("topic", {})
                                        child_res = cr.get("result", {})
                                        child_name = child.get('topic_name')
                                        if not child_name:
                                            continue
                                        logger.info(f"🎯 Researched expansion topic: {child_name} for user {user_id}")
                                        total_topics_researched += 1
                                        if child_res and child_res.get("stored", False):
                                            total_findings_stored += 1
                                        if child_res and child_res.get("quality_score"):
                                            quality_scores.append(child_res.get("quality_score"))

                                        # Update last_researched for child
                                        child_topic_id = child.get("topic_id")
                                        if child_topic_id:
                                            await self.db_service.create_or_update_topic_score(
                                                user_id=user_uuid,
                                                topic_id=uuid.UUID(str(child_topic_id)),
                                                topic_name=child_name,
                                                last_researched=time.time()
                                            )

                            except Exception as ex:
                                logger.debug(f"Expansion wiring failed for {topic_name}: {ex}")
                            
                            # Small delay between topics
                            await asyncio.sleep(config.RESEARCH_TOPIC_DELAY)
                            
                        except Exception as e:
                            logger.error(f"🎯 Error researching topic {topic_name}: {str(e)}")
                            continue
                    
                
                except Exception as e:
                    logger.error(f"🎯 Error processing user {user_id}: {str(e)}")
                    continue
            
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            
            logger.info(f"🎯 Research cycle completed: {total_topics_researched} topics, {total_findings_stored} findings, avg quality: {avg_quality:.2f}")
            
            # Cleanup old findings globally (once for all users)
            try:
                await self.research_service.async_cleanup_old_research_findings(config.RESEARCH_FINDINGS_RETENTION_DAYS)
            except Exception as cleanup_error:
                logger.debug(f"Error cleaning up old findings: {cleanup_error}")
            
            # Update expansion lifecycle for all processed users
            try:
                for user_uuid in unique_users:
                    await self._update_expansion_lifecycle(str(user_uuid))
            except Exception as e:
                logger.error(f"Lifecycle update failed: {str(e)}")
            
            return {
                "topics_researched": total_topics_researched,
                "findings_stored": total_findings_stored,
                "average_quality": avg_quality,
            }
            
        except Exception as e:
            logger.error(f"🎯 Error in research cycle: {str(e)}", exc_info=True)
            return {
                "topics_researched": 0,
                "findings_stored": 0,
                "average_quality": 0.0,
            }
        """

        from services.autonomous_research_engine import get_autonomous_researcher
        researcher = get_autonomous_researcher()

        try:
            _, active_topics = await self.topic_service.async_get_active_research_topics()
            if not active_topics or not researcher:
                if not active_topics:
                    logger.info("🔬 No active research topics found")
                if not researcher:
                    logger.warning("Autonomous researcher not initialized; skipping research")

                return {
                    "topics_researched": 0,
                    "findings_stored": 0,
                    "average_quality": 0.0,
                }

            logger.info(f"🔬 Processing {len(active_topics)} active research topics...")

            total_topics_researched = 0
            total_findings_stored = 0
            quality_scores: List[float] = []
            processed_users: set = set()

            for topic in active_topics:
                try:
                    user_id = str(topic.user_id)
                    processed_users.add(user_id)
                    root_name = topic.name
                    logger.info(f"🔬 Researching topic: {root_name} for user {user_id}")

                    topic_payload = {
                        "topic_id": str(topic.id),
                        "topic_name": topic.name,
                        "description": topic.description,
                        "last_researched": topic.last_researched.astimezone(timezone.utc).strftime("%Y-%m-%d") if topic.last_researched else None,
                        "is_active_research": topic.is_active_research,
                    }

                    result = await researcher.run_langgraph_research(user_id, topic_payload)

                    if result:
                        total_topics_researched += 1
                        if result.get("stored", False):
                            total_findings_stored += 1
                        if result.get("quality_score"):
                            quality_scores.append(result.get("quality_score"))

                    await asyncio.sleep(config.RESEARCH_TOPIC_DELAY)

                except Exception as e:
                    logger.error(
                        f"🔬 Error researching topic {topic.name} for user {topic.user_id}: {str(e)}"
                    )
                    continue

            logger.info(
                f"🔬 LangGraph research cycle completed: {total_topics_researched} topics researched, {total_findings_stored} findings stored"
            )

            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

            try:
                await self.research_service.async_cleanup_old_research_findings(config.RESEARCH_FINDINGS_RETENTION_DAYS)
            except Exception as cleanup_error:
                logger.debug(f"Error cleaning up old findings: {cleanup_error}")

            try:
                for user_id in processed_users:
                    await self._update_expansion_lifecycle(user_id)
            except Exception as e:
                logger.error(f"Lifecycle update failed: {str(e)}")

            return {
                "topics_researched": total_topics_researched,
                "findings_stored": total_findings_stored,
                "average_quality": avg_quality,
            }

        except Exception as e:
            logger.error(f"🔬 Error in research cycle: {str(e)}", exc_info=True)
            return {
                "topics_researched": 0,
                "findings_stored": 0,
                "average_quality": 0.0,
            }

    async def get_recent_average_quality(self, user_id: str, topic_id: uuid.UUID, window_days: int) -> float:
        """Compute recent average quality over window for a topic."""
        try:
            now = time.time()
            window_start = now - (window_days * 24 * 3600)
            success, findings = await self.research_service.async_get_findings(user_id, str(topic_id))
            if not success:
                return 0.0
            scores = [f.quality_score for f in findings if f.created_at and f.created_at.timestamp() >= window_start and isinstance(f.quality_score, (int, float))]
            if not scores:
                return 0.0
            return sum(scores) / len(scores)
        except Exception:
            return 0.0

    async def _update_expansion_lifecycle(self, user_id: str) -> None:
        """Evaluate and update lifecycle state for expansion topics for a user."""
        try:
            topics_data = self.research_manager.get_user_topics(user_id)
            if not topics_data:
                return
            now_ts = time.time()
            promoted = paused = retired = 0
            changed = False
            window_days = config.EXPANSION_ENGAGEMENT_WINDOW_DAYS
            promote_thr = config.EXPANSION_PROMOTE_ENGAGEMENT
            retire_thr = config.EXPANSION_RETIRE_ENGAGEMENT
            min_quality = config.EXPANSION_MIN_QUALITY
            backoff_days = config.EXPANSION_BACKOFF_DAYS
            retire_ttl_days = config.EXPANSION_RETIRE_TTL_DAYS

            # Fetch active topics from database once per user
            user_uuid = uuid.UUID(user_id)
            _, active_topics = await self.topic_service.async_get_active_research_topics(user_id=user_uuid)
            # Create a lookup map by topic name
            topics_by_name = {t.name: t for t in active_topics}

            for sid, session_topics in topics_data.get('sessions', {}).items():
                for topic in session_topics:
                    if not topic.get('is_expansion', False):
                        continue
                    name = topic.get('topic_name')
                    depth = int(topic.get('expansion_depth', 0) or 0)
                    
                    # Look up topic from database
                    topic_obj = topics_by_name.get(name)
                    
                    engagement = 0.0
                    try:
                        if topic_obj:
                            engagement = await self._get_topic_engagement_score(user_id, topic_obj.id)
                    except Exception:
                        engagement = 0.0
                    avg_quality = await self.get_recent_average_quality(user_id, topic_obj.id, window_days) if topic_obj else 0.0

                    status = topic.get('expansion_status', 'active')
                    last_eval = float(topic.get('last_evaluated_at', 0) or 0)
                    backoff_until = float(topic.get('last_backoff_until', 0) or 0)

                    decision_debug = f"topic='{name}' depth={depth} engagement={engagement:.2f} avg_q={avg_quality:.2f} status={status}"

                    # Promote to allow children
                    if engagement >= promote_thr and avg_quality >= min_quality:
                        if not topic.get('child_expansion_enabled', False) or status != 'active':
                            topic['child_expansion_enabled'] = True
                            topic['expansion_status'] = 'active'
                            changed = True
                            promoted += 1
                            logger.debug(f"Lifecycle promote: {decision_debug}")
                        topic['last_evaluated_at'] = now_ts
                        continue

                    # Assess interactions in window via findings read/bookmark/integration
                    any_interaction = False
                    try:
                        if topic_obj:
                            success, findings = await self.research_service.async_get_findings(user_id, str(topic_obj.id))
                            if success:
                                window_start = now_ts - window_days * 24 * 3600
                                any_interaction = any(
                                    (f.read or f.bookmarked or f.integrated) and f.created_at and f.created_at.timestamp() >= window_start
                                    for f in findings
                                )
                    except Exception:
                        any_interaction = False

                    # Retire after TTL if still cold (check before pausing again)
                    if status == 'paused' and last_eval and (now_ts - last_eval) >= retire_ttl_days * 24 * 3600:
                        if engagement < retire_thr and not any_interaction:
                            topic['expansion_status'] = 'retired'
                            topic['last_evaluated_at'] = now_ts
                            changed = True
                            retired += 1
                            logger.debug(f"Lifecycle retire: {decision_debug}")
                            continue

                    # Pause on cold engagement and no interactions in window
                    if engagement < retire_thr and not any_interaction:
                        topic['is_active_research'] = False
                        topic['child_expansion_enabled'] = False
                        topic['expansion_status'] = 'paused'
                        topic['last_backoff_until'] = now_ts + backoff_days * 24 * 3600
                        topic['last_evaluated_at'] = now_ts
                        changed = True
                        paused += 1
                        logger.debug(f"Lifecycle pause: {decision_debug}")
                        continue

                    # No action
                    topic['last_evaluated_at'] = now_ts

            if changed:
                self.research_manager.save_user_topics(user_id, topics_data)
            logger.info(f"Lifecycle update for {user_id}: promoted={promoted}, paused={paused}, retired={retired}")

        except Exception as e:
            logger.error(f"Error updating expansion lifecycle for user {user_id}: {str(e)}")

    # NOTE: Research execution lives in Research Engine now

    async def _on_research_completed(self, quality_score: float) -> None:
        """Handle completion of research cycle."""
        try:
            # Update topic engagement metrics based on research quality
            # This could be expanded to update success rates, etc.
            logger.debug(f"🎯 Research completed with quality score: {quality_score:.2f}")
            
            # Future: Could update global motivation state based on research success
            # For now, we rely on per-topic scoring
            
        except Exception as e:
            logger.error(f"Error in _on_research_completed: {str(e)}")

    async def get_motivation_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get motivation statistics for a user."""
        try:
            user_uuid = uuid.UUID(user_id)
            return await self.db_service.get_motivation_statistics(user_uuid)
            
        except Exception as e:
            logger.error(f"Error getting motivation statistics for {user_id}: {str(e)}")
            return {}

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the motivation system."""
        return {
            "running": self.is_running,
            "check_interval": self.check_interval,
            "quality_threshold": self.quality_threshold,
            "system_type": "MotivationSystem",
            "features": [
                "database_persistence",
                "per_topic_scoring",
                "integrated_research_loop",
                "engagement_based_motivation"
            ]
        }


