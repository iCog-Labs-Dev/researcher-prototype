"""
WebSocket-based notification manager for real-time updates.
"""
import json
import logging
import asyncio
import time
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
from dependencies import profile_manager
import config

# SendGrid - optional
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except Exception:
    SENDGRID_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for notifications."""
    
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a WebSocket connection for a user."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"🔌 User {user_id} connected to notifications (total connections: {len(self.active_connections[user_id])})")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection for a user."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"🔌 User {user_id} disconnected from notifications")
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send a notification to all connections for a specific user."""
        if user_id not in self.active_connections:
            logger.info(f"📡 No active connections for user {user_id} (total users: {len(self.active_connections)})")
            return
        
        # Create a copy of the set to avoid modification during iteration
        connections = self.active_connections[user_id].copy()
        disconnected_connections = []
        
        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
                logger.debug(f"📡 Sent notification to user {user_id}: {message.get('type', 'unknown')}")
            except Exception as e:
                logger.warning(f"📡 Failed to send notification to user {user_id}: {e}")
                disconnected_connections.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected_connections:
            self.disconnect(connection, user_id)
    
    async def broadcast_to_all(self, message: dict):
        """Send a notification to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)
    
    def get_connection_count(self, user_id: Optional[str] = None) -> int:
        """Get the number of active connections."""
        if user_id:
            return len(self.active_connections.get(user_id, set()))
        return sum(len(connections) for connections in self.active_connections.values())


# Global connection manager instance
connection_manager = ConnectionManager()


class NotificationService:
    """Service for sending different types of notifications.

    Note: In-app WebSocket notifications are immediate by design. The
    `interaction_preferences.notification_frequency` is reserved for future
    external channels (email/SMS) and is not applied here.
    """
    
    @staticmethod
    async def notify_new_research(user_id: str, topic_id: str, result_id: str, topic_name: str = None):
        """Notify user about new research results."""
        message = {
            "type": "new_research",
            "data": {
                "topic_id": topic_id,
                "result_id": result_id,
                "topic_name": topic_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        logger.info(f"📡 NotificationService: Sending new research notification to user {user_id}")
        await connection_manager.send_to_user(user_id, message)
    
    @staticmethod
    async def notify_research_complete(user_id: str, topic_id: str, results_count: int, topic_name: str = None):
        """Notify user when a research cycle completes."""
        message = {
            "type": "research_complete",
            "data": {
                "topic_id": topic_id,
                "results_count": results_count,
                "topic_name": topic_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        # Always send in-app WebSocket notification if connected
        await connection_manager.send_to_user(user_id, message)

        # Optionally send external email notification via SendGrid
        try:
            if config.SENDGRID_ENABLED and SENDGRID_AVAILABLE and config.SENDGRID_API_KEY:
                # Fetch user profile to get email & preferences
                profile = profile_manager.get_user(user_id)
                email = None
                prefs = None
                if profile:
                    email = profile.get("metadata", {}).get("email") or profile.get("email")
                    prefs = profile.get("preferences")

                # Respect user notification frequency preference if available
                notify_email = False
                if email:
                    # Default: only send for moderate/high frequency
                    if prefs and isinstance(prefs, dict):
                        freq = prefs.get("interaction_preferences", {}).get("notification_frequency", "moderate")
                    else:
                        freq = "moderate"

                    if freq in ("moderate", "high"):
                        notify_email = True

                if notify_email:
                    subject = f"Research complete: {topic_name or topic_id}"
                    plain_content = f"Your background research for '{topic_name or topic_id}' completed with {results_count} new results.\n\nVisit your dashboard to review the findings.\n\n- Researcher Prototype"
                    html_content = f"<p>Your background research for '<strong>{topic_name or topic_id}</strong>' completed with <strong>{results_count}</strong> new results.</p><p>Visit your dashboard to review the findings.</p><p>— Researcher Prototype</p>"

                    message_mail = Mail(from_email=config.SENDGRID_FROM_EMAIL, to_emails=email, subject=subject, plain_text_content=plain_content, html_content=html_content)
                    try:
                        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
                        resp = sg.send(message_mail)
                        logger.info(f"✉️ Sent research complete email to {email} (status: {resp.status_code})")
                    except Exception as e:
                        logger.warning(f"✉️ Failed to send research complete email to {email}: {e}")

        except Exception as e:
            logger.warning(f"✉️ Error while attempting external notification for user {user_id}: {e}")
    
    @staticmethod
    async def notify_system_status(status: str, details: dict = None):
        """Broadcast system status updates to all users."""
        message = {
            "type": "system_status",
            "data": {
                "status": status,
                "details": details or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        await connection_manager.broadcast_to_all(message)


# Convenience instance
notification_service = NotificationService()