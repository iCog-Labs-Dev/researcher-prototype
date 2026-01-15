"""
Motivation System with database persistence and main research loop.
"""

import asyncio
import time
import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, func, select, and_, distinct
import sqlalchemy as sa
from db import SessionLocal
from services.logging_config import get_logger
from database.motivation_repository import MotivationRepository
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
    ):
        """Initialize the enhanced motivation system."""
        self.session = session
        self.db_service = MotivationRepository(session)
        
        # Research loop state
        self.is_running = False
        self.research_task = None
        self.check_interval = config.MOTIVATION_CHECK_INTERVAL
        
        # Research parameters
        self.max_topics_per_user = config.RESEARCH_MAX_TOPICS_PER_USER
        self.quality_threshold = config.RESEARCH_QUALITY_THRESHOLD
        
        # Initialize topic expansion service
        try:
            from dependencies import zep_manager as _zep_manager_singleton
            self.topic_expansion_service = TopicExpansionService(_zep_manager_singleton, None)
        except Exception:
            self.topic_expansion_service = TopicExpansionService(None, None)
        
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
            
            logger.debug(f"🎯 Starting score update with config: threshold={self._config.topic_threshold}, engagement_weight={self._config.engagement_weight}, quality_weight={self._config.quality_weight}, staleness_scale={self._config.staleness_scale}")
            
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

            await self.session.commit()  # Ensure changes are saved
            
            updated_count = result.rowcount
            logger.debug(f"🎯 Updated motivation scores for {updated_count} topics")
            
            # Log detailed scores for each topic after update
            await self._log_topic_scores_detail()
            
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
                logger.debug("🎯 No active research topics found")
                return False

            unique_users: set = set()
            for topic in active_topics:
                unique_users.add(topic.user_id)
            
            logger.debug(f"🎯 Checking research needs for {len(unique_users)} users with threshold={self._config.topic_threshold}")

            for user_uuid in unique_users:
                try:
                    topics_needing_research = await self.db_service.get_topics_needing_research(
                        user_uuid,
                        threshold=self._config.topic_threshold,
                        limit=1,
                    )

                    if topics_needing_research:
                        logger.debug(f"🎯 Found {len(topics_needing_research)} topics needing research for user {user_uuid}")
                        for topic in topics_needing_research:
                            logger.debug(f"🎯   - Topic '{topic.topic_name}': motivation={topic.motivation_score:.4f} (threshold={self._config.topic_threshold})")
                        return True

                except Exception as e:
                    logger.error(f"Error checking research need for user {user_uuid}: {str(e)}")
                    continue
            
            logger.debug("🎯 No topics currently need research")
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
            topic_name = topic.get('topic_name', 'unknown')
            last_researched = topic.get('last_researched', 0)
            
            # NEW TOPICS GET PRIORITY: Never researched topics should be researched immediately
            if last_researched == 0:
                logger.debug(f"🎯 Topic '{topic_name}': NEVER RESEARCHED - returning score=1.0 (auto-research)")
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
            
            logger.debug(
                f"🎯 Topic '{topic_name}' motivation calculation:\n"
                f"   - Staleness: {staleness_time:.0f}s * {staleness_coefficient} * {self._config.staleness_scale} = {staleness_pressure:.4f}\n"
                f"   - Engagement: {engagement_score:.4f} * {self._config.engagement_weight} = {engagement_score * self._config.engagement_weight:.4f}\n"
                f"   - Success: {success_rate:.4f} * {self._config.quality_weight} = {success_rate * self._config.quality_weight:.4f}\n"
                f"   - TOTAL MOTIVATION: {motivation_score:.4f}"
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
                logger.debug(f"🎯 Topic {topic_id}: No findings found, engagement=0.0")
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
            final_score = min(total_score, config.ENGAGEMENT_SCORE_MAX)
            
            logger.debug(
                f"🎯 Topic {topic_id} engagement breakdown:\n"
                f"   - Findings: {total_findings} total, {read_findings} read ({read_percentage:.2%})\n"
                f"   - Recent reads (7d): {recent_reads} → bonus={recent_bonus:.4f}\n"
                f"   - Volume bonus: {total_findings} * {config.ENGAGEMENT_VOLUME_BONUS_RATE} = {volume_bonus:.4f}\n"
                f"   - Bookmarks: {bookmarked_findings} → bonus={bookmark_bonus:.4f}\n"
                f"   - Integrations: {integrated_findings} → bonus={integration_bonus:.4f}\n"
                f"   - TOTAL ENGAGEMENT: {final_score:.4f} (capped at {config.ENGAGEMENT_SCORE_MAX})"
            )
            
            return final_score
            
        except Exception as e:
            logger.debug(f"Error calculating engagement score for topic {topic_id}: {str(e)}")
            return 0.0

    async def _get_topic_success_rate(self, user_id: str, topic_id: uuid.UUID) -> float:
        """Calculate research success rate from user engagement patterns."""
        try:
            # Use engagement as proxy for success rate (database-backed)
            engagement_score = await self._get_topic_engagement_score(user_id, topic_id)
            success_rate = 0.3 + (engagement_score * 0.4)  # Range: 0.3-0.7
            
            return success_rate
            
        except Exception as e:
            logger.debug(f"Error getting success rate for topic {topic_id}: {str(e)}")
            return 0.5

    async def _conduct_research_cycle(self) -> Dict[str, Any]:
        """Conduct a complete research cycle for all users with motivated topics."""
        try:
            # Get all unique users from TopicScore table
            user_ids_result = await self.session.execute(
                select(distinct(TopicScore.user_id)).where(TopicScore.is_active_research == True)
            )
            user_ids = [row[0] for row in user_ids_result.all()]
            
            if not user_ids:
                logger.info("🎯 No users with active research topics found")
                return {
                    "topics_researched": 0,
                    "findings_stored": 0,
                    "average_quality": 0.0,
                }
            
            logger.info(f"🎯 Scanning {len(user_ids)} users for motivated research topics...")
            
            # Get researcher instance once before the loop
            from services.autonomous_research_engine import get_autonomous_researcher
            researcher = get_autonomous_researcher()
            if not researcher:
                logger.warning("Autonomous researcher not initialized; skipping research cycle")
                return {
                    "topics_researched": 0,
                    "findings_stored": 0,
                    "average_quality": 0.0,
                }
            
            total_topics_researched = 0
            total_findings_stored = 0
            quality_scores: List[float] = []
            
            for user_uuid in user_ids:
                try:
                    user_id = str(user_uuid)
                    
                    # Get topics needing research based on motivation scores
                    topics_needing_research = await self.db_service.get_topics_needing_research(
                        user_uuid,
                        threshold=self._config.topic_threshold,
                        limit=self.max_topics_per_user
                    )
                    
                    if not topics_needing_research:
                        logger.debug(f"🎯 User {user_id}: No topics above threshold ({self._config.topic_threshold})")
                        continue
                    
                    logger.info(f"🎯 User {user_id} has {len(topics_needing_research)} motivated topics")
                    for ts in topics_needing_research:
                        logger.info(f"🎯   → '{ts.topic_name}': motivation={ts.motivation_score:.4f}, staleness={ts.staleness_pressure:.4f}, engagement={ts.engagement_score:.4f}, success={ts.success_rate:.4f}, last_researched={ts.last_researched}")
                    
                    # Fetch all active topics for this user once before the loop
                    topics = await self.topic_service.get_active_research_topics_by_user_id(
                        self.session,
                        user_uuid
                    )
                    # Build lookup map: topic_name -> ResearchTopic
                    topic_lookup = {t.name: t for t in topics}
                    
                    for topic_score in topics_needing_research:
                        try:
                            topic_name = topic_score.topic_name
                            
                            logger.debug(f"🎯 Processing topic '{topic_name}' with motivation={topic_score.motivation_score:.4f}")
                            
                            # Get full topic data from lookup map
                            topic = topic_lookup.get(topic_name)
                            if not topic:
                                logger.debug(f"Topic '{topic_name}' missing from active topics lookup; skipping")
                                continue
                            
                            # Re-check if topic is still active (user may have deactivated it during research cycle)
                            async with SessionLocal() as check_session:
                                from models.topic import ResearchTopic
                                check_query = select(ResearchTopic).where(
                                    and_(
                                        ResearchTopic.id == topic.id,
                                        ResearchTopic.user_id == user_uuid,
                                        ResearchTopic.is_active_research.is_(True)
                                    )
                                )
                                check_result = await check_session.execute(check_query)
                                active_topic = check_result.scalar_one_or_none()
                                
                                if not active_topic:
                                    logger.info(f"🎯 Topic '{topic_name}' was deactivated during research cycle; skipping")
                                    continue
                                
                                # Update topic with fresh data
                                topic = active_topic
                            
                            # Log current state before research
                            last_researched_str = topic.last_researched.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if topic.last_researched else "NEVER"
                            logger.info(f"🎯 STARTING RESEARCH for '{topic_name}' (user={user_id})")
                            logger.info(f"🎯   - Last researched: {last_researched_str}")
                            logger.info(f"🎯   - Current motivation: {topic_score.motivation_score:.4f}")
                            logger.info(f"🎯   - Staleness pressure: {topic_score.staleness_pressure:.4f}")
                            logger.info(f"🎯   - Engagement score: {topic_score.engagement_score:.4f}")
                            logger.info(f"🎯   - Success rate: {topic_score.success_rate:.4f}")
                            
                            topic_data = {
                                "topic_id": str(topic.id),
                                "topic_name": topic.name,
                                "description": topic.description,
                                "last_researched": topic.last_researched.astimezone(timezone.utc).strftime("%Y-%m-%d") if topic.last_researched else None,
                                "is_active_research": topic.is_active_research,
                            }
                            
                            # Research the topic via research engine instance
                            result = await researcher.run_langgraph_research(user_id, topic_data)
                            
                            total_topics_researched += 1
                            if result and result.get("stored", False):
                                total_findings_stored += 1
                            if result and result.get("quality_score"):
                                quality_scores.append(result.get("quality_score"))
                            
                            # Update last_researched timestamp
                            new_timestamp = time.time()
                            logger.info(f"🎯 COMPLETED RESEARCH for '{topic_name}' - updating last_researched to {new_timestamp}")
                            await self.db_service.create_or_update_topic_score(
                                user_id=user_uuid,
                                topic_id=topic.id,
                                topic_name=topic_name,
                                last_researched=new_timestamp
                            )

                            # --- Topic expansion wiring ---
                            try:
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
                                        # Auto-deactivate only child topics that haven't been researched before
                                        # If user manually activated a previously auto-deactivated child topic, keep it active
                                        child_topic_id = child.get("topic_id")
                                        if child_topic_id:
                                            child_topic_uuid = uuid.UUID(str(child_topic_id))
                                            
                                            from models.topic import ResearchTopic
                                            
                                            # Get the child topic
                                            topic_query = select(ResearchTopic).where(
                                                ResearchTopic.id == child_topic_uuid
                                            )
                                            topic_result = await self.session.execute(topic_query)
                                            child_topic = topic_result.scalar_one_or_none()
                                            
                                            # Get TopicScore
                                            topic_score_query = select(TopicScore).where(
                                                and_(
                                                    TopicScore.topic_id == child_topic_uuid,
                                                    TopicScore.user_id == user_uuid
                                                )
                                            )
                                            score_result = await self.session.execute(topic_score_query)
                                            child_score = score_result.scalar_one_or_none()
                                            
                                            # Always update last_researched timestamp
                                            if child_score:
                                                child_score.last_researched = time.time()
                                                self.session.add(child_score)
                                            
                                            # Mark as researched_once and auto-deactivate if this is the first research
                                            # This prevents auto-deactivating child topics that users manually reactivated
                                            if child_topic:
                                                # Check if this is the first research (researched_once is False)
                                                if not child_topic.researched_once:
                                                    # Mark as researched
                                                    child_topic.researched_once = True
                                                    self.session.add(child_topic)
                                                    
                                                    # Auto-deactivate after first research
                                                    child_topic.is_active_research = False
                                                    if child_score:
                                                        child_score.is_active_research = False
                                                    logger.info(f"🔄 Auto-deactivated child topic '{child_name}' after first expansion research (can be manually reactivated if desired)")
                                                else:
                                                    logger.info(f"ℹ️ Child topic '{child_name}' has been researched before; keeping current active state")
                                            
                                            # Commit updates
                                            await self.session.commit()

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
                for user_uuid in user_ids:
                    await self._update_expansion_lifecycle(str(user_uuid))
            except Exception as e:
                logger.error(f"Lifecycle update failed: {str(e)}")
            
            # Update motivation scores for all researched topics (after research is complete)
            try:
                await self.update_scores()
                logger.info("🎯 Updated motivation scores after research cycle")
            except Exception as e:
                logger.error(f"Error updating motivation scores: {str(e)}")
            
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
            now_ts = time.time()
            promoted = paused = retired = 0
            changed = False
            window_days = config.EXPANSION_ENGAGEMENT_WINDOW_DAYS
            promote_thr = config.EXPANSION_PROMOTE_ENGAGEMENT
            retire_thr = config.EXPANSION_RETIRE_ENGAGEMENT
            min_quality = config.EXPANSION_MIN_QUALITY
            backoff_days = config.EXPANSION_BACKOFF_DAYS
            retire_ttl_days = config.EXPANSION_RETIRE_TTL_DAYS

            user_uuid = uuid.UUID(user_id)
            # Fetch topic scores for this user and filter to expansion topics using meta_data
            topic_scores = await self.db_service.get_user_topic_scores(user_uuid, active_only=False, limit=None, order_by_motivation=False)

            for ts in topic_scores:
                meta = ts.meta_data or {}
                if not meta.get('is_expansion', False):
                    continue
                name = ts.topic_name
                depth = int(meta.get('expansion_depth', 0) or 0)
                
                # Compute engagement and recent average quality from DB-backed findings
                engagement = 0.0
                try:
                    engagement = await self._get_topic_engagement_score(user_id, ts.topic_id)
                except Exception:
                    engagement = 0.0
                avg_quality = await self.get_recent_average_quality(user_id, ts.topic_id, window_days)

                status = meta.get('expansion_status', 'active')
                last_eval = float(meta.get('last_evaluated_at', 0) or 0)
                backoff_until = float(meta.get('last_backoff_until', 0) or 0)

                decision_debug = f"topic='{name}' depth={depth} engagement={engagement:.2f} avg_q={avg_quality:.2f} status={status}"

                # Promote to allow children
                if engagement >= promote_thr and avg_quality >= min_quality:
                    if not meta.get('child_expansion_enabled', False) or status != 'active':
                        meta['child_expansion_enabled'] = True
                        meta['expansion_status'] = 'active'
                        changed = True
                        promoted += 1
                        logger.debug(f"Lifecycle promote: {decision_debug}")
                    meta['last_evaluated_at'] = now_ts
                    if changed:
                        await self.db_service.update_topic_score(
                            user_uuid,
                            ts.topic_name,
                            meta_data=meta,
                        )
                    continue

                # Assess interactions in window via findings read/bookmark/integration
                any_interaction = False
                try:
                    success, findings = await self.research_service.async_get_findings(user_id, str(ts.topic_id))
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
                        meta['expansion_status'] = 'retired'
                        meta['last_evaluated_at'] = now_ts
                        changed = True
                        retired += 1
                        logger.debug(f"Lifecycle retire: {decision_debug}")
                        await self.db_service.update_topic_score(
                            user_uuid,
                            ts.topic_name,
                            meta_data=meta,
                        )
                        continue

                # Pause on cold engagement and no interactions in window
                if engagement < retire_thr and not any_interaction:
                    meta['is_active_research'] = False
                    meta['child_expansion_enabled'] = False
                    meta['expansion_status'] = 'paused'
                    meta['last_backoff_until'] = now_ts + backoff_days * 24 * 3600
                    meta['last_evaluated_at'] = now_ts
                    changed = True
                    paused += 1
                    logger.debug(f"Lifecycle pause: {decision_debug}")
                    await self.db_service.update_topic_score(
                        user_uuid,
                        ts.topic_name,
                        meta_data=meta,
                    )
                    continue

                # No action
                meta['last_evaluated_at'] = now_ts

            logger.info(f"Lifecycle update for {user_id}: promoted={promoted}, paused={paused}, retired={retired}")

        except Exception as e:
            logger.error(f"Error updating expansion lifecycle for user {user_id}: {str(e)}")

    # NOTE: Research execution lives in Research Engine now

    async def _on_research_completed(self, quality_score: float) -> None:
        """Handle completion of research cycle."""
        try:
            # Update topic engagement metrics based on research quality
            # This could be expanded to update success rates, etc.
            logger.info(f"🎯 Research cycle completed with average quality score: {quality_score:.2f}")
            
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
    
    async def _log_topic_scores_detail(self) -> None:
        """Log detailed scores for all active topics (debug helper)."""
        try:
            # Get all active topic scores
            result = await self.session.execute(
                select(TopicScore)
                .where(TopicScore.is_active_research == True)
                .order_by(TopicScore.motivation_score.desc())
            )
            topic_scores = result.scalars().all()
            
            if not topic_scores:
                logger.debug("🎯 No active topic scores to log")
                return
            
            logger.debug(f"🎯 ===== TOPIC SCORES SUMMARY ({len(topic_scores)} active topics) =====")
            for ts in topic_scores:
                last_researched_ago = "NEVER" if not ts.last_researched else f"{(time.time() - ts.last_researched):.0f}s ago"
                above_threshold = "✓" if ts.motivation_score >= self._config.topic_threshold else "✗"
                logger.debug(
                    f"🎯 {above_threshold} '{ts.topic_name}' (user={ts.user_id}):\n"
                    f"     motivation={ts.motivation_score:.4f} (threshold={self._config.topic_threshold})\n"
                    f"     staleness={ts.staleness_pressure:.4f} (coeff={ts.staleness_coefficient}), engagement={ts.engagement_score:.4f}, success={ts.success_rate:.4f}\n"
                    f"     last_researched={last_researched_ago}, findings={ts.total_findings} (read={ts.read_findings}, bookmarked={ts.bookmarked_findings}, integrated={ts.integrated_findings})"
                )
            logger.debug("🎯 ===== END TOPIC SCORES SUMMARY =====")
            
        except Exception as e:
            logger.debug(f"Error logging topic scores detail: {str(e)}")


