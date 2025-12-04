"""
Graph API endpoints for managing knowledge graphs.
"""

from fastapi import APIRouter, Request, Depends, HTTPException

from dependencies import inject_user_id
from storage.zep_manager import ZepManager
from services.logging_config import get_logger
from schemas.graph import GraphIn, GraphOut

logger = get_logger(__name__)

router = APIRouter(prefix="/graph", tags=["v2/graph"], dependencies=[Depends(inject_user_id)])


@router.post("/fetch", response_model=GraphOut)
async def fetch_graph_data(
    request: Request,
    body: GraphIn,
) -> GraphOut:
    """
    Fetch graph data from Zep for visualization.
    
    Args:
        body: GraphIn containing type and id
        
    Returns:
        GraphOut containing triplets for visualization
    """

    user_id = str(request.state.user_id)

    try:
        # Log the body
        logger.info(f"Fetching graph data for {body.type}: {body.id}")
        
        # Initialize ZepManager
        zep_manager = ZepManager()
        
        if not zep_manager.is_enabled():
            logger.warning("ZepManager is not enabled")
            return GraphOut(triplets=[])
        
        # For user graphs, validate that the user is requesting their own data
        # or has appropriate permissions (could be extended for admin access)
        if body.type == "user" and body.id != user_id:
            logger.warning(f"User {user_id} attempted to access graph for user {body.id}")
            raise HTTPException(
                status_code=403,
                detail="You can only view your own knowledge graph"
            )
        
        # Currently only support user graphs (groups not implemented yet)
        if body.type != "user":
            raise HTTPException(
                status_code=400,
                detail="Only user graphs are currently supported"
            )
        
        # Fetch all nodes and edges for the user using the proper API methods
        logger.debug(f"Fetching nodes and edges for user {body.id}")
        
        # Use Promise.all equivalent - run both fetches concurrently
        import asyncio
        nodes_task = zep_manager.get_all_nodes_by_user_id(body.id)
        edges_task = zep_manager.get_all_edges_by_user_id(body.id)
        
        nodes, edges = await asyncio.gather(nodes_task, edges_task)
        
        logger.debug(f"Retrieved {len(nodes)} nodes and {len(edges)} edges for user {body.id}")
        
        # Check if we got any data
        if not nodes and not edges:
            logger.info(f"No graph data found for user {body.id}")
            return GraphOut(triplets=[])
        
        # Create triplets from nodes and edges
        triplets = zep_manager.create_triplets(edges, nodes)
        
        logger.info(f"Successfully created {len(triplets)} triplets for user {body.id}")
        
        return GraphOut(triplets=triplets)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching graph for {body.type} {body.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch graph data: {str(e)}")
