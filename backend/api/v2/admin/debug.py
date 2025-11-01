from fastapi import APIRouter, Request, HTTPException
from typing import Optional, List, Dict, Any

from dependencies import (
    profile_manager,
    research_manager,
    zep_manager,
    _motivation_config_override,
)
import config
from schemas.schemas import MotivationConfigUpdate, ExpansionRequest
from services.autonomous_research_engine import initialize_autonomous_researcher
from services.logging_config import get_logger
from services.topic_expansion_service import TopicExpansionService, ExpansionCandidate

router = APIRouter(prefix="/debug")

logger = get_logger(__name__)


@router.post("/expand/{user_id}")
async def debug_expand_topics(
    user_id: str,
    body: ExpansionRequest
):
    """Debug-only: Generate (and optionally persist) topic expansion candidates from Zep."""
    try:
        if not config.ZEP_ENABLED or not zep_manager.is_enabled():
            return {"success": False, "error": "Zep disabled"}

        # Validate input
        root = body.root_topic or {}
        name = (root.get("topic_name") or "").strip()
        if not name:
            return {"success": False, "error": "Invalid root_topic.topic_name"}

        # Generate candidates
        svc = TopicExpansionService(zep_manager, research_manager)
        candidates: List[ExpansionCandidate] = await svc.generate_candidates(user_id, body.root_topic)

        # Transform for response
        cand_dicts: List[Dict[str, Any]] = [
            {
                "name": c.name,
                "source": c.source,
                "similarity": c.similarity,
                "rationale": c.rationale,
            }
            for c in candidates
        ]

        created: List[Dict[str, Any]] = []
        skipped_duplicates: List[str] = []

        # Optional persistence path (bounded)
        limit = body.limit if isinstance(body.limit, int) and body.limit > 0 else config.EXPLORATION_PER_ROOT_MAX
        if body.create_topics:
            to_create = min(limit, len(candidates))
            root_name = (body.root_topic.get("topic_name") or "").strip()
            base_desc = (body.root_topic.get("description") or "").strip()
            for cand in candidates[:to_create]:
                desc = base_desc or f"Expanded from '{root_name}' via Zep ({cand.source})"
                # TODO: Extend topic schema to capture is_expansion + origin metadata
                result = research_manager.add_custom_topic(
                    user_id=user_id,
                    topic_name=cand.name,
                    description=desc,
                    confidence_score=0.8,
                    enable_research=bool(body.enable_research),
                )
                if result.get("success"):
                    topic = result.get("topic", {})
                    created.append({"topic_id": topic.get("topic_id"), "name": topic.get("topic_name")})
                else:
                    # Likely duplicate
                    skipped_duplicates.append(cand.name)

        logger.info(
            f"Expansion preview for user {user_id}: {len(cand_dicts)} candidates, created {len(created)}"
        )

        return {
            "success": True,
            "root_topic": body.root_topic.get("topic_name"),
            "candidates": cand_dicts,
            "created_topics": created,
            "skipped_duplicates": skipped_duplicates,
            "limit": (body.limit if body.limit is not None else config.EXPLORATION_PER_ROOT_MAX),
            "metrics": getattr(svc, "metrics", {}),
        }

    except Exception as e:
        logger.error(f"Error expanding topics for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Expansion error: {str(e)}")


@router.get("/active-topics")
async def get_debug_active_topics():
    """Debug endpoint to see active research topics across all users."""
    try:
        debug_info = {"total_users": 0, "users_with_active_topics": 0, "total_active_topics": 0, "user_breakdown": []}

        # Get all users
        all_users = profile_manager.list_users()
        debug_info["total_users"] = len(all_users)

        for user_id in all_users:
            try:
                active_topics = research_manager.get_active_research_topics(user_id)
                if active_topics:
                    debug_info["users_with_active_topics"] += 1
                    debug_info["total_active_topics"] += len(active_topics)

                    debug_info["user_breakdown"].append(
                        {
                            "user_id": user_id,
                            "active_topics_count": len(active_topics),
                            "topics": [
                                {
                                    "name": topic.get("topic_name"),
                                    "description": (
                                        topic.get("description", "")[:100] + "..."
                                        if len(topic.get("description", "")) > 100
                                        else topic.get("description", "")
                                    ),
                                    "last_researched": topic.get("last_researched"),
                                    "research_count": topic.get("research_count", 0),
                                }
                                for topic in active_topics
                            ],
                        }
                    )

            except Exception as e:
                logger.error(f"Error getting active topics for user {user_id}: {str(e)}")
                continue

        return debug_info

    except Exception as e:
        logger.error(f"Error getting debug active topics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting debug info: {str(e)}")


@router.get("/config-override")
async def get_config_override():
    """Debug endpoint to see what's in the config override."""
    return {"override": _motivation_config_override}


@router.post("/clear-override")
async def clear_config_override():
    """Debug endpoint to clear the config override."""
    global _motivation_config_override
    _motivation_config_override = {}
    return {"success": True, "message": "Config override cleared"}


@router.get("/motivation")
async def get_motivation_status(
    request: Request,
):
    """Debug endpoint to check motivation system status."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            researcher = request.app.state.autonomous_researcher
            motivation = researcher.motivation

            # Only tick if the research engine is actually running
            # This ensures drives only evolve when the engine is active
            if researcher.is_running:
                motivation.tick()

            return {
                "motivation_system": {
                    "boredom": round(motivation.boredom, 4),
                    "curiosity": round(motivation.curiosity, 4),
                    "tiredness": round(motivation.tiredness, 4),
                    "satisfaction": round(motivation.satisfaction, 4),
                    "impetus": round(motivation.impetus(), 4),
                    "threshold": motivation.drives.threshold,
                    "should_research": motivation.should_research(),
                    "time_since_last_tick": round(time.time() - motivation.last_tick, 2),
                },
                "research_engine": {
                    "enabled": researcher.enabled,
                    "running": researcher.is_running,
                    "check_interval": researcher.check_interval,
                },
                "drive_rates": {
                    "boredom_rate": motivation.drives.boredom_rate,
                    "curiosity_decay": motivation.drives.curiosity_decay,
                    "tiredness_decay": motivation.drives.tiredness_decay,
                    "satisfaction_decay": motivation.drives.satisfaction_decay,
                },
            }
        else:
            return {"error": "Autonomous researcher not available"}

    except Exception as e:
        logger.error(f"Error getting motivation status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting motivation status: {str(e)}")


@router.post("/trigger-user-activity")
async def trigger_user_activity(
    request: Request,
):
    """Debug endpoint to simulate user activity (increases curiosity)."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            researcher = request.app.state.autonomous_researcher
            researcher.motivation.on_user_activity()

            return {
                "success": True,
                "message": "User activity triggered",
                "new_motivation_state": {
                    "boredom": round(researcher.motivation.boredom, 4),
                    "curiosity": round(researcher.motivation.curiosity, 4),
                    "impetus": round(researcher.motivation.impetus(), 4),
                    "should_research": researcher.motivation.should_research(),
                },
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")

    except Exception as e:
        logger.error(f"Error triggering user activity: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error triggering user activity: {str(e)}")


@router.post("/adjust-drives")
async def adjust_motivation_drives(
    request: Request,
    boredom: Optional[float] = None,
    curiosity: Optional[float] = None,
    tiredness: Optional[float] = None,
    satisfaction: Optional[float] = None,
):
    """Debug endpoint to manually set motivation drive values for testing."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            researcher = request.app.state.autonomous_researcher
            motivation = researcher.motivation

            old_values = {
                "boredom": motivation.boredom,
                "curiosity": motivation.curiosity,
                "tiredness": motivation.tiredness,
                "satisfaction": motivation.satisfaction,
            }

            # Update provided values
            if boredom is not None:
                motivation.boredom = max(0.0, min(1.0, boredom))
            if curiosity is not None:
                motivation.curiosity = max(0.0, min(1.0, curiosity))
            if tiredness is not None:
                motivation.tiredness = max(0.0, min(1.0, tiredness))
            if satisfaction is not None:
                motivation.satisfaction = max(0.0, min(1.0, satisfaction))

            new_values = {
                "boredom": motivation.boredom,
                "curiosity": motivation.curiosity,
                "tiredness": motivation.tiredness,
                "satisfaction": motivation.satisfaction,
            }

            return {
                "success": True,
                "message": "Motivation drives adjusted",
                "old_values": old_values,
                "new_values": new_values,
                "impetus": round(motivation.impetus(), 4),
                "should_research": motivation.should_research(),
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")

    except Exception as e:
        logger.error(f"Error adjusting motivation drives: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adjusting drives: {str(e)}")


@router.post("/update-config")
async def update_motivation_config(
    request: Request,
    config: MotivationConfigUpdate,
):
    """Debug endpoint to update motivation system configuration parameters."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            researcher = request.app.state.autonomous_researcher
            motivation = researcher.motivation
            drives_config = motivation.drives

            # Check if this is a complete config replacement (all parameters provided)
            all_params_provided = all(
                getattr(config, param) is not None
                for param in ["threshold", "boredom_rate", "curiosity_decay", "tiredness_decay", "satisfaction_decay"]
            )

            if all_params_provided:
                # Complete replacement - clear override and set new values
                global _motivation_config_override
                _motivation_config_override = {}

            # Update provided values
            if config.threshold is not None:
                value = max(0.1, min(10.0, config.threshold))
                drives_config.threshold = value
                _motivation_config_override["threshold"] = value
            if config.boredom_rate is not None:
                value = max(0.0, min(0.1, config.boredom_rate))
                drives_config.boredom_rate = value
                _motivation_config_override["boredom_rate"] = value
            if config.curiosity_decay is not None:
                value = max(0.0, min(0.1, config.curiosity_decay))
                drives_config.curiosity_decay = value
                _motivation_config_override["curiosity_decay"] = value
            if config.tiredness_decay is not None:
                value = max(0.0, min(0.1, config.tiredness_decay))
                drives_config.tiredness_decay = value
                _motivation_config_override["tiredness_decay"] = value
            if config.satisfaction_decay is not None:
                value = max(0.0, min(0.1, config.satisfaction_decay))
                drives_config.satisfaction_decay = value
                _motivation_config_override["satisfaction_decay"] = value

            return {
                "success": True,
                "message": "Motivation configuration updated",
                "impetus": round(motivation.impetus(), 4),
                "should_research": motivation.should_research(),
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")

    except Exception as e:
        logger.error(f"Error updating motivation config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")


@router.post("/simulate-research-completion")
async def simulate_research_completion(
    request: Request,
    quality_score: float = 0.7,
):
    """Debug endpoint to simulate research completion with specified quality."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            researcher = request.app.state.autonomous_researcher

            old_state = {
                "boredom": researcher.motivation.boredom,
                "curiosity": researcher.motivation.curiosity,
                "tiredness": researcher.motivation.tiredness,
                "satisfaction": researcher.motivation.satisfaction,
            }

            researcher.motivation.on_research_completed(quality_score)

            new_state = {
                "boredom": researcher.motivation.boredom,
                "curiosity": researcher.motivation.curiosity,
                "tiredness": researcher.motivation.tiredness,
                "satisfaction": researcher.motivation.satisfaction,
            }

            return {
                "success": True,
                "message": f"Research completion simulated with quality {quality_score}",
                "quality_score": quality_score,
                "old_state": old_state,
                "new_state": new_state,
                "impetus": round(researcher.motivation.impetus(), 4),
                "should_research": researcher.motivation.should_research(),
            }
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")

    except Exception as e:
        logger.error(f"Error simulating research completion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error simulating research completion: {str(e)}")


@router.post("/trigger/{user_id}")
async def trigger_research_for_user(
    request: Request,
    user_id: str,
):
    """Manually trigger research for a specific user (for testing/debugging)."""
    try:
        if hasattr(request.app.state, "autonomous_researcher"):
            result = await request.app.state.autonomous_researcher.trigger_research_for_user(user_id)
            return result
        else:
            raise HTTPException(status_code=503, detail="Autonomous researcher not available")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering research for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error triggering research: {str(e)}")


@router.post("/control/start")
async def start_research_engine(
    request: Request,
):
    """Start the autonomous research engine."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            # Enable and start
            request.app.state.autonomous_researcher.enable()
            await request.app.state.autonomous_researcher.start()
            return {
                "success": True,
                "message": "Autonomous research engine started successfully",
                "status": request.app.state.autonomous_researcher.get_status(),
            }
        else:
            # Try to initialize if not available
            try:
                logger.info("🔬 Re-initializing Autonomous Research Engine...")
                request.app.state.autonomous_researcher = initialize_autonomous_researcher(
                    profile_manager, research_manager, _motivation_config_override
                )
                request.app.state.autonomous_researcher.enable()
                await request.app.state.autonomous_researcher.start()
                logger.info("🔬 Autonomous Research Engine re-initialized and started successfully")
                return {
                    "success": True,
                    "message": "Autonomous research engine initialized and started successfully",
                    "status": request.app.state.autonomous_researcher.get_status(),
                }
            except Exception as e:
                logger.error(f"🔬 Failed to initialize/start Autonomous Research Engine: {str(e)}", exc_info=True)
                raise HTTPException(status_code=503, detail=f"Failed to start research engine: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting research engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting research engine: {str(e)}")


@router.post("/control/stop")
async def stop_research_engine(
    request: Request,
):
    """Stop the autonomous research engine."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            # Stop and disable
            await request.app.state.autonomous_researcher.stop()
            request.app.state.autonomous_researcher.disable()
            return {
                "success": True,
                "message": "Autonomous research engine stopped successfully",
                "status": request.app.state.autonomous_researcher.get_status(),
            }
        else:
            return {
                "success": True,
                "message": "Autonomous research engine was not running",
                "status": {"enabled": False, "running": False, "error": "Research engine not initialized"},
            }

    except Exception as e:
        logger.error(f"Error stopping research engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error stopping research engine: {str(e)}")


@router.post("/control/restart")
async def restart_research_engine(
    request: Request,
):
    """Restart the autonomous research engine."""
    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            # Stop first
            await request.app.state.autonomous_researcher.stop()
            # Then enable and start again
            request.app.state.autonomous_researcher.enable()
            await request.app.state.autonomous_researcher.start()
            return {
                "success": True,
                "message": "Autonomous research engine restarted successfully",
                "status": request.app.state.autonomous_researcher.get_status(),
            }
        else:
            # Try to initialize if not available
            try:
                logger.info("🔬 Initializing Autonomous Research Engine for restart...")
                request.app.state.autonomous_researcher = initialize_autonomous_researcher(
                    profile_manager, research_manager, _motivation_config_override
                )
                request.app.state.autonomous_researcher.enable()
                await request.app.state.autonomous_researcher.start()
                logger.info("🔬 Autonomous Research Engine initialized and started successfully")
                return {
                    "success": True,
                    "message": "Autonomous research engine initialized and started successfully",
                    "status": request.app.state.autonomous_researcher.get_status(),
                }
            except Exception as e:
                logger.error(f"🔬 Failed to initialize/restart Autonomous Research Engine: {str(e)}", exc_info=True)
                raise HTTPException(status_code=503, detail=f"Failed to restart research engine: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting research engine: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error restarting research engine: {str(e)}")
