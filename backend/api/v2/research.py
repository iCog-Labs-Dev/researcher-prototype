import time
from uuid import UUID
from typing import Optional, Annotated
from fastapi import APIRouter, Request, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

import config
from db import get_session
from services.logging_config import get_logger
from dependencies import (
    profile_manager,
    inject_user_id,
    research_manager,
    _motivation_config_override,
)
from schemas.research import (
    BookmarkUpdateInOut,
    MotivationConfigUpdate,
    ExpansionIn,
    ResearchFindingsOut,
)
from services.autonomous_research_engine import initialize_autonomous_researcher
from services.research import ResearchService

router = APIRouter(prefix="/research", tags=["v2/research"], dependencies=[Depends(inject_user_id)])

logger = get_logger(__name__)


# need attention: there was a user_id parameter. is it correct?
@router.get("/findings", response_model=ResearchFindingsOut)
async def get_research_findings(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    topic_id: Optional[UUID] = Query(None, description="Filter by topic ID"),
    unread_only: bool = Query(False, description="Only return unread findings"),
) -> ResearchFindingsOut:
    user_id = str(request.state.user_id)

    service = ResearchService()
    findings = await service.get_findings(session, user_id, topic_id, unread_only)

    return ResearchFindingsOut(
        total_findings=len(findings),
        findings=findings
    )


@router.post("/findings/{finding_id}/mark_read")
async def mark_research_finding_read(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    finding_id: UUID,
):
    user_id = str(request.state.user_id)

    service = ResearchService()
    await service.mark_finding_as_read(session, user_id, finding_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/findings/{finding_id}/integrate", deprecated=True, description="Deprecated: Zep integration disabled")
async def integrate_research_finding(
    finding_id: UUID,
):
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/findings/{finding_id}/bookmark", response_model=BookmarkUpdateInOut)
async def bookmark_research_finding(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    finding_id: UUID,
    body: BookmarkUpdateInOut,
) -> BookmarkUpdateInOut:
    user_id = str(request.state.user_id)

    service = ResearchService()
    result = await service.mark_finding_bookmarked(session, user_id, finding_id, body.bookmarked)

    return BookmarkUpdateInOut(bookmarked=result)


@router.delete("/findings/{finding_id}")
async def delete_research_finding(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    finding_id: UUID,
):
    user_id = str(request.state.user_id)

    service = ResearchService()
    await service.delete_research_finding(session, user_id, finding_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/findings/topic/{topic_id}")
async def delete_all_topic_findings(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    topic_id: UUID,
):
    user_id = str(request.state.user_id)

    service = ResearchService()
    await service.delete_all_topic_findings(session, user_id, topic_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/status")
async def get_research_engine_status(
    request: Request,
):
    """Get the current status of the autonomous research engine."""

    try:
        if hasattr(request.app.state, "autonomous_researcher"):
            status = request.app.state.autonomous_researcher.get_status()
            return status
        else:
            return {"enabled": False, "running": False, "error": "Autonomous researcher not initialized"}

    except Exception as e:
        logger.error(f"Error getting research engine status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting research status: {str(e)}")


@router.post("/debug/expand", deprecated=True, description="Deprecated: Zep integration disabled")
async def debug_expand_topics(
    body: ExpansionIn
):
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/debug/active-topics", deprecated=True, description="Deprecated: Don't use on frontend")
async def get_debug_active_topics():
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/debug/config-override")
async def get_config_override():
    """Debug endpoint to see what's in the config override."""

    return {"override": _motivation_config_override}


@router.post("/debug/clear-override")
async def clear_config_override():
    """Debug endpoint to clear the config override."""

    global _motivation_config_override
    _motivation_config_override = {}
    return {"success": True, "message": "Config override cleared"}


# Back-compat aliases used by tests
@router.get("/debug/config/override")
async def get_config_override_alias():
    return {"success": True, "override": _motivation_config_override}


@router.delete("/debug/config/override")
async def clear_config_override_alias():
    global _motivation_config_override
    _motivation_config_override = {}
    return {"success": True, "message": "Cleared config override"}


# need attention: there is work with researcher.motivation, which no longer exists
@router.get("/debug/motivation")
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


# need attention: there is work with researcher.motivation, which no longer exists (and on_user_activity, etc)
@router.post("/debug/trigger-user-activity")
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


# need attention: there is work with researcher.motivation, which no longer exists
@router.post("/debug/adjust-drives")
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


# need attention: there is work with researcher.motivation, which no longer exists
@router.post("/debug/update-config")
async def update_motivation_config(
    request: Request,
    body: MotivationConfigUpdate,
):
    """Debug endpoint to update motivation system configuration parameters."""

    try:
        if hasattr(request.app.state, "autonomous_researcher") and request.app.state.autonomous_researcher:
            researcher = request.app.state.autonomous_researcher
            motivation = researcher.motivation
            drives_config = motivation.drives

            # Check if this is a complete config replacement (all parameters provided)
            all_params_provided = all(
                getattr(body, param) is not None
                for param in ["threshold", "boredom_rate", "curiosity_decay", "tiredness_decay", "satisfaction_decay"]
            )

            if all_params_provided:
                # Complete replacement - clear override and set new values
                global _motivation_config_override
                _motivation_config_override = {}

            # Update provided values
            if body.threshold is not None:
                value = max(0.1, min(10.0, body.threshold))
                drives_config.threshold = value
                _motivation_config_override["threshold"] = value
            if body.boredom_rate is not None:
                value = max(0.0, min(0.1, body.boredom_rate))
                drives_config.boredom_rate = value
                _motivation_config_override["boredom_rate"] = value
            if body.curiosity_decay is not None:
                value = max(0.0, min(0.1, body.curiosity_decay))
                drives_config.curiosity_decay = value
                _motivation_config_override["curiosity_decay"] = value
            if body.tiredness_decay is not None:
                value = max(0.0, min(0.1, body.tiredness_decay))
                drives_config.tiredness_decay = value
                _motivation_config_override["tiredness_decay"] = value
            if body.satisfaction_decay is not None:
                value = max(0.0, min(0.1, body.satisfaction_decay))
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


# need attention: there is work with researcher.motivation, which no longer exists
@router.post("/debug/simulate-research-completion")
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


# need attention: there was a user_id parameter. is it correct?
@router.post("/trigger")
async def trigger_research_for_user(
    request: Request,
):
    """Manually trigger research for a specific user (for testing/debugging)."""

    user_id = str(request.state.user_id)

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
