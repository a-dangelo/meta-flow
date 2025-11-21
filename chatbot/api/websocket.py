"""
WebSocket support for real-time log streaming and status updates.

Provides WebSocket endpoint for clients to receive:
- Real-time execution logs
- Status updates during workflow execution
- Final results
- Error notifications
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
from datetime import datetime
import logging
import json
import asyncio

from chatbot.api.models import (
    WSMessage,
    WSLogMessage,
    WSStatusMessage,
    WSResultMessage,
    WSErrorMessage
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== CONNECTION MANAGER ====================

class ConnectionManager:
    """
    Manages WebSocket connections for multiple sessions.

    Supports multiple clients per session for collaborative viewing.
    """

    def __init__(self):
        """Initialize connection manager."""
        # session_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Accept and register a WebSocket connection.

        Args:
            websocket: WebSocket connection
            session_id: Session identifier
        """
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = []

        self.active_connections[session_id].append(websocket)

        logger.info(
            f"WebSocket connected for session {session_id} "
            f"({len(self.active_connections[session_id])} total connections)"
        )

    def disconnect(self, websocket: WebSocket, session_id: str):
        """
        Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection
            session_id: Session identifier
        """
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)

            # Clean up empty session
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

            logger.info(
                f"WebSocket disconnected for session {session_id} "
                f"({len(self.active_connections.get(session_id, []))} remaining)"
            )

    async def send_to_session(self, session_id: str, message: dict):
        """
        Send message to all connections for a session.

        Args:
            session_id: Session identifier
            message: Message dictionary to send
        """
        if session_id not in self.active_connections:
            return

        # Send to all connections
        disconnected = []
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    f"Failed to send to connection: {e}. "
                    f"Marking for removal."
                )
                disconnected.append(connection)

        # Clean up disconnected
        for connection in disconnected:
            self.disconnect(connection, session_id)

    async def broadcast_log(self, session_id: str, content: str, level: str = "info"):
        """
        Broadcast a log message to session.

        Args:
            session_id: Session identifier
            content: Log content
            level: Log level (info, warning, error)
        """
        message = WSLogMessage(
            type="log",
            level=level,
            content=content,
            timestamp=datetime.utcnow()
        )

        await self.send_to_session(session_id, message.model_dump())

    async def broadcast_status(
        self,
        session_id: str,
        status: str,
        progress: int = None
    ):
        """
        Broadcast a status update to session.

        Args:
            session_id: Session identifier
            status: Status message
            progress: Progress percentage (0-100)
        """
        message = WSStatusMessage(
            type="status",
            status=status,
            progress=progress,
            timestamp=datetime.utcnow()
        )

        await self.send_to_session(session_id, message.model_dump())

    async def broadcast_result(
        self,
        session_id: str,
        result: dict,
        reference_id: str = None
    ):
        """
        Broadcast execution result to session.

        Args:
            session_id: Session identifier
            result: Result data
            reference_id: Reference ID for result
        """
        message = WSResultMessage(
            type="result",
            result=result,
            reference_id=reference_id,
            timestamp=datetime.utcnow()
        )

        await self.send_to_session(session_id, message.model_dump())

    async def broadcast_error(
        self,
        session_id: str,
        error: str,
        error_type: str = None
    ):
        """
        Broadcast error message to session.

        Args:
            session_id: Session identifier
            error: Error message
            error_type: Type of error
        """
        message = WSErrorMessage(
            type="error",
            error=error,
            error_type=error_type,
            timestamp=datetime.utcnow()
        )

        await self.send_to_session(session_id, message.model_dump())

    def get_connection_count(self, session_id: str) -> int:
        """
        Get number of active connections for a session.

        Args:
            session_id: Session identifier

        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(session_id, []))


# Global connection manager instance
manager = ConnectionManager()


# ==================== WEBSOCKET ENDPOINT ====================

@router.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat updates.

    Clients connect to receive:
    - Real-time execution logs
    - Status updates
    - Results
    - Errors

    URL: ws://localhost:8000/ws/chat/{session_id}

    Message Types:
        - log: {"type": "log", "content": "...", "level": "info"}
        - status: {"type": "status", "status": "executing", "progress": 50}
        - result: {"type": "result", "result": {...}, "reference_id": "REF-123"}
        - error: {"type": "error", "error": "...", "error_type": "..."}

    Args:
        websocket: WebSocket connection
        session_id: Session identifier
    """
    await manager.connect(websocket, session_id)

    try:
        # Send welcome message
        welcome = WSMessage(
            type="connected",
            content=f"Connected to session {session_id}",
            timestamp=datetime.utcnow()
        )
        await websocket.send_json(welcome.model_dump())

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()

                # Parse message
                try:
                    message = json.loads(data)
                    message_type = message.get("type")

                    # Handle different message types
                    if message_type == "ping":
                        # Respond to ping with pong
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        })

                    elif message_type == "subscribe":
                        # Client subscribing to updates (already connected)
                        await websocket.send_json({
                            "type": "subscribed",
                            "session_id": session_id,
                            "timestamp": datetime.utcnow().isoformat()
                        })

                    else:
                        logger.warning(
                            f"Unknown message type '{message_type}' "
                            f"from session {session_id}"
                        )

                except json.JSONDecodeError:
                    logger.warning(
                        f"Invalid JSON from session {session_id}: {data}"
                    )

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break

            except Exception as e:
                logger.error(
                    f"Error in WebSocket loop for session {session_id}: {e}",
                    exc_info=True
                )
                break

    finally:
        manager.disconnect(websocket, session_id)


# ==================== HELPER FUNCTIONS ====================

async def stream_execution_logs(
    session_id: str,
    logs: List[str]
):
    """
    Stream execution logs to WebSocket clients.

    Helper function to send multiple log messages.

    Args:
        session_id: Session identifier
        logs: List of log messages
    """
    for log in logs:
        await manager.broadcast_log(session_id, log)
        await asyncio.sleep(0.01)  # Small delay for readability


def get_manager() -> ConnectionManager:
    """
    Get the global connection manager.

    For use in other modules that need to broadcast messages.

    Returns:
        ConnectionManager instance
    """
    return manager
