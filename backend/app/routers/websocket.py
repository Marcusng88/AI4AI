"""WebSocket router for real-time browser viewer communication."""

import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from fastapi.routing import APIRouter
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Store active WebSocket connections by session ID
active_connections: Dict[str, Set[WebSocket]] = {}

class ConnectionManager:
    """Manages WebSocket connections for browser viewer."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept a WebSocket connection and add to active connections."""
        try:
            await websocket.accept()
            
            if session_id not in self.active_connections:
                self.active_connections[session_id] = set()
            
            self.active_connections[session_id].add(websocket)
            logger.info(f"WebSocket connected for session {session_id}. Total connections: {len(self.active_connections[session_id])}")
            
            # Send initial connection confirmation
            await self.send_personal_message({
                "type": "browser_viewer_connected",
                "message": "Connected to browser viewer",
                "session_id": session_id,
                "timestamp": asyncio.get_event_loop().time()
            }, websocket)
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection for session {session_id}: {e}")
            raise
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def send_to_session(self, message: dict, session_id: str):
        """Send a message to all connections in a session."""
        if session_id in self.active_connections:
            disconnected = set()
            for websocket in self.active_connections[session_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to session {session_id}: {e}")
                    disconnected.add(websocket)
            
            # Remove disconnected websockets
            for websocket in disconnected:
                self.active_connections[session_id].discard(websocket)
    
    async def broadcast_browser_status(self, session_id: str, status: dict):
        """Broadcast browser status to all connections in a session."""
        message = {
            "type": "browser_status",
            "status": status,
            "session_id": session_id
        }
        await self.send_to_session(message, session_id)
    
    async def broadcast_browser_viewer_ready(self, session_id: str, live_url: str, browser_connected: bool, hyperbrowser_session_active: bool):
        """Broadcast browser viewer ready event."""
        message = {
            "type": "browser_viewer_ready",
            "live_url": live_url,
            "browser_connected": browser_connected,
            "hyperbrowser_session_active": hyperbrowser_session_active,
            "session_id": session_id
        }
        await self.send_to_session(message, session_id)
    
    async def broadcast_live_view_available(self, session_id: str, live_view_url: str, presigned_url: str = None):
        """Broadcast that live view streaming is available."""
        message = {
            "type": "live_view_available",
            "session_id": session_id,
            "live_view_url": live_view_url,
            "presigned_url": presigned_url,
            "streaming_enabled": True
        }
        await self.send_to_session(message, session_id)
    
    async def broadcast_browser_session_created(self, session_id: str, ws_url: str, headers: dict):
        """Broadcast that a browser session has been created."""
        message = {
            "type": "browser_session_created",
            "session_id": session_id,
            "ws_url": ws_url,
            "headers": headers,
            "status": "active"
        }
        await self.send_to_session(message, session_id)
    
    async def broadcast_control_event(self, session_id: str, event_type: str, user_id: str = None):
        """Broadcast control events (take_control, release_control)."""
        message = {
            "type": event_type,
            "session_id": session_id,
            "user_id": user_id
        }
        await self.send_to_session(message, session_id)

# Global connection manager instance
manager = ConnectionManager()

@router.websocket("/ws/browser-viewer/{session_id}")
async def websocket_browser_viewer(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for browser viewer communication."""
    try:
        await manager.connect(websocket, session_id)
        
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "request_browser_status":
                    # Request current browser status
                    # This would typically query the automation agent for current status
                    # For now, return a default status - this should be enhanced to check actual automation state
                    await manager.send_personal_message({
                        "type": "browser_status",
                        "status": {
                            "status": "connected",
                            "browser_connected": False,
                            "hyperbrowser_session_active": False,
                            "live_url": None
                        },
                        "session_id": session_id
                    }, websocket)
                
                elif message.get("type") == "take_control":
                    # Handle user taking control
                    await manager.broadcast_control_event(session_id, "control_taken")
                    logger.info(f"User took control for session {session_id}")
                
                elif message.get("type") == "release_control":
                    # Handle user releasing control
                    await manager.broadcast_control_event(session_id, "control_released")
                    logger.info(f"User released control for session {session_id}")
                
                else:
                    logger.warning(f"Unknown message type received: {message.get('type')}")
            
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received from session {session_id}: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid message format",
                    "session_id": session_id
                }, websocket)
            except Exception as e:
                logger.error(f"Error processing message for session {session_id}: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"Error processing message: {str(e)}",
                    "session_id": session_id
                }, websocket)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(websocket, session_id)
    finally:
        # Ensure cleanup
        manager.disconnect(websocket, session_id)

# Utility functions for other parts of the application to use
async def notify_browser_status(session_id: str, status: dict):
    """Notify all connected clients about browser status changes."""
    await manager.broadcast_browser_status(session_id, status)

async def notify_browser_viewer_ready(session_id: str, live_url: str, browser_connected: bool, hyperbrowser_session_active: bool):
    """Notify all connected clients that browser viewer is ready."""
    await manager.broadcast_browser_viewer_ready(session_id, live_url, browser_connected, hyperbrowser_session_active)

async def notify_control_event(session_id: str, event_type: str, user_id: str = None):
    """Notify all connected clients about control events."""
    await manager.broadcast_control_event(session_id, event_type, user_id)
