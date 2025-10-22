"""
Motivation System with database persistence and main research loop.
"""

import asyncio
import time
import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from services.logging_config import get_logger
from database.motivation_repository import MotivationRepository
from storage.profile_manager import ProfileManager
from storage.research_manager import ResearchManager
from services.personalization_manager import PersonalizationManager
from research_graph_builder import research_graph
from services.topic_expansion_service import TopicExpansionService
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
        self.max_topics_per_user = config.RESEARCH_MAX_TOPICS_PER_USER
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
        
        # Research graph
        self.research_graph = research_graph
        
        logger.info("🎯 Motivation System initialized")

    async def initialize(self) -> None:
        """Initialize the motivation system with default configuration if needed."""
        try:
            # Get or create default configuration
            self._config = await self.db_service.get_default_config()
            if not self._config:
                logger.info("Creating default motivation configuration...")
                self._config = await self.db_service.create_default_config()
            
            # Get or create active motivation state
            state = await self.db_service.get_motivation_state()
            if not state:
                logger.info("Creating initial motivation state...")
                state = await self.db_service.create_motivation_state()
            
            logger.info(f"🎯 Motivation system initialized with config: {self._config.id}, state: {state.id}")
            
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
                
                # Check if research is needed
                research_needed = await self.check_for_research_needed()
                
                if research_needed:
                    logger.info("🎯 Research needed - starting research cycle")
                    result = await self._conduct_research_cycle()
                    
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
        Update motivation scores for all active topics.
        
        This function:
        1. Gets all users and their active topics
        2. Calculates per-topic motivation scores based on:
           - Staleness pressure (time since last research)
           - User engagement with research findings
           - Research success rate
        3. Updates scores in the database
        """
        try:
            # Get all users
            users = self.profile_manager.list_users()
            users_list = list(users) if users else []
            all_users = users_list or ["guest"]
            
            updated_count = 0
            
            for user_id in all_users:
                try:
                    # Get active research topics for this user
                    active_topics = self.research_manager.get_active_research_topics(user_id)
                    
                    if not active_topics:
                        continue
                    
                    user_uuid = uuid.UUID(user_id) if user_id != "guest" else None
                    if not user_uuid:
                        continue  # Skip guest user for now
                    
                    for topic in active_topics:
                        topic_name = topic.get('topic_name', '')
                        if not topic_name:
                            continue
                        
                        # Calculate motivation score
                        motivation_score = await self._calculate_topic_motivation_score(
                            str(user_uuid), topic
                        )
                        
                        # Update in database
                        await self.db_service.create_or_update_topic_score(
                            user_id=user_uuid,
                            topic_name=topic_name,
                            motivation_score=motivation_score,
                            last_researched=topic.get('last_researched'),
                            staleness_coefficient=topic.get('staleness_coefficient', 1.0),
                            is_active_research=topic.get('is_active_research', False)
                        )
                        
                        updated_count += 1
                
                except Exception as e:
                    logger.error(f"Error updating scores for user {user_id}: {str(e)}")
                    continue
            
            logger.debug(f"🎯 Updated motivation scores for {updated_count} topics")
            
        except Exception as e:
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
            
            # Get all users
            users = self.profile_manager.list_users()
            users_list = list(users) if users else []
            all_users = users_list or ["guest"]
            
            for user_id in all_users:
                try:
                    user_uuid = uuid.UUID(user_id) if user_id != "guest" else None
                    if not user_uuid:
                        continue
                    
                    # Get topics needing research
                    topics_needing_research = await self.db_service.get_topics_needing_research(
                        user_uuid, 
                        threshold=self._config.topic_threshold,
                        limit=1  # Just check if any exist
                    )
                    
                    if topics_needing_research:
                        logger.debug(f"🎯 Found {len(topics_needing_research)} topics needing research for user {user_id}")
                        return True
                
                except Exception as e:
                    logger.error(f"Error checking research need for user {user_id}: {str(e)}")
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
            engagement_score = await self._get_topic_engagement_score(
                user_id, topic.get('topic_name', '')
            )
            success_rate = await self._get_topic_success_rate(
                user_id, topic.get('topic_name', '')
            )
            
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

    async def _get_topic_engagement_score(self, user_id: str, topic_name: str) -> float:
        """Get engagement score for a topic based on research findings interactions."""
        try:
            if not self.personalization_manager:
                return 0.0
            
            # Import here to avoid circular dependencies
            from storage.research_manager import ResearchManager
            research_manager = ResearchManager(
                self.personalization_manager.storage, 
                self.personalization_manager.profile_manager
            )
            
            # Get all findings for this user and topic
            all_findings = research_manager.get_research_findings_for_api(user_id, topic_name, unread_only=False)
            if not all_findings:
                return 0.0
            
            total_findings = len(all_findings)
            read_findings = sum(1 for f in all_findings if f.get('read', False))
            bookmarked_findings = sum(1 for f in all_findings if f.get('bookmarked', False))
            integrated_findings = sum(1 for f in all_findings if f.get('integrated', False))
            
            # Base engagement: percentage of findings read
            read_percentage = read_findings / total_findings if total_findings > 0 else 0.0
            
            # Bonus for recent reads (findings read in last 7 days get extra weight)
            recent_threshold = time.time() - (7 * 24 * 3600)  # 7 days ago
            recent_reads = sum(1 for f in all_findings 
                             if f.get('read', False) and 
                             f.get('created_at', 0) > recent_threshold)
            
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
            logger.debug(f"Error calculating engagement score for {topic_name}: {str(e)}")
            return 0.0

    async def _get_topic_success_rate(self, user_id: str, topic_name: str) -> float:
        """Calculate research success rate from user engagement patterns."""
        try:
            if not self.personalization_manager:
                return 0.5  # Default neutral success rate
            
            # Use engagement as proxy for success rate
            engagement_score = await self._get_topic_engagement_score(user_id, topic_name)
            success_rate = 0.3 + (engagement_score * 0.4)  # Range: 0.3-0.7
            
            return success_rate
            
        except Exception as e:
            logger.debug(f"Error getting success rate for {topic_name}: {str(e)}")
            return 0.5

    async def _conduct_research_cycle(self) -> Dict[str, Any]:
        """Conduct a complete research cycle for all users with motivated topics."""
        try:
            # Get all users
            users = self.profile_manager.list_users()
            users_list = list(users) if users else []
            all_users = users_list or ["guest"]
            
            logger.info(f"🎯 Scanning {len(all_users)} users for motivated research topics...")
            
            total_topics_researched = 0
            total_findings_stored = 0
            quality_scores: List[float] = []
            
            for user_id in all_users:
                try:
                    user_uuid = uuid.UUID(user_id) if user_id != "guest" else None
                    if not user_uuid:
                        continue
                    
                    # Get topics needing research based on motivation scores
                    topics_needing_research = await self.db_service.get_topics_needing_research(
                        user_uuid,
                        threshold=self._config.topic_threshold,
                        limit=self.max_topics_per_user
                    )
                    
                    if not topics_needing_research:
                        continue
                    
                    logger.info(f"🎯 User {user_id} has {len(topics_needing_research)} motivated topics")
                    
                    for topic_score in topics_needing_research:
                        try:
                            topic_name = topic_score.topic_name
                            logger.info(f"🎯 Researching motivated topic: {topic_name} for user {user_id}")
                            
                            # Get full topic data from research manager
                            topic_data = self.research_manager.get_topic_by_name(user_id, topic_name)
                            if not topic_data:
                                continue
                            
                            # Research the topic
                            result = await self._research_topic_with_langgraph(user_id, topic_data)
                            
                            total_topics_researched += 1
                            if result and result.get("stored", False):
                                total_findings_stored += 1
                            if result and result.get("quality_score"):
                                quality_scores.append(result.get("quality_score"))
                            
                            # Update last_researched timestamp
                            await self.db_service.create_or_update_topic_score(
                                user_id=user_uuid,
                                topic_name=topic_name,
                                last_researched=time.time()
                            )
                            
                            # Small delay between topics
                            await asyncio.sleep(config.RESEARCH_TOPIC_DELAY)
                            
                        except Exception as e:
                            logger.error(f"🎯 Error researching topic {topic_name}: {str(e)}")
                            continue
                    
                    # Cleanup old findings for this user
                    self.research_manager.cleanup_old_research_findings(user_id, config.RESEARCH_FINDINGS_RETENTION_DAYS)
                
                except Exception as e:
                    logger.error(f"🎯 Error processing user {user_id}: {str(e)}")
                    continue
            
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            
            logger.info(f"🎯 Research cycle completed: {total_topics_researched} topics, {total_findings_stored} findings, avg quality: {avg_quality:.2f}")
            
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

    async def _research_topic_with_langgraph(self, user_id: str, topic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Conduct research on a specific topic using the LangGraph research workflow."""
        try:
            topic_name = topic["topic_name"]
            topic_description = topic.get("description", "")
            last_researched = topic.get("last_researched")

            logger.info(f"🎯 Starting LangGraph research workflow for topic: {topic_name}")

            # Create initial state for the research graph
            research_state = {
                "messages": [],
                "model": config.RESEARCH_MODEL,
                "temperature": 0.3,
                "max_tokens": config.RESEARCH_MAX_TOKENS,
                "personality": {"style": "research", "tone": "analytical"},
                "current_module": None,
                "module_results": {},
                "workflow_context": {
                    "research_context": {
                        "topic_name": topic_name,
                        "topic_description": topic_description,
                        "user_id": user_id,
                        "last_researched": last_researched,
                        "model": config.RESEARCH_MODEL,
                    }
                },
                "user_id": user_id,
                "routing_analysis": None,
                "thread_id": None,
                "memory_context": None,
            }

            # Run the research workflow through LangGraph
            logger.debug(f"🎯 Invoking research graph for topic: {topic_name}")
            research_result = await self.research_graph.ainvoke(research_state)

            # Extract results from the workflow
            storage_results = research_result.get("module_results", {}).get("research_storage", {})

            if storage_results.get("success", False):
                stored = storage_results.get("stored", False)
                quality_score = storage_results.get("quality_score", 0.0)

                if stored:
                    logger.info(f"🎯 LangGraph research completed successfully for {topic_name} - Finding stored (quality: {quality_score:.2f})")
                    return {
                        "success": True,
                        "stored": True,
                        "quality_score": quality_score,
                        "finding_id": storage_results.get("finding_id"),
                        "insights_count": storage_results.get("insights_count", 0),
                    }
                else:
                    reason = storage_results.get("reason", "Unknown reason")
                    logger.info(f"🎯 LangGraph research completed for {topic_name} - Finding not stored: {reason}")
                    return {"success": True, "stored": False, "reason": reason, "quality_score": quality_score}
            else:
                error = storage_results.get("error", "Unknown error in storage")
                logger.error(f"🎯 LangGraph research failed for {topic_name}: {error}")
                return {"success": False, "error": error, "stored": False}

        except Exception as e:
            logger.error(f"🎯 Error in LangGraph research workflow for topic {topic.get('topic_name', 'unknown')}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e), "stored": False}

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
            user_uuid = uuid.UUID(user_id) if user_id != "guest" else None
            if not user_uuid:
                return {}
            
            return await self.db_service.get_motivation_statistics(user_uuid)
            
        except Exception as e:
            logger.error(f"Error getting motivation statistics for {user_id}: {str(e)}")
            return {}

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the motivation system."""
        return {
            "running": self.is_running,
            "check_interval": self.check_interval,
            "max_topics_per_user": self.max_topics_per_user,
            "quality_threshold": self.quality_threshold,
            "system_type": "MotivationSystem",
            "features": [
                "database_persistence",
                "per_topic_scoring",
                "integrated_research_loop",
                "engagement_based_motivation"
            ]
        }


