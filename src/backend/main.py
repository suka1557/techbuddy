import os
from loguru import logger
from pathlib import Path

from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import psycopg2
import tempfile
from concurrent.futures import ThreadPoolExecutor
from minio import Minio
from minio.error import S3Error

from io import BytesIO



from src.backend.configs.config import Config
from src.backend.utils.download_whisper import download_whisper_model
from src.backend.audio.whisper_model import StreamingFasterWhisperTranscriber
from src.backend.websocket.candidate_websocket_handler import TranscriptionWebSocket
from src.backend.websocket.interviewer_websocket_handler import NarratorWebSocket
from src.backend.questions.question_provider import QuestionProvider
from src.backend.utils.configure_logger import configure_logger
from src.backend.utils.openai_client import AsyncOpenAIClient
from src.backend.utils.minio_client import AsyncMinioClient


ROOT_PATH = Path(__file__).resolve().parents[2]  # .../techbuddy

# Load configuration
config = Config.from_yaml(os.path.join(ROOT_PATH, "src", "backend", "configs", os.getenv("ENVIRONMENT", "dev") + ".yaml"))

DATA_PATH = ROOT_PATH / "data"
LOGS_PATH = ROOT_PATH / config.get("logs", {}).get("log_dir","")

# Configure logger
configure_logger(
    log_file=os.path.join(LOGS_PATH, "techbuddy.log"),
    log_level=config.get("logs", {}).get("log_level", "INFO")
)

logger.info(f"ENVIRONMENT variable: {os.getenv('ENVIRONMENT')}")
logger.info(f"Base path: {ROOT_PATH}")

if not os.getenv("OPENAI_API_KEY"):
    logger.error("OPENAI_API_KEY is not set in environment variables. Please set it before running the application.")
    raise EnvironmentError("OPENAI_API_KEY is required")

# Shared executor
shared_executor = ThreadPoolExecutor(
    max_workers=config.get("threading", {}).get("max_workers", 20),
    thread_name_prefix="techbuddy-worker"
)

# ==========================================================
# MINIO CONFIG
# ==========================================================

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

BUCKET_NAME = config.get("minio", {}).get("bucket_name", "techbuddy")

# Initialize MinIO client
minio_client = AsyncMinioClient(executor=shared_executor, 
                                endpoint=MINIO_ENDPOINT, 
                               access_key=MINIO_ACCESS_KEY, 
                               secret_key=MINIO_SECRET_KEY, 
                               secure=MINIO_SECURE)

# Load Whisper Model configuration
model_cfg = config.get("stt_model", {})
model_name = model_cfg.get("model_name", "base.en")
model_dir = model_cfg.get("model_dir", os.path.join(ROOT_PATH, "src", "backend", "models"))
logger.info(f"Model configuration - Name: {model_name}, Directory: {model_dir}")

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

# Pull values from the environment (injected by Docker Compose)
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "techbuddy_db"),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASS", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}
# Log the database configuration (except password) for debugging
logger.info(f"Database configuration - Host: {DB_CONFIG['host']}, Port: {DB_CONFIG['port']}, Name: {DB_CONFIG['dbname']}, User: {DB_CONFIG['user']}")

# Initialize OpenAI client
stt_cleaner_model = config.get("openai", {}).get("stt_cleaner_model", "gpt-4.1")
logger.info(f"STT Cleanup model: {stt_cleaner_model}")
openai_client = AsyncOpenAIClient(model=stt_cleaner_model)
logger.info("OpenAI client initialized")

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

# Initialize Transcription WebSocket handler
ws_handler = TranscriptionWebSocket(whisper_model, openai_client, stt_cleaner_model)

#Initialize Question Provider
question_provider = QuestionProvider(file_path=config.get("questions", {}).get("file_path"))    
# Initialize Narrator WebSocket handler
narrator_ws_handler = NarratorWebSocket(question_provider=question_provider)



@app.on_event("startup")
async def startup_event():

    # Create bucket if missing
    await minio_client.create_bucket(BUCKET_NAME)

    # Create logical paths
    await minio_client.create_path(
        BUCKET_NAME,
        "resumes/"
    )

    await minio_client.create_path(
        BUCKET_NAME,
        "job_descriptions/"
    )


# ==========================================================
# RESUME UPLOAD
# ==========================================================

@app.post("/upload/resume")
async def upload_resume(
    file: UploadFile = File(...)
):
    try:

        # Save temporarily
        suffix = Path(file.filename).suffix

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            content = await file.read()

            temp_file.write(content)

            temp_path = temp_file.name

        # Upload to MinIO
        await minio_client.upload_file(
            bucket_name=BUCKET_NAME,
            object_name=f"resumes/{file.filename}",
            file_path=temp_path,
            content_type=file.content_type
        )

        # Cleanup temp file
        os.remove(temp_path)

        return {
            "success": True,
            "filename": file.filename,
            "bucket": BUCKET_NAME,
            "path": f"resumes/{file.filename}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    

# ==========================================================
# JD UPLOAD
# ==========================================================

@app.post("/upload/jd")
async def upload_jd(
    file: UploadFile = File(...)
):
    try:

        suffix = Path(file.filename).suffix

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            content = await file.read()

            temp_file.write(content)

            temp_path = temp_file.name

        # Upload to MinIO
        await minio_client.upload_file(
            bucket_name=BUCKET_NAME,
            object_name=f"job_descriptions/{file.filename}",
            file_path=temp_path,
            content_type=file.content_type
        )

        # Cleanup temp file
        os.remove(temp_path)

        return {
            "success": True,
            "filename": file.filename,
            "bucket": BUCKET_NAME,
            "path": f"job_descriptions/{file.filename}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/", response_class=HTMLResponse)
async def login_page():
    """Serve the Sign In / Sign Up page."""
    auth_path = frontend_path / "auth.html"
    if auth_path.exists():
        return auth_path.read_text()
    return "<h1>TechBuddy</h1><p>Auth page not found</p>"


@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    """Serve the upload page."""
    upload_path = frontend_path / "upload.html"
    if upload_path.exists():
        return upload_path.read_text()
    return "<h1>TechBuddy</h1><p>Upload page not found</p>"


@app.get("/interview", response_class=HTMLResponse)
async def interview_page():
    """Serve the main transcription/interview interface."""
    transcribe_path = frontend_path / "transcribe2.html"
    if transcribe_path.exists():
        return transcribe_path.read_text()
    return "<h1>Error</h1><p>Transcription page not found</p>"


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

@app.websocket("/ws/narrator")
async def websocket_narrator(websocket: WebSocket):
    """Handle Left Side Questions/Narration"""
    await narrator_ws_handler.handle_narrator(websocket)


def main():
    """Run the FastAPI server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"Starting TechBuddy server on {host}:{port}")
    logger.info(f"WebSocket endpoint: ws://{host}:{port}/ws/transcribe")
    logger.info(f"Narrator WebSocket endpoint: ws://{host}:{port}/ws/narrator")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()