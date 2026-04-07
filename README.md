# techbuddy
Local, streaming speech transcription over WebSocket using `whisper.cpp`.

## Overview
Mic audio is captured in 30 ms frames, gated by VAD, buffered into utterances, and sent as raw PCM bytes to a FastAPI WebSocket server. The server runs `pywhispercpp` and streams transcript segments back to the UI.

```
[ Microphone ] -> [ Python UI ] -> [ WebSocket ] -> [ Python Server ] -> [ whisper.cpp ] -> [ Transcript back to UI ]
```

## Requirements
- Python 3.11+
- A `whisper.cpp` model file (e.g., `ggml-base.en.bin`)

## Notes
- The UI uses `sounddevice` with a raw input stream; ensure your microphone device is available.
- `pywhispercpp` requires a compatible `whisper.cpp` model file.
