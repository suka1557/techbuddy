import os
from loguru import logger
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

ROOT_PATH = Path(__file__).resolve().parents[2]  # .../techbuddy
logger.info(f"Base path: {ROOT_PATH}")

from configs.config import Config
from utils.download_whisper import download_whisper_model
from core.whisper_model3 import StreamingFasterWhisperTranscriber
from core.websocket_handler2 import TranscriptionWebSocket

# Load configuration
config = Config.from_yaml(os.path.join(ROOT_PATH, "src", "backend", "configs/dev.yaml"))

# Load Model configuration
model_cfg = config.get("model", {})
model_name = model_cfg.get("model_name", "base.en")
model_dir = model_cfg.get("model_dir", os.path.join(ROOT_PATH, "src", "backend", "models"))

# Download model if not already present
model_path = download_whisper_model(model_dir, model_name)
logger.info(f"Model ready at: {model_path}")

# Initialize Whisper Model
whisper_model = StreamingFasterWhisperTranscriber(
    model_size="base",  # Adjust as needed
    device="cpu",
    compute_type="int8",
    sample_rate=16000,
    window_size_sec=3.0,
    step_size_sec=0.5,
    min_silence_duration_ms=700
)
logger.info("Whisper model initialized")

# Initialize FastAPI app
app = FastAPI(
    title="TechBuddy - Streaming Speech Transcription",
    description="Real-time speech-to-text via WebSocket",
    version="0.1.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend files
frontend_path = ROOT_PATH / "src" / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Initialize WebSocket handler
ws_handler = TranscriptionWebSocket(whisper_model)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main page with WebSocket transcription."""
    transcribe_path = frontend_path / "transcribe2.html"
    if transcribe_path.exists():
        return transcribe_path.read_text()
    return "<h1>TechBuddy Server</h1><p>Frontend not found</p>"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": model_name,
        "model_loaded": whisper_model is not None
    }


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for streaming audio transcription.
    
    Client should send audio chunks as binary data.
    Server responds with JSON messages containing transcribed text.
    """
    await ws_handler.handle_transcription(websocket)


def main():
    """Run the FastAPI server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"Starting TechBuddy server on {host}:{port}")
    logger.info(f"WebSocket endpoint: ws://{host}:{port}/ws/transcribe")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()