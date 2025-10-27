from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, status

from services.prompt_manager import prompt_manager
from services.flow_analyzer import flow_analyzer
from services.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/flow")


@router.get("")
async def get_flow_summary():
    """Get summary of all LangGraph flows and their prompt usage."""

    try:
        summary = flow_analyzer.get_flow_summary()

        return {
            'success': True,
            'flow_summary': summary,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting flow summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving flow summary: {str(e)}"
        )


@router.get("/prompt-usage")
async def get_prompt_usage_map():
    """Get mapping of prompts to the nodes that use them."""

    try:
        prompt_usage = flow_analyzer.get_prompt_usage_map()

        return {
            'success': True,
            'prompt_usage': prompt_usage,
            'total_prompts': len(prompt_usage),
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting prompt usage map: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving prompt usage map: {str(e)}"
        )


@router.get("/nodes/{node_id}")
async def get_node_info(
    node_id: str
):
    """Get detailed information about a specific node including its prompt."""

    try:
        node_info = flow_analyzer.get_node_prompt_info(node_id)

        if not node_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node '{node_id}' not found"
            )

        # If the node has a prompt, get the full prompt details
        prompt_details = None
        if node_info.get('prompt'):
            prompt_name = node_info['prompt']
            prompt_details = prompt_manager.get_prompt(prompt_name)

        return {
            'success': True,
            'node_id': node_id,
            'node_info': node_info,
            'prompt_details': prompt_details,
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node info for {node_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving node information: {str(e)}"
        )


@router.post("/diagrams/generate")
async def generate_flow_diagrams(
    request: Request,
    force_regenerate: bool = False,
):
    """
    Generate flow diagrams for both main chat and research graphs.
    Uses cached diagrams if they exist unless force_regenerate is True.
    """

    admin_id = str(request.state.user_id)

    try:
        # Generate diagrams (or use cache)
        result = flow_analyzer.generate_flow_diagrams(force_regenerate=force_regenerate)

        # Save metadata for frontend consumption
        metadata_saved = flow_analyzer.save_flow_metadata()

        # Log appropriate message
        if any(diagram.get('cached', False) for diagram in result['diagrams'].values()):
            logger.info(f"Admin {admin_id} loaded cached flow diagrams")
        else:
            logger.info(f"Admin {admin_id} generated flow diagrams")

        return {
            'success': result['success'],
            'diagrams': result['diagrams'],
            'errors': result['errors'],
            'metadata_saved': metadata_saved,
            'force_regenerate': force_regenerate,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating flow diagrams: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating flow diagrams: {str(e)}"
        )


@router.get("/{graph_type}")
async def get_flow_data(
    graph_type: str
):
    """Get detailed flow data for a specific graph type (main or research)."""

    if graph_type not in ["main", "research"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Graph type must be 'main' or 'research'"
        )

    try:
        flow_data = flow_analyzer.get_flow_data(graph_type)

        return {
            'success': True,
            'graph_type': graph_type,
            'flow_data': flow_data,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting flow data for {graph_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving flow data: {str(e)}"
        )
