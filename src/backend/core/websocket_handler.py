"""
WebSocket handler for streaming audio transcription.
"""
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
from typing import Optional
import json

from core.whisper_model import WhisperModel


class TranscriptionWebSocket:
    """
    WebSocket handler for real-time audio transcription.
    
    Handles WebSocket connections, receives audio chunks from frontend,
    and sends back transcribed text continuously.
    """
    
    def __init__(self, whisper_model: WhisperModel):
        """
        Initialize WebSocket handler.
        
        Args:
            whisper_model: Instance of WhisperModel for transcription
        """
        self.whisper_model = whisper_model
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection to accept
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def handle_transcription(self, websocket: WebSocket):
        """
        Main handler for WebSocket transcription session.
        
        Receives audio chunks, transcribes them, and sends back results.
        
        Args:
            websocket: Active WebSocket connection
        """
        await self.connect(websocket)
        
        try:
            # Send initial connection confirmation
            await websocket.send_json({
                "type": "connection",
                "status": "connected",
                "message": "Ready for audio streaming"
            })
            
            # Reset model buffer for new session
            self.whisper_model.reset_buffer()
            
            while True:
                # Receive data from client
                data = await websocket.receive()
                
                # Handle different message types
                if "bytes" in data:
                    # Binary audio data
                    audio_chunk = data["bytes"]
                    await self._process_audio_chunk(websocket, audio_chunk, finalize=False)
                
                elif "text" in data:
                    # Text commands (JSON)
                    message = json.loads(data["text"])
                    await self._handle_command(websocket, message)
        
        except WebSocketDisconnect:
            logger.info("Client disconnected normally")
            self.disconnect(websocket)
        
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
            except:
                pass
            self.disconnect(websocket)
    
    async def _process_audio_chunk(
        self,
        websocket: WebSocket,
        audio_chunk: bytes,
        finalize: bool = False
    ):
        """
        Process an audio chunk and send transcription.
        
        Args:
            websocket: WebSocket to send results to
            audio_chunk: Audio data in bytes
            finalize: Whether this is the final chunk
        """
        try:
            if not finalize:
                # Just acknowledge receipt during recording
                await websocket.send_json({
                    "type": "chunk_received",
                    "buffer_size": len(self.whisper_model.audio_buffer),
                    "chunk_count": self.whisper_model.chunk_count
                })
            else:
                # Send processing status when finalizing
                await websocket.send_json({
                    "type": "processing",
                    "status": "transcribing",
                    "message": "Processing complete audio..."
                })
            
            # Transcribe using streaming method
            async for text in self.whisper_model.transcribe_stream(
                audio_chunk,
                finalize=finalize
            ):
                if text.strip():
                    # Send transcribed text back to client
                    await websocket.send_json({
                        "type": "transcription",
                        "text": text,
                        "is_final": finalize
                    })
                    logger.info(f"Sent transcription: {text[:50]}...")
        
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"Transcription error: {str(e)}"
            })
    
    async def _handle_command(self, websocket: WebSocket, message: dict):
        """
        Handle text commands from client.
        
        Args:
            websocket: WebSocket connection
            message: Command message as dict
        """
        command = message.get("command")
        
        if command == "finalize":
            # Finalize current audio buffer
            logger.info("Finalizing transcription")
            await self._process_audio_chunk(
                websocket,
                b"",  # Empty chunk
                finalize=True
            )
            await websocket.send_json({
                "type": "finalized",
                "message": "Transcription finalized"
            })
        
        elif command == "reset":
            # Reset audio buffer
            self.whisper_model.reset_buffer()
            await websocket.send_json({
                "type": "reset",
                "message": "Buffer reset"
            })
            logger.info("Buffer reset by client command")
        
        elif command == "ping":
            # Health check
            await websocket.send_json({
                "type": "pong",
                "message": "alive"
            })
        
        else:
            logger.warning(f"Unknown command: {command}")
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown command: {command}"
            })
    
    async def broadcast(self, message: dict):
        """
        Send a message to all connected clients.
        
        Args:
            message: Message to broadcast
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
