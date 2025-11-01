"""
WebSocket API endpoints for real-time notifications.
"""
import logging
from fastapi import APIRouter, Request, Depends, WebSocket, WebSocketDisconnect, Header, Query
from typing import Optional

from dependencies import get_session, inject_user_id, resolve_ws_user
from exceptions import AuthError
from services.notification_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notification", tags=["v2/notifications"])


@router.websocket("/ws")
async def websocket_notifications(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None, alias="token")
):
    """
    WebSocket endpoint for real-time notifications.
    
    Client should connect with token as query parameter:
    ws://localhost:8000/ws/notifications?token=XXXX
    """
    if not token:
        await websocket.close(code=1008, reason="Missing token parameter")
        return

    async with get_session() as session:
        try:
            user_id = await resolve_ws_user(token, session)
        except AuthError as e:
            await websocket.close(code=1008, reason=str(e))
            return
        except Exception:
            await websocket.close(code=1008, reason="Auth failed")
            return

        await websocket.accept()

        try:
            await connection_manager.connect(websocket, user_id)

            # Send initial connection confirmation
            await websocket.send_text('{"type": "connection_established", "data": {"user_id": "' + user_id + '"}}')

            # Keep connection alive and handle incoming messages
            while True:
                try:
                    # Wait for any message from client (could be ping/heartbeat)
                    data = await websocket.receive_text()
                    logger.debug(f"📡 Received message from user {user_id}: {data}")

                    # Echo back as heartbeat response
                    await websocket.send_text('{"type": "heartbeat", "data": {"status": "alive"}}')

                except WebSocketDisconnect:
                    logger.info(f"📡 User {user_id} disconnected normally")
                    break
                except Exception as e:
                    logger.error(f"📡 Error handling message from user {user_id}: {e}")
                    break

        except WebSocketDisconnect:
            logger.info(f"📡 User {user_id} disconnected during setup")
        except Exception as e:
            logger.error(f"📡 Error in websocket connection for user {user_id}: {e}")
        finally:
            connection_manager.disconnect(websocket, user_id)


@router.get("/status", dependencies=[Depends(inject_user_id)])
async def get_notification_status(
    request: Request,
):
    """Get notification system status for debugging."""

    user_id = str(request.state.user_id)

    return {
        "total_connections": connection_manager.get_connection_count(),
        "user_connections": connection_manager.get_connection_count(user_id),
        "active_users": len(connection_manager.active_connections)
    }
