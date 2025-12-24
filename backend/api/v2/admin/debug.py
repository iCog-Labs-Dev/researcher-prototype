from fastapi import APIRouter, Request, HTTPException, Response, status

from dependencies import (
    profile_manager,
    research_manager,
    _motivation_config_override,
)
import config
from schemas.schemas import MotivationConfigUpdate
from services.autonomous_research_engine import initialize_autonomous_researcher
from services.logging_config import get_logger

router = APIRouter(prefix="/debug")

logger = get_logger(__name__)


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


@router.post("/expand", deprecated=True, description="Deprecated: Zep integration disabled")
async def debug_expand_topics():
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/active-topics", deprecated=True, description="Deprecated: Don't use on frontend")
async def get_debug_active_topics():
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


# Back-compat aliases used by tests
@router.get("/config/override")
async def get_config_override_alias():
    return {"success": True, "override": _motivation_config_override}


@router.delete("/config/override")
async def clear_config_override_alias():
    global _motivation_config_override
    _motivation_config_override = {}
    return {"success": True, "message": "Cleared config override"}


@router.get("/motivation", deprecated=True, description="Deprecated: v2/research/status endpoint provides the information in motivation_system")
async def get_motivation_status():
    """Debug endpoint to check motivation system status."""

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/adjust-drives", deprecated=True, description="Deprecated: Don't use on frontend")
async def adjust_motivation_drives():
    """Debug endpoint to manually set motivation drive values for testing."""

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# need attention: there is work with researcher.motivation, which no longer exists
@router.post("/update-config")
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


@router.post("/simulate-research-completion", deprecated=True, description="Deprecated: Don't use on frontend")
async def simulate_research_completion():
    """Debug endpoint to simulate research completion with specified quality."""

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/trigger/{user_id}")
async def trigger_research_for_user(
    request: Request,
    user_id: str
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
