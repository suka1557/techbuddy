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
        self.full_transcript = ""   # Accumulates committed text
        self.previous_output = ""   # Previous transcription for overlap detection

    def _find_committed_text(self, previous: str, current: str) -> str:
        """
        Detect text that has 'fallen off' the sliding window.
        When the current transcription no longer starts with the same text,
        the missing beginning has been implicitly committed.
        """
        if not previous or not current:
            return ""
        
        prev_words = previous.split()
        curr_words = current.split()
        
        if not prev_words or not curr_words:
            return ""
        
        # Find where current text overlaps with previous text
        # Look for the longest suffix of prev_words that matches a prefix of curr_words
        best_overlap_start = len(prev_words)  # Default: no overlap found
        
        for i in range(len(prev_words)):
            suffix = prev_words[i:]
            # Check if this suffix matches the start of current (with some tolerance)
            match_len = min(len(suffix), len(curr_words))
            if match_len > 0:
                # Count matching words at the start
                matches = 0
                for j in range(match_len):
                    # Fuzzy match - ignore punctuation and case
                    w1 = suffix[j].lower().strip('.,!?;:')
                    w2 = curr_words[j].lower().strip('.,!?;:')
                    if w1 == w2:
                        matches += 1
                    else:
                        break
                
                # If we found a good overlap (at least 2 words matching)
                if matches >= min(2, match_len):
                    best_overlap_start = i
                    break
        
        # Everything before the overlap has "fallen off" - commit it
        if best_overlap_start > 0:
            committed_words = prev_words[:best_overlap_start]
            return " ".join(committed_words)
        
        return ""

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
                    self.full_transcript = ""
                    self.previous_output = ""
                    await websocket.send_json({"type": "reset", "status": "ok"})
                
                elif message.get("command") == "get_transcript":
                    # Return the full accumulated transcript + current window
                    final_text = self.full_transcript
                    if self.previous_output.strip():
                        final_text += " " + self.previous_output.strip()
                    final_text = final_text.strip()
                    logger.info(f"Final transcript requested: {final_text}")
                    await websocket.send_json({
                        "type": "full_transcript",
                        "text": final_text
                    })

    async def _send_loop(self, websocket: WebSocket):
        """
        Consumer: Continuously pulls results from the Tier 2/3 generator.
        Detects text that falls off the sliding window and commits it.
        """
        async for text in self.transcriber.stream_transcribe():
            
            if text == "[COMMIT]":
                # Explicit commit signal - add current window to transcript
                if self.previous_output.strip():
                    self.full_transcript += " " + self.previous_output.strip()
                self.previous_output = ""
                
                await websocket.send_json({
                    "type": "transcription",
                    "text": "",
                    "is_final": True
                })
            else:
                # Detect text that "fell off" the sliding window
                committed = self._find_committed_text(self.previous_output, text)
                if committed:
                    self.full_transcript += " " + committed
                    logger.debug(f"Committed text: {committed}")
                    logger.debug(f"Full transcript so far: {self.full_transcript.strip()}")
                
                # Update previous for next comparison
                self.previous_output = text
                
                # Send current window as interim
                await websocket.send_json({
                    "type": "transcription",
                    "text": text,
                    "is_final": False
                })

    def _cleanup(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.transcriber.reset()
        self.full_transcript = ""
        self.previous_output = ""