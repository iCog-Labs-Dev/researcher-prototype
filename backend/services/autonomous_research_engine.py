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
from research_graph_builder import research_graph
from services.motivation import MotivationSystem
from services.topic_expansion_service import TopicExpansionService
from services.topic import TopicService
from services.research import ResearchService
from db import SessionLocal
from exceptions import CommonError


class AutonomousResearcher:
    """
    LangGraph-based autonomous research engine that conducts background research on subscribed topics.
    """

    def __init__(self, motivation_config_override: dict = None):
        """Initialize the autonomous researcher."""
        self.is_running = False
        self.research_task = None
        
        # Initialize motivation system (will be set up in start() method with database session)
        self.motivation_system = None
        
        # Configure research parameters from config
        self.quality_threshold = config.RESEARCH_QUALITY_THRESHOLD
        self.enabled = config.RESEARCH_ENGINE_ENABLED

        # Topic expansion service is instantiated on-demand in process_expansions_for_root
        self.topic_service = TopicService()
        self.research_service = ResearchService()

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

    async def _update_expansion_lifecycle(self, user_id: str) -> None:
        """Evaluate and update lifecycle state for expansion topics for a user (delegates to MotivationSystem)."""
        if self.motivation_system:
            await self.motivation_system._update_expansion_lifecycle(user_id)
        else:
            logger.warning("Motivation system not initialized; cannot update expansion lifecycle")

    

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
            active_topics = await self.topic_service.async_get_active_research_topics(user_id=user_uuid)

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
                    logger.error(f"🔬 Error in manual LangGraph research for topic {topic.name}: {str(e)}")
                    research_details.append(
                        {
                            "topic_name": topic.name,
                            "success": False,
                            "stored": False,
                            "error": str(e),
                        }
                    )
                    continue

            # Cleanup old findings globally
            try:
                await self.research_service.async_cleanup_old_research_findings(config.RESEARCH_FINDINGS_RETENTION_DAYS)
            except Exception as cleanup_error:
                logger.debug(f"Error cleaning up old findings: {cleanup_error}")

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
            # Initialize TopicExpansionService
            try:
                from dependencies import zep_manager as _zep_manager_singleton  # type: ignore
                topic_expansion_service = TopicExpansionService(_zep_manager_singleton, None)
            except Exception:
                topic_expansion_service = TopicExpansionService(None, None)  # type: ignore[arg-type]

            # Generate candidates
            candidates = await topic_expansion_service.generate_candidates(user_id, root_topic)
            if not candidates:
                return results

            k = min(getattr(config, 'EXPLORATION_PER_ROOT_MAX', 2), len(candidates))
            selected = candidates[:k]
            active_children: List[Dict[str, Any]] = []

            for cand in selected:
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
                    "expansion_status": "active",
                    "last_evaluated_at": time.time(),
                }

                # Create topic in database using TopicService
                try:
                    # Try to create topic with research enabled - async_create_topic will check limit internally
                    try:
                        topic = await self.topic_service.async_create_topic(
                            user_id=user_id,
                            name=cand.name,
                            description=desc,
                            confidence_score=0.8,
                            is_active_research=True,
                            conversation_context="",
                            strict=True,
                        )
                        enable_research = True
                    except CommonError:
                        # Limit exceeded, create without research enabled
                        topic = await self.topic_service.async_create_topic(
                            user_id=user_id,
                            name=cand.name,
                            description=desc,
                            confidence_score=0.8,
                            is_active_research=False,
                            conversation_context="",
                            strict=True,
                        )
                        enable_research = False
                        extra_meta["expansion_status"] = "inactive"
                    
                    # Convert ResearchTopic to dict format expected by run_langgraph_research
                    topic_dict = {
                        "topic_id": str(topic.id),
                        "topic_name": topic.name,
                        "description": topic.description,
                        "is_active_research": topic.is_active_research,
                        "expansion_depth": child_depth,
                        "expansion_status": extra_meta["expansion_status"],
                        **extra_meta  # Include all expansion metadata
                    }
                    if topic.is_active_research:
                        active_children.append(topic_dict)
                except CommonError as e:
                    logger.warning(f"Cannot create expansion topic {cand.name} for user {user_id}: {e}")
                    enable_research = False
                    continue
                except Exception as e:
                    logger.error(f"Error creating expansion topic {cand.name} for user {user_id}: {e}")
                    continue

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


def initialize_autonomous_researcher(motivation_config_override: dict = None) -> AutonomousResearcher:
    """Initialize the global LangGraph autonomous researcher instance."""
    global autonomous_researcher
    autonomous_researcher = AutonomousResearcher(motivation_config_override)
    return autonomous_researcher


    
