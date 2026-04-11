import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

# Import the new class we created
from audio.whisper_model import StreamingFasterWhisperTranscriber

class TranscriptionWebSocket:
    """
    Updated WebSocket handler for true real-time streaming.
    Uses a concurrent producer/consumer architecture.
    """
    
    def __init__(self, transcriber: StreamingFasterWhisperTranscriber):
        self.transcriber = transcriber
        self.active_connections: list[WebSocket] = []

    async def handle_transcription(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Create task references so we can cancel them manually if needed
        receive_task = asyncio.create_task(self._receive_loop(websocket))
        send_task = asyncio.create_task(self._send_loop(websocket))

        try:
            await websocket.send_json({
                "type": "connection",
                "status": "connected",
                "message": "Real-time PCM stream active"
            })

            # Wait for either the receiver (disconnect) or sender (error) to finish
            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # If we reach here, one task finished. 
            # We must cancel the other one immediately.
            for task in pending:
                task.cancel()
                try:
                    await task # Clean up the cancelled task
                except asyncio.CancelledError:
                    pass

        except WebSocketDisconnect:
            logger.info("Client disconnected normally")
        except Exception as e:
            logger.error(f"Streaming session error: {e}")
        finally:
            # Crucial: Ensure the 'send' task isn't left hanging 
            # and the transcriber is reset for the next connection.
            receive_task.cancel()
            send_task.cancel()
            self._cleanup(websocket)

    async def _receive_loop(self, websocket: WebSocket):
        """
        Producer: Continuously receives binary data from the frontend.
        Expects Raw Float32 PCM @ 16kHz.
        """
        while True:
            data = await websocket.receive()
            
            if "bytes" in data:
                # Push raw bytes into the Tier 1 buffer
                await self.transcriber.consume_audio(data["bytes"])
            
            elif "text" in data:
                message = json.loads(data["text"])
                if message.get("command") == "reset":
                    self.transcriber.reset()
                    await websocket.send_json({"type": "reset", "status": "ok"})

    async def _send_loop(self, websocket: WebSocket):
        """
        Consumer: Continuously pulls results from the Tier 2/3 generator.
        """
        async for text in self.transcriber.stream_transcribe():
            if text == "[COMMIT]":
                # Signal the frontend that the current sentence is finalized
                await websocket.send_json({
                    "type": "transcription",
                    "text": "",
                    "is_final": True
                })
            else:
                # Send interim (rolling) results
                await websocket.send_json({
                    "type": "transcription",
                    "text": text,
                    "is_final": False
                })

    def _cleanup(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.transcriber.reset()