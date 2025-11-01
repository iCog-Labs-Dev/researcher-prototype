from fastapi import APIRouter, Request, Depends, HTTPException, Query
from typing import Optional

from dependencies import (
    inject_user_id,
    research_manager,
    zep_manager,
)
from schemas.schemas import BookmarkUpdate
from services.logging_config import get_logger

router = APIRouter(prefix="/research", tags=["v2/research"], dependencies=[Depends(inject_user_id)])

logger = get_logger(__name__)


@router.get("")
async def get_research_findings(
    request: Request,
    topic_name: Optional[str] = Query(None, description="Filter by topic name"),
    unread_only: bool = Query(False, description="Only return unread findings"),
):
    """Get research findings for a user, optionally filtered by topic or read status."""

    user_id = str(request.state.user_id)

    try:
        # Use the new API method from research_manager
        findings = research_manager.get_research_findings_for_api(user_id, topic_name, unread_only)

        return {
            "success": True,
            "user_id": user_id,
            "total_findings": len(findings),
            "filters": {"topic_name": topic_name, "unread_only": unread_only},
            "findings": findings,
        }

    except Exception as e:
        logger.error(f"Error getting research findings for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting research findings: {str(e)}")


@router.post("/{finding_id}/mark_read")
async def mark_research_finding_read(
    request: Request,
    finding_id: str,
):
    """Mark a research finding as read."""

    user_id = str(request.state.user_id)

    try:
        success = research_manager.mark_finding_as_read(user_id, finding_id)

        if not success:
            raise HTTPException(status_code=404, detail="Finding not found")

        return {"success": True, "message": f"Marked finding {finding_id} as read", "finding_id": finding_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking finding as read for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error marking finding as read: {str(e)}")


@router.post("/{finding_id}/integrate")
async def integrate_research_finding(
    request: Request,
    finding_id: str,
):
    """Integrate a research finding into the knowledge graph."""

    user_id = str(request.state.user_id)

    try:
        # First get the finding to make sure it exists and get its content
        findings = research_manager.get_research_findings_for_api(user_id, None, False)
        finding = None
        
        for f in findings:
            if f.get("finding_id") == finding_id:
                finding = f
                break
        
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")
            
        if finding.get("integrated"):
            return {
                "success": True, 
                "message": "Finding is already integrated",
                "finding_id": finding_id,
                "was_already_integrated": True
            }

        # Submit key insights to Zep for automatic entity/relationship extraction
        key_insights = finding.get("key_insights", [])
        if not key_insights:
            # If no key insights, use the findings summary as content
            key_insights = [finding.get("findings_summary", "No summary available")]
        
        try:
            # Get topic metadata for enhanced context
            topic_name = finding.get("topic_name", "Unknown Topic")
            topic_info = research_manager.get_topic_info_by_name(user_id, topic_name)
            
            topic_description = None
            topic_context = None
            if topic_info:
                topic_description = topic_info.get("description")
                topic_context = topic_info.get("conversation_context")
            
            # Use Zep's content submission for entity extraction
            zep_success = await zep_manager.store_research_finding(
                user_id=user_id,
                topic_name=topic_name,
                key_insights=key_insights,
                finding_id=finding_id,
                topic_description=topic_description,
                topic_context=topic_context
            )
            
            if not zep_success:
                logger.warning(f"Failed to store research finding in Zep for finding {finding_id}")
        
        except Exception as e:
            logger.error(f"Error submitting content to Zep: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error integrating with knowledge graph: {str(e)}")

        # Mark the finding as integrated
        integration_success = research_manager.mark_finding_as_integrated(user_id, finding_id)
        
        if not integration_success:
            logger.warning(f"Added to knowledge graph but failed to mark finding {finding_id} as integrated")
        
        return {
            "success": True,
            "message": f"Successfully submitted finding to knowledge graph for entity extraction",
            "finding_id": finding_id,
            "topic_name": finding.get("topic_name"),
            "key_insights_submitted": len(key_insights),
            "zep_integration_success": zep_success,
            "integration_marked": integration_success,
            "was_already_integrated": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error integrating finding {finding_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error integrating finding: {str(e)}")


@router.post("/{finding_id}/bookmark")
async def bookmark_research_finding(
    request: Request,
    finding_id: str,
    update: BookmarkUpdate,
):
    """Bookmark or unbookmark a specific research finding."""

    user_id = str(request.state.user_id)

    try:
        success = research_manager.mark_finding_bookmarked(user_id, finding_id, update.bookmarked)
        if not success:
            raise HTTPException(status_code=404, detail="Finding not found")

        return {
            "success": True,
            "message": ("Bookmarked" if update.bookmarked else "Unbookmarked") + f" finding {finding_id}",
            "finding_id": finding_id,
            "bookmarked": update.bookmarked,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bookmark for finding {finding_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating bookmark: {str(e)}")


@router.delete("/{finding_id}")
async def delete_research_finding(
    request: Request,
    finding_id: str,
):
    """Delete a specific research finding."""

    user_id = str(request.state.user_id)

    try:
        result = research_manager.delete_research_finding(user_id, finding_id)

        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "message": "Successfully deleted research finding",
            "deleted_finding": result["deleted_finding"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting research finding {finding_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting research finding: {str(e)}")


@router.delete("/topic/{topic_name}")
async def delete_all_topic_findings(
    request: Request,
    topic_name: str,
):
    """Delete all research findings for a specific topic."""

    user_id = str(request.state.user_id)

    try:
        result = research_manager.delete_all_topic_findings(user_id, topic_name)

        if not result["success"]:
            if "not found" in result["error"]:
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "message": f"Successfully deleted all findings for topic '{topic_name}'",
            "topic_name": result["topic_name"],
            "findings_deleted": result["findings_deleted"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting all findings for topic '{topic_name}' for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting topic findings: {str(e)}")
