import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from questions.question_provider import QuestionProvider

class NarratorWebSocket:
    """
    Handles the Left Side of the UI.
    Requests questions from a DB/API and streams them to the client.
    """
    def __init__(self, question_provider: QuestionProvider):
        self.active_connections: list[WebSocket] = []
        self.question_provider = question_provider

    async def handle_narrator(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Narrator WebSocket connected")

        try:
            while True:
                # Wait for commands like "get_next_question"
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("command") == "get_next_question":
                    question = self.question_provider.get_next_from_file()
                    await self.stream_text(websocket, question)

        except WebSocketDisconnect:
            logger.info("Narrator WebSocket disconnected")
        finally:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def stream_text(self, websocket: WebSocket, full_text: str):
        """Drip-feeds text to create a typing effect."""
        words = full_text.split()
        for word in words:
            await websocket.send_json({
                "type": "narrator_stream",
                "text": word + "  ",
                "is_final": False
            })
            await asyncio.sleep(0.06) 
        
        # Final signal to trigger last TTS chunk
        await websocket.send_json({
            "type": "narrator_stream",
            "text": "",
            "is_final": True
        })