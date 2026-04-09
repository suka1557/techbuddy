# TechBuddy - Streaming Whisper Transcription

## Overview

TechBuddy now includes a custom Whisper Model class with real-time streaming transcription capabilities over WebSocket connections.

## Architecture

### Backend Components

1. **WhisperModel Class** (`src/backend/models/whisper_model.py`)
   - Loads Whisper GGML models into memory
   - Accepts audio bytes and transcribes to text
   - Supports streaming mode for continuous audio input
   - Thread-safe async operations

2. **TranscriptionWebSocket** (`src/backend/utils/websocket_handler.py`)
   - Manages WebSocket connections
   - Handles audio chunk processing
   - Streams transcription results back to clients
   - Supports commands: finalize, reset, ping

3. **FastAPI Server** (`src/backend/main.py`)
   - REST API endpoints
   - WebSocket endpoint at `/ws/transcribe`
   - Serves static frontend files
   - CORS enabled for development

### Frontend

- **transcribe.html**: Enhanced UI with WebSocket support
  - Real-time audio recording
  - Live waveform visualization
  - Continuous transcription display
  - Connection status monitoring

## Installation

1. **Install dependencies:**
```bash
pip install -e .
```

This installs:
- `pywhispercpp` - Python bindings for whisper.cpp
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `websockets` - WebSocket support
- `pydub` - Audio processing
- Other required packages

2. **Download Whisper model** (if not already downloaded):
```bash
# Models are auto-downloaded on first run
# Configuration in: src/backend/configs/dev.yaml
```

## Usage

### Starting the Server

```bash
# Run from project root
cd /home/ar-in-u-301/Documents/codes/techbuddy

# Start the server
python -m src.backend.main

# Or use the entry point (after installation)
# techbuddy-server  # (if configured)
```

The server starts on `http://localhost:8000`

### WebSocket Endpoint

**Endpoint:** `ws://localhost:8000/ws/transcribe`

**Message Protocol:**

From Client:
- Binary messages: Audio chunks (WebM format)
- JSON commands:
  ```json
  {"command": "finalize"}  // Finalize current buffer
  {"command": "reset"}     // Clear audio buffer
  {"command": "ping"}      // Health check
  ```

From Server:
```json
{
  "type": "connection",
  "status": "connected",
  "message": "Ready for audio streaming"
}

{
  "type": "transcription",
  "text": "transcribed text here",
  "is_final": false
}

{
  "type": "error",
  "message": "error details"
}
```

### Using the Frontend

1. **Open in browser:**
   ```
   http://localhost:8000/static/transcribe.html
   ```

2. **Grant microphone permissions**

3. **Click "Start Recording"** - Audio streams to server

4. **Transcription appears in real-time**

5. **Click "Stop Recording"** when done

## API Reference

### WhisperModel Class

```python
from models.whisper_model import WhisperModel

# Initialize model
model = WhisperModel(
    model_path="/path/to/ggml-model.bin",
    n_threads=4,
    language="en",
    translate=False,
)

# Synchronous transcription
text = model.transcribe(audio_bytes)

# Async transcription
text = await model.transcribe_async(audio_bytes)

# Streaming mode
async for text in model.transcribe_stream(chunk, finalize=False):
    print(text)

# Reset buffer
model.reset_buffer()
```

### Configuration

Edit `src/backend/configs/dev.yaml`:

```yaml
model:
  model_name: "base.en"  # Available: tiny, base, small, medium, large-v3
  model_dir: "/path/to/models"
```

## Features

### WhisperModel Features
- ✅ Loads GGML format models
- ✅ Synchronous and asynchronous transcription
- ✅ Streaming mode with audio buffering
- ✅ Automatic audio format detection (WebM, WAV, PCM)
- ✅ Audio preprocessing (mono conversion, 16kHz resampling)
- ✅ Thread-safe operations

### WebSocket Features
- ✅ Real-time audio streaming
- ✅ Continuous transcription updates
- ✅ Connection management
- ✅ Error handling and recovery
- ✅ Command protocol (finalize, reset, ping)
- ✅ Multi-client support

### Frontend Features
- ✅ Live audio recording
- ✅ Waveform visualization
- ✅ Real-time transcription display
- ✅ Connection status monitoring
- ✅ Auto-reconnection
- ✅ Microphone permissions handling

## Troubleshooting

### pywhispercpp Installation Issues

If you encounter issues installing `pywhispercpp`:

```bash
# Option 1: Install from source
pip install git+https://github.com/abdeladim-s/pywhispercpp

# Option 2: Use whisper (OpenAI's package) instead
# Modify whisper_model.py to use OpenAI's whisper
pip install openai-whisper
```

### WebSocket Connection Errors

- Check if server is running on port 8000
- Verify firewall settings
- Ensure browser supports WebSocket
- Check CORS configuration in main.py

### Audio Issues

- Grant microphone permissions in browser
- Check microphone is working (browser dev tools)
- Verify audio format compatibility
- Check sample rate (model expects 16kHz)

### Model Loading Issues

- Verify model path in config
- Check model file exists and is GGML format
- Ensure sufficient memory for model

## Performance Tips

1. **Model Selection:**
   - `tiny`: Fastest, lower accuracy
   - `base`: Good balance (recommended)
   - `small`: Better accuracy, slower
   - `large-v3`: Best accuracy, requires GPU

2. **Thread Configuration:**
   ```python
   # Adjust based on CPU cores
   model = WhisperModel(model_path, n_threads=4)
   ```

3. **Buffer Settings:**
   ```python
   # Adjust min_audio_length for responsiveness vs accuracy
   model.min_audio_length = 1.0  # seconds
   ```

4. **Audio Chunk Size:**
   - Frontend sends chunks every 1000ms
   - Adjust in transcribe.html: `mediaRecorder.start(1000)`

## Development

### Project Structure
```
src/backend/
├── main.py                    # FastAPI server + WebSocket
├── configs/
│   ├── config.py             # Config loader
│   └── dev.yaml              # Model configuration
├── models/
│   ├── __init__.py
│   └── whisper_model.py      # WhisperModel class
└── utils/
    ├── download_whisper.py   # Model downloader
    └── websocket_handler.py  # WebSocket handler

src/frontend/
├── index.html                # Original recorder
├── index2.html
└── transcribe.html          # WebSocket-enabled UI
```

### Running Tests

```bash
# TODO: Add tests
pytest tests/
```

## License

See LICENSE file in project root.

## Credits

- Uses [whisper.cpp](https://github.com/ggerganov/whisper.cpp) models
- Based on OpenAI's Whisper architecture
