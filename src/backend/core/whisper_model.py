"""
Streaming Whisper Model Class for real-time audio transcription.
Supports continuous audio input and streaming text output via WebSocket.
"""

from __future__ import annotations

import asyncio
import io
import wave
from pathlib import Path
from typing import AsyncGenerator
from loguru import logger

try:
    from pywhispercpp.model import Model as WhisperCppModel

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("pywhispercpp not installed. Install with: pip install pywhispercpp")

import numpy as np
from pydub import AudioSegment


class WhisperModel:
    """
    Whisper Model wrapper for streaming transcription.

    This class loads a Whisper model and provides methods to transcribe
    audio in a streaming fashion, suitable for WebSocket connections.
    """

    def __init__(
        self,
        model_path: str | Path,
        n_threads: int = 4,
        language: str = "en",
        translate: bool = False,
        print_realtime: bool = False,
        print_progress: bool = False,
    ):
        """
        Initialize the Whisper model.

        Args:
            model_path: Path to the GGML whisper model file
            n_threads: Number of threads for inference
            language: Language code (e.g., 'en', 'es', 'fr')
            translate: Whether to translate to English
            print_realtime: Print transcription in real-time
            print_progress: Print progress during transcription
        """
        if not WHISPER_AVAILABLE:
            raise RuntimeError(
                "pywhispercpp is required but not installed. "
                "Install with: pip install pywhispercpp"
            )

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at: {self.model_path}")

        self.n_threads = n_threads
        self.language = language
        self.translate = translate
        self.print_realtime = print_realtime
        self.print_progress = print_progress

        logger.info(f"Loading Whisper model from: {self.model_path}")
        self.model = WhisperCppModel(
            str(self.model_path),
            n_threads=self.n_threads,
            print_realtime=self.print_realtime,
            print_progress=self.print_progress,
        )
        logger.info("Whisper model loaded successfully")

        # Audio buffer for accumulating chunks
        self.audio_buffer = bytearray()
        self.sample_rate = 16000  # Whisper expects 16kHz
        self.min_audio_length = 2.0  # Minimum 2 seconds of audio before transcription
        self.chunk_count = 0  # Track number of chunks received

    def transcribe(self, audio_data: bytes | np.ndarray, **kwargs) -> str:
        """
        Transcribe audio data synchronously.

        Args:
            audio_data: Audio bytes or numpy array (16kHz, mono, float32)
            **kwargs: Additional parameters for transcription

        Returns:
            Transcribed text
        """
        # Convert bytes to numpy array if needed
        if isinstance(audio_data, bytes):
            audio_array = self._bytes_to_array(audio_data)
        else:
            audio_array = audio_data

        # Ensure float32 and normalized
        if audio_array.dtype != np.float32:
            audio_array = audio_array.astype(np.float32)

        # Normalize to [-1, 1] if needed
        if audio_array.max() > 1.0:
            audio_array = audio_array / 32768.0

        # Transcribe
        segments = self.model.transcribe(
            audio_array, language=self.language, translate=self.translate, **kwargs
        )

        # Combine segments into text
        text = " ".join([seg.text.strip() for seg in segments if seg.text.strip()])
        return text

    async def transcribe_async(self, audio_data: bytes | np.ndarray, **kwargs) -> str:
        """
        Transcribe audio data asynchronously.

        Args:
            audio_data: Audio bytes or numpy array
            **kwargs: Additional parameters for transcription

        Returns:
            Transcribed text
        """
        # Run transcription in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.transcribe,
            audio_data,
        )

    async def transcribe_stream(
        self,
        audio_chunk: bytes,
        finalize: bool = False,
    ) -> AsyncGenerator[str, None]:
        """
        Process audio chunks in streaming mode.

        This method accumulates audio chunks and transcribes when enough
        audio is buffered or when finalized, yielding partial results.

        Args:
            audio_chunk: Audio bytes chunk (WebM, WAV, or raw PCM)
            finalize: Whether this is the final chunk

        Yields:
            Transcribed text segments
        """
        # Add chunk to buffer
        if audio_chunk:
            self.audio_buffer.extend(audio_chunk)
            self.chunk_count += 1
            logger.debug(
                f"Accumulated chunk #{self.chunk_count}, buffer size: {len(self.audio_buffer)} bytes"
            )

        # Only transcribe when finalizing to avoid partial WebM parsing issues
        # WebM chunks are not self-contained - they need to be processed as a complete stream
        if finalize and len(self.audio_buffer) > 0:
            try:
                logger.info(
                    f"Finalizing transcription with {len(self.audio_buffer)} bytes from {self.chunk_count} chunks"
                )

                # Convert entire accumulated buffer to audio array
                audio_array = self._bytes_to_array(bytes(self.audio_buffer))

                # Transcribe
                text = await self.transcribe_async(audio_array)

                if text.strip():
                    yield text

                # Clear buffer after transcription
                self.audio_buffer.clear()
                self.chunk_count = 0

            except Exception as e:
                logger.error(f"Error during streaming transcription: {e}")
                # Clear buffer on error when finalizing
                self.audio_buffer.clear()
                self.chunk_count = 0
                raise

    def reset_buffer(self):
        """Clear the audio buffer."""
        self.audio_buffer.clear()
        self.chunk_count = 0
        logger.debug("Audio buffer reset")

    def _bytes_to_array(self, audio_bytes: bytes) -> np.ndarray:
        """
        Convert audio bytes to numpy array.

        Supports WAV, WebM, and raw PCM formats.

        Args:
            audio_bytes: Audio data in bytes

        Returns:
            Numpy array (float32, mono, 16kHz)
        """
        try:
            # Try to parse as AudioSegment (handles WebM, WAV, etc.)
            audio_segment = AudioSegment.from_file(
                io.BytesIO(audio_bytes),
                format="webm",  # Frontend sends WebM
            )

            # Convert to mono and 16kHz
            audio_segment = audio_segment.set_channels(1)
            audio_segment = audio_segment.set_frame_rate(self.sample_rate)

            # Convert to numpy array
            samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)

            # Normalize to [-1, 1]
            samples = samples / 32768.0

            return samples

        except Exception as e:
            logger.warning(f"Could not parse as AudioSegment: {e}, trying WAV")

            # Try parsing as WAV
            try:
                with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
                    frames = wav_file.readframes(wav_file.getnframes())
                    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                    samples = samples / 32768.0
                    return samples
            except Exception as wav_error:
                logger.error(f"Could not parse audio: {wav_error}")
                raise ValueError("Unsupported audio format") from wav_error

    def _estimate_duration(self, buffer_size: bytes) -> float:
        """
        Estimate audio duration from buffer size.

        Assumes 16kHz, mono, 16-bit PCM.

        Args:
            buffer_size: Size of audio buffer in bytes

        Returns:
            Duration in seconds
        """
        bytes_per_second = self.sample_rate * 2  # 16-bit = 2 bytes per sample
        return buffer_size / bytes_per_second

    def __del__(self):
        """Cleanup when object is destroyed."""
        if hasattr(self, "model"):
            logger.debug("Cleaning up Whisper model")
