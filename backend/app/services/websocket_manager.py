"""WebSocket connection manager for real-time device event notifications."""
from typing import List, Dict, Any
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasts device events."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast_event(self, event: Dict[str, Any]):
        """
        Broadcast an event to all connected WebSocket clients.

        Args:
            event: Event dictionary with type, device info, and timestamp
        """
        logger.info(f"Broadcasting event: {event.get('type')} to {len(self.active_connections)} connections")

        if not self.active_connections:
            logger.warning("No active WebSocket connections to broadcast to")
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(event)
                logger.info(f"Event sent successfully to connection")
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
