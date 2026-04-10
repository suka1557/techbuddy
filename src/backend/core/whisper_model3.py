import asyncio
import numpy as np
from collections import deque
from typing import AsyncGenerator
from loguru import logger
from faster_whisper import WhisperModel

class StreamingFasterWhisperTranscriber:
    """
    Real-time Streaming Transcriber using faster-whisper.
    Uses CTranslate2 backend for high-performance inference.
    """

    def __init__(
        self,
        model_size: str = "base",  # choices: "tiny", "base", "small", "medium", "large-v3"
        device: str = "cpu",        # "cpu" or "cuda"
        compute_type: str = "int8", # "int8" for CPU, "float16" for GPU
        sample_rate: int = 16000,
        window_size_sec: float = 3.0,
        step_size_sec: float = 0.5,
        min_silence_duration_ms: int = 700,
    ):
        self.sample_rate = sample_rate
        self.step_size_sec = step_size_sec
        self.window_size_samples = int(window_size_sec * sample_rate)
        self.step_size_samples = int(step_size_sec * sample_rate)
        
        # Audio Buffer (Rolling Window)
        self.audio_buffer = deque(maxlen=self.window_size_samples * 2)
        
        # Initialize Faster Whisper
        # This will automatically download the model on the first run
        logger.info(f"Loading Faster-Whisper model: {model_size} ({compute_type})")
        self.model = WhisperModel(
            model_size, 
            device=device, 
            compute_type=compute_type
        )
        
        # VAD & State
        self.silence_samples_count = 0
        self.min_silence_samples = int((min_silence_duration_ms / 1000) * sample_rate)
        self.is_speaking = False
        
        self._lock = asyncio.Lock()

    async def consume_audio(self, pcm_chunk: bytes):
        """Tier 1: Accept raw Float32 PCM bytes."""
        samples = np.frombuffer(pcm_chunk, dtype=np.float32)
        async with self._lock:
            self.audio_buffer.extend(samples)

    async def stream_transcribe(self) -> AsyncGenerator[str, None]:
        """Tier 2 & 3: Optimized sliding window transcription."""
        while True:
            if len(self.audio_buffer) < self.window_size_samples:
                await asyncio.sleep(0.1)
                continue

            async with self._lock:
                current_window = np.array(list(self.audio_buffer))
            
            # Transcription with built-in VAD filter
            loop = asyncio.get_running_loop()
            text, speech_detected = await loop.run_in_executor(
                None, self._transcribe_internal, current_window
            )

            if speech_detected:
                self.is_speaking = True
                self.silence_samples_count = 0
                if text:
                    yield text
            else:
                # Silence logic (Commit)
                if self.is_speaking:
                    self.silence_samples_count += self.step_size_samples
                    if self.silence_samples_count >= self.min_silence_samples:
                        logger.info("VAD: End of speech detected.")
                        yield "[COMMIT]"
                        async with self._lock:
                            self.audio_buffer.clear()
                        self.is_speaking = False
                        self.silence_samples_count = 0

            await asyncio.sleep(self.step_size_sec)

    def _transcribe_internal(self, audio: np.ndarray):
        """
        Synchronous wrapper for Faster-Whisper.
        Uses greedy decoding (beam_size=1) for maximum speed.
        """
        try:
            # vad_filter=True uses Silero VAD internally
            segments, info = self.model.transcribe(
                audio,
                beam_size=1,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                language="en"
            )
            
            # Convert segments to string
            segments = list(segments)
            speech_detected = len(segments) > 0
            text = " ".join([s.text for s in segments]).strip()
            
            return text, speech_detected
        except Exception as e:
            logger.error(f"Faster-Whisper Inference Error: {e}")
            return "", False

    def reset(self):
        self.audio_buffer.clear()
        self.is_speaking = False
        self.silence_samples_count = 0