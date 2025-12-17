"""
Autonomous Research Engine using LangGraph for conducting background research on user-subscribed topics.
"""

import asyncio
import time
import uuid
from datetime import timezone
from typing import Dict, List, Any, Optional


# Import logging
from services.logging_config import get_logger

logger = get_logger(__name__)

# Import configuration and existing components
import config
from storage.profile_manager import ProfileManager
from storage.research_manager import ResearchManager
from services.personalization_manager import PersonalizationManager
from research_graph_builder import research_graph
from services.motivation import MotivationSystem
from services.topic_expansion_service import TopicExpansionService
from services.topic import TopicService
from services.research import ResearchService


class AutonomousResearcher:
    """
    LangGraph-based autonomous research engine that conducts background research on subscribed topics.
    """

    def __init__(self, profile_manager: ProfileManager, research_manager: ResearchManager, motivation_config_override: dict = None, personalization_manager: PersonalizationManager = None):
        """Initialize the autonomous researcher."""
        self.profile_manager = profile_manager
        self.research_manager = research_manager
        self.is_running = False
        self.research_task = None
        
        # Use provided PersonalizationManager or create one using the same storage as profile_manager
        if personalization_manager:
            self.personalization_manager = personalization_manager
        else:
            # Extract storage manager from profile_manager to avoid duplication
            self.personalization_manager = PersonalizationManager(profile_manager.storage, profile_manager)
        
        # Initialize motivation system (will be set up in start() method with database session)
        self.motivation_system = None
        
        # Configure research parameters from config
        self.quality_threshold = config.RESEARCH_QUALITY_THRESHOLD
        self.enabled = config.RESEARCH_ENGINE_ENABLED

        # Topic expansion service is instantiated on-demand in process_expansions_for_root
        self.topic_service = TopicService()
        self.research_service = ResearchService()

    async def get_recent_average_quality(self, user_id: str, topic_name: str, window_days: int) -> float:
        """Compute recent average quality over window for a topic."""
        try:
            user_uuid = uuid.UUID(user_id) if user_id != "guest" else None
            if not user_uuid:
                return 0.0
            
            now = time.time()
            window_start = now - (window_days * 24 * 3600)
            findings = await self.research_service.async_get_findings(user_uuid, topic_name=topic_name, unread_only=False)
            scores = [f.get("quality_score") for f in findings if f.get("research_time", 0) >= window_start and isinstance(f.get("quality_score"), (int, float))]
            if not scores:
                return 0.0
            return sum(scores) / len(scores)
        except Exception:
            return 0.0

        

    async def start(self):
        """Start the autonomous research engine."""
        if not self.enabled:
            logger.info("""🔬 Autonomous Research Engine is disabled in configuration.
                        It can be enabled it in the Research Topics dashboard.""")
            return

        if self.is_running:
            logger.warning("🔬 Autonomous Research Engine is already running")
            return

        self.is_running = True
        logger.info("🔬 Starting LangGraph Autonomous Research Engine...")

        # Initialize motivation system with database session
        try:
            from db import SessionLocal
            # Create a persistent session for the motivation system
            self.db_session = SessionLocal()
            self.motivation_system = MotivationSystem(
                session=self.db_session,
                profile_manager=self.profile_manager,
                research_manager=self.research_manager,
                personalization_manager=self.personalization_manager
            )
            await self.motivation_system.start()
            logger.info("🔬 Motivation system initialized and started")
        except Exception as e:
            logger.error(f"🔬 Failed to initialize motivation system: {str(e)}", exc_info=True)
            self.is_running = False
            return

        # Start the research loop (now handled by motivation system)
        # The motivation system will handle the main research loop
        logger.info("🔬 Autonomous Research Engine started with motivation-driven research loop")

    async def stop(self):
        """Stop the autonomous research engine."""
        if not self.is_running:
            return

        logger.info("🔬 Stopping LangGraph Autonomous Research Engine...")
        self.is_running = False

        # Stop motivation system
        if self.motivation_system:
            try:
                await self.motivation_system.stop()
                logger.info("🔬 Motivation system stopped")
            except Exception as e:
                logger.error(f"🔬 Error stopping motivation system: {str(e)}")
        
        # Close database session
        if hasattr(self, 'db_session') and self.db_session:
            try:
                await self.db_session.close()
                logger.info("🔬 Database session closed")
            except Exception as e:
                logger.error(f"🔬 Error closing database session: {str(e)}")

        logger.info("🔬 LangGraph Autonomous Research Engine stopped")

    def enable(self):
        """Enable the research engine."""
        self.enabled = True
        logger.info("🔬 Autonomous Research Engine enabled")

    def disable(self):
        """Disable the research engine."""
        self.enabled = False
        logger.info("🔬 Autonomous Research Engine disabled")

    def toggle_enabled(self):
        """Toggle the enabled state of the research engine."""
        self.enabled = not self.enabled
        logger.info(f"🔬 Autonomous Research Engine {'enabled' if self.enabled else 'disabled'}")
        return self.enabled

    def is_enabled(self) -> bool:
        """Check if the research engine is enabled."""
        return self.enabled

    async def _conduct_research_cycle(self):
        """Conduct a complete research cycle for all users with active topics (DB-backed)."""
        try:
            active_topics = await self.topic_service.async_get_active_research_topics()
            if not active_topics:
                logger.info("🔬 No active research topics found in database")
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
                    root_name = topic.name
                    logger.info(f"🔬 Researching topic: {root_name} for user {user_id}")

                    topic_payload = {
                        "topic_id": str(topic.id),
                        "topic_name": topic.name,
                        "description": topic.description,
                        "last_researched": topic.last_researched.astimezone(timezone.utc).strftime("%Y-%m-%d") if topic.last_researched else None,
                        "is_active_research": topic.is_active_research,
                    }

                    root_result = await self.run_langgraph_research(user_id, topic_payload)
                    if root_result:
                        total_topics_researched += 1
                        if root_result.get("stored", False):
                            total_findings_stored += 1
                        if root_result.get("quality_score"):
                            quality_scores.append(root_result.get("quality_score"))

                    try:
                        child_runs = await self.process_expansions_for_root(user_id, topic_payload)
                        if child_runs:
                            logger.info("🔬 Executed %d expansion child research task(s) for user %s on '%s'", len(child_runs), user_id, root_name)
                            for cr in child_runs:
                                cres = cr.get("result") or {}
                                total_topics_researched += 1
                                if cres.get("stored", False):
                                    total_findings_stored += 1
                                if cres.get("quality_score"):
                                    quality_scores.append(cres.get("quality_score"))
                    except Exception as ex:
                        logger.debug(f"Expansion processing failed for '{root_name}': {ex}")

                    # Cleanup old findings for this user (once per user)
                    if user_id not in processed_users:
                        try:
                            user_uuid = uuid.UUID(user_id) if user_id != "guest" else None
                            if user_uuid:
                                await self.research_service.async_cleanup_old_research_findings(user_uuid, config.RESEARCH_FINDINGS_RETENTION_DAYS)
                        except Exception as cleanup_error:
                            logger.debug(f"Error cleaning up old findings for user {user_id}: {cleanup_error}")
                        processed_users.add(user_id)

                    await asyncio.sleep(config.RESEARCH_TOPIC_DELAY)

                except Exception as e:
                    logger.error(
                        f"🔬 Error researching topic {getattr(topic, 'name', 'unknown')} for user {getattr(topic, 'user_id', 'unknown')}: {str(e)}"
                    )
                    continue

            logger.info(
                f"🔬 LangGraph research cycle completed: {total_topics_researched} topics researched, {total_findings_stored} findings stored"
            )

            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

            # Update expansion lifecycle for all processed users
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

            for sid, session_topics in topics_data.get('sessions', {}).items():
                for topic in session_topics:
                    if not topic.get('is_expansion', False):
                        continue
                    name = topic.get('topic_name')
                    depth = int(topic.get('expansion_depth', 0) or 0)
                    engagement = 0.0
                    try:
                        engagement = 0.0
                        if self.motivation_system:
                            engagement = await self.motivation_system._get_topic_engagement_score(user_id, name)
                    except Exception:
                        engagement = 0.0
                    avg_quality = await self.get_recent_average_quality(user_id, name, window_days)

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
                    try:
                        user_uuid = uuid.UUID(user_id) if user_id != "guest" else None
                        if user_uuid:
                            findings = await self.research_service.async_get_findings(user_uuid, topic_name=name, unread_only=False)
                            window_start = now_ts - window_days * 24 * 3600
                            any_interaction = any(
                                (f.get('read', False) or f.get('bookmarked', False) or f.get('integrated', False)) and f.get('research_time', 0) >= window_start
                                for f in findings
                            )
                        else:
                            any_interaction = False
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

    

    async def trigger_research_for_user(self, user_id: str) -> Dict[str, Any]:
        """
        Manually trigger research for a specific user using LangGraph (for testing/API).

        Args:
            user_id: ID of the user

        Returns:
            Dictionary with research results summary
        """
        try:
            logger.info(f"🔬 Manual LangGraph research trigger for user: {user_id}")

            try:
                user_uuid = uuid.UUID(user_id)
            except Exception:
                return {"success": False, "error": "Invalid user_id", "topics_researched": 0, "findings_stored": 0}

            # Get active research topics for this user from DB
            active_topics_all = await self.topic_service.async_get_active_research_topics()
            active_topics = [t for t in active_topics_all if t.user_id == user_uuid]

            if not active_topics:
                return {
                    "success": True,
                    "message": "No active research topics found",
                    "topics_researched": 0,
                    "findings_stored": 0,
                }

            # Research all active topics (already limited by MAX_ACTIVE_RESEARCH_TOPICS_PER_USER)
            topics_to_research = active_topics
            topics_researched = 0
            findings_stored = 0
            research_details = []

            for topic in topics_to_research:
                try:
                    logger.info(f"🔬 Manual LangGraph research for topic: {topic.name}")

                    # Force research using LangGraph regardless of last research time
                    topic_payload = {
                        "topic_id": str(topic.id),
                        "topic_name": topic.name,
                        "description": topic.description,
                        "last_researched": topic.last_researched.astimezone(timezone.utc).strftime("%Y-%m-%d") if topic.last_researched else None,
                        "is_active_research": topic.is_active_research,
                    }
                    research_result = await self.run_langgraph_research(user_id, topic_payload)

                    topics_researched += 1

                    if research_result and research_result.get("stored", False):
                        findings_stored += 1

                    research_details.append(
                        {
                            "topic_name": topic.name,
                            "success": research_result.get("success", False) if research_result else False,
                            "stored": research_result.get("stored", False) if research_result else False,
                            "quality_score": research_result.get("quality_score", 0.0) if research_result else 0.0,
                            "reason": research_result.get("reason") if research_result else None,
                            "error": research_result.get("error") if research_result else None,
                        }
                    )

                    # Small delay between topics
                    await asyncio.sleep(config.RESEARCH_MANUAL_DELAY)

                except Exception as e:
                    logger.error(f"🔬 Error in manual LangGraph research for topic {getattr(topic, 'name', 'unknown')}: {str(e)}")
                    research_details.append(
                        {
                            "topic_name": getattr(topic, "name", "Unknown"),
                            "success": False,
                            "stored": False,
                            "error": str(e),
                        }
                    )
                    continue

            # Cleanup old findings
            try:
                user_uuid = uuid.UUID(user_id) if user_id != "guest" else None
                if user_uuid:
                    await self.research_service.async_cleanup_old_research_findings(user_uuid, config.RESEARCH_FINDINGS_RETENTION_DAYS)
            except Exception as cleanup_error:
                logger.debug(f"Error cleaning up old findings for user {user_id}: {cleanup_error}")

            return {
                "success": True,
                "message": f"Manual LangGraph research completed for {topics_researched} topics",
                "topics_researched": topics_researched,
                "findings_stored": findings_stored,
                "total_active_topics": len(active_topics),
                "research_details": research_details,
            }

        except Exception as e:
            logger.error(f"🔬 Error in manual LangGraph research trigger: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e), "topics_researched": 0, "findings_stored": 0}

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the research engine."""
        status = {
            "enabled": self.enabled,
            "running": self.is_running,
            "quality_threshold": self.quality_threshold,
            "retention_days": config.RESEARCH_FINDINGS_RETENTION_DAYS,
            "engine_type": "Motivation-driven LangGraph-based",
            "research_graph_nodes": [
                "research_initializer",
                "research_query_generator",
                "search",
                "research_quality_assessor",
                "research_deduplication",
                "research_storage",
            ],
        }
        
        # Add motivation system status if available
        if self.motivation_system:
            status["motivation_system"] = self.motivation_system.get_status()
        
        return status

    # Reusable helper to run LangGraph research for a single topic (instance method)
    async def run_langgraph_research(self, user_id: str, topic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run LangGraph research workflow for a single topic and return the result."""
        try:
            topic_name = topic["topic_name"]
            topic_description = topic.get("description", "")
            last_researched = topic.get("last_researched")

            logger.info(f"🔬 Starting LangGraph research workflow for topic: {topic_name}")

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

            logger.debug(f"🔬 Invoking research graph for topic: {topic_name}")
            research_result = await research_graph.ainvoke(research_state)

            # In tests, research_graph may be patched; guard lookups
            storage_results = {}
            try:
                storage_results = research_result.get("module_results", {}).get("research_storage", {})
            except Exception:
                storage_results = {}
            if storage_results.get("success", False):
                stored = storage_results.get("stored", False)
                quality_score = storage_results.get("quality_score", 0.0)
                if stored:
                    logger.info(
                        f"🔬 LangGraph research completed successfully for {topic_name} - Finding stored (quality: {quality_score:.2f})"
                    )
                    return {
                        "success": True,
                        "stored": True,
                        "quality_score": quality_score,
                        "finding_id": storage_results.get("finding_id"),
                        "insights_count": storage_results.get("insights_count", 0),
                    }
                else:
                    reason = storage_results.get("reason", "Unknown reason")
                    logger.info(f"🔬 LangGraph research completed for {topic_name} - Finding not stored: {reason}")
                    return {"success": True, "stored": False, "reason": reason, "quality_score": quality_score}
            else:
                error = storage_results.get("error") if isinstance(storage_results, dict) else None
                if not error:
                    error = "No successful search results available"
                logger.error(f"🔬 LangGraph research failed for {topic_name}: {error}")
                return {"success": False, "error": error, "stored": False}

        except Exception as e:
            logger.error(
                f"🔬 Error in LangGraph research workflow for topic {topic.get('topic_name', 'unknown')}: {str(e)}",
                exc_info=True,
            )
            return {"success": False, "error": str(e), "stored": False}

    # Reusable helper to generate and process expansions for a root topic (instance method)
    async def process_expansions_for_root(self, user_id: str, root_topic: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate expansion candidates for a root topic, create child topics respecting breadth limits, and research active children."""
        results: List[Dict[str, Any]] = []
        try:
            # Initialize TopicExpansionService similar to engine init
            try:
                from dependencies import zep_manager as _zep_manager_singleton  # type: ignore
                topic_expansion_service = TopicExpansionService(_zep_manager_singleton, self.research_manager)
            except Exception:
                topic_expansion_service = TopicExpansionService(None, self.research_manager)  # type: ignore[arg-type]

            # Generate candidates
            candidates = await topic_expansion_service.generate_candidates(user_id, root_topic)
            if not candidates:
                return results

            k = min(getattr(config, 'EXPLORATION_PER_ROOT_MAX', 2), len(candidates))
            selected = candidates[:k]
            active_children: List[Dict[str, Any]] = []

            for cand in selected:
                # Breadth control: allow activation only if within limits
                limit_check = self.research_manager.check_active_topics_limit(user_id, enabling_new=True)
                enable_research = bool(limit_check.get("allowed", False))

                # Build child metadata
                parent_depth = int(root_topic.get('expansion_depth', 0) or 0)
                child_depth = min(parent_depth + 1, getattr(config, 'EXPANSION_MAX_DEPTH', 2))
                desc = getattr(cand, 'description', None) or (
                    f"Research into {cand.name.lower()} and its relationship to {root_topic.get('topic_name','').lower()}"
                )
                extra_meta = {
                    "is_expansion": True,
                    "origin": {
                        "type": "expansion",
                        "parent_topic": root_topic.get('topic_name'),
                        "method": getattr(cand, 'source', None),
                        "similarity": getattr(cand, 'similarity', None),
                        "rationale": getattr(cand, 'rationale', None),
                    },
                    "expansion_depth": child_depth,
                    "child_expansion_enabled": True,
                    "expansion_status": "active" if enable_research else "inactive",
                    "last_evaluated_at": time.time(),
                }

                res = self.research_manager.add_custom_topic(
                    user_id=user_id,
                    topic_name=cand.name,
                    description=desc,
                    confidence_score=0.8,
                    enable_research=enable_research,
                    extra=extra_meta,
                )
                if res and res.get('success') and res.get('topic', {}).get('is_active_research', False):
                    active_children.append(res['topic'])

            # Research active children immediately
            for child in active_children:
                try:
                    child_result = await self.run_langgraph_research(user_id, child)
                    results.append({"topic": child, "result": child_result})
                except Exception as e:
                    logger.error(f"Error researching expansion child {child.get('topic_name')}: {e}")
                    continue

            return results
        except Exception as e:
            logger.debug(f"process_expansions_for_root failed: {e}")
            return results


# Global instance
autonomous_researcher: Optional[AutonomousResearcher] = None


def get_autonomous_researcher() -> Optional[AutonomousResearcher]:
    """Get the global autonomous researcher instance."""
    return autonomous_researcher


def initialize_autonomous_researcher(profile_manager: ProfileManager, research_manager: ResearchManager, motivation_config_override: dict = None) -> AutonomousResearcher:
    """Initialize the global LangGraph autonomous researcher instance."""
    global autonomous_researcher
    autonomous_researcher = AutonomousResearcher(profile_manager, research_manager, motivation_config_override)
    return autonomous_researcher


    
