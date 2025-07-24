"""
WebSocket handlers for real-time speech processing and debugging
"""
import asyncio
import json
import logging
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import uuid

from .speech_processing import speech_debugger, speech_processor, ProcessingStage, DebugEvent

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.debug_connections: Dict[str, WebSocket] = {}
        
    async def connect_audio(self, websocket: WebSocket, session_id: str):
        """Connect audio processing WebSocket"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Audio WebSocket connected: {session_id}")
        
    async def connect_debug(self, websocket: WebSocket, client_id: str):
        """Connect debug console WebSocket"""
        await websocket.accept()
        self.debug_connections[client_id] = websocket
        logger.info(f"Debug WebSocket connected: {client_id}")
        
    def disconnect_audio(self, session_id: str):
        """Disconnect audio WebSocket"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"Audio WebSocket disconnected: {session_id}")
            
    def disconnect_debug(self, client_id: str):
        """Disconnect debug WebSocket"""
        if client_id in self.debug_connections:
            del self.debug_connections[client_id]
            logger.info(f"Debug WebSocket disconnected: {client_id}")
            
    async def send_audio_response(self, session_id: str, data: bytes):
        """Send audio response to client"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_bytes(data)
            
    async def broadcast_debug_event(self, event: Dict[str, Any]):
        """Broadcast debug event to all debug consoles"""
        disconnected = []
        for client_id, websocket in self.debug_connections.items():
            try:
                await websocket.send_json(event)
            except Exception as e:
                logger.error(f"Error sending to debug client {client_id}: {e}")
                disconnected.append(client_id)
                
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect_debug(client_id)

# Global connection manager
connection_manager = ConnectionManager()

async def handle_audio_websocket(websocket: WebSocket):
    """Handle audio streaming WebSocket connection"""
    session_id = str(uuid.uuid4())
    await connection_manager.connect_audio(websocket, session_id)
    
    # Log connection event
    await speech_debugger.log_event(DebugEvent(
        stage=ProcessingStage.AUDIO_CAPTURE,
        data={
            "action": "websocket_connected",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        },
        session_id=session_id
    ))
    
    try:
        while True:
            # Receive audio data
            data = await websocket.receive_bytes()
            
            # Log raw audio received
            await speech_debugger.log_event(DebugEvent(
                stage=ProcessingStage.AUDIO_CAPTURE,
                data={
                    "action": "audio_received",
                    "size": len(data),
                    "type": "binary"
                },
                session_id=session_id
            ))
            
            # Process audio asynchronously
            asyncio.create_task(process_audio_data(data, session_id))
            
    except WebSocketDisconnect:
        connection_manager.disconnect_audio(session_id)
        await speech_debugger.log_event(DebugEvent(
            stage=ProcessingStage.AUDIO_CAPTURE,
            data={
                "action": "websocket_disconnected",
                "reason": "client_disconnect"
            },
            session_id=session_id
        ))
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect_audio(session_id)
        await speech_debugger.log_event(DebugEvent(
            stage=ProcessingStage.AUDIO_CAPTURE,
            data={
                "action": "websocket_error",
                "error": str(e)
            },
            session_id=session_id
        ))

async def handle_debug_websocket(websocket: WebSocket):
    """Handle debug console WebSocket connection"""
    client_id = str(uuid.uuid4())
    await connection_manager.connect_debug(websocket, client_id)
    
    # Subscribe to debug events
    event_queue = speech_debugger.subscribe()
    
    # Send initial state
    await websocket.send_json({
        "type": "initial_state",
        "active_sessions": list(speech_debugger.active_sessions.keys()),
        "timestamp": datetime.utcnow().isoformat()
    })
    
    try:
        # Create tasks for receiving and sending
        receive_task = asyncio.create_task(receive_debug_commands(websocket, client_id))
        send_task = asyncio.create_task(send_debug_events(websocket, event_queue))
        
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            {receive_task, send_task},
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            
    except WebSocketDisconnect:
        logger.info(f"Debug client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Debug WebSocket error: {e}")
    finally:
        connection_manager.disconnect_debug(client_id)
        speech_debugger.unsubscribe(event_queue)

async def receive_debug_commands(websocket: WebSocket, client_id: str):
    """Receive commands from debug console"""
    while True:
        data = await websocket.receive_json()
        command = data.get("command")
        
        if command == "get_session_events":
            session_id = data.get("session_id")
            events = speech_debugger.get_session_events(session_id)
            await websocket.send_json({
                "type": "session_events",
                "session_id": session_id,
                "events": events
            })
        elif command == "clear_events":
            speech_debugger.events.clear()
            await websocket.send_json({
                "type": "events_cleared",
                "timestamp": datetime.utcnow().isoformat()
            })
        elif command == "get_stats":
            stats = {
                "total_events": len(speech_debugger.events),
                "active_sessions": len(speech_debugger.active_sessions),
                "total_subscribers": len(speech_debugger.subscribers)
            }
            await websocket.send_json({
                "type": "stats",
                "data": stats
            })

async def send_debug_events(websocket: WebSocket, event_queue: asyncio.Queue):
    """Send debug events to console"""
    while True:
        event = await event_queue.get()
        await websocket.send_json({
            "type": "debug_event",
            "event": event
        })

async def process_audio_data(audio_data: bytes, session_id: str):
    """Process audio data and send response"""
    try:
        # Create a mock stream reader for the audio data
        stream = asyncio.StreamReader()
        stream.feed_data(audio_data)
        stream.feed_eof()
        
        # Process through speech pipeline
        await speech_processor.process_audio_stream(stream, session_id)
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        await speech_debugger.log_event(DebugEvent(
            stage=ProcessingStage.AUDIO_CAPTURE,
            data={
                "action": "processing_error",
                "error": str(e)
            },
            session_id=session_id
        ))