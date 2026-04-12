import io
import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Callable, Any
from openai import AsyncOpenAI, OpenAI
from openai._exceptions import OpenAIError

from services.transcriber.exceptions import (
    InvalidAudioError,
    InvalidFormatError,
    AudioSizeError,
    TranscriptionError,
    TranscriptionTimeoutError,
    APIConfigError,
    RetryExhaustedError,
)
from services.transcriber.models import TranscriptionRequest, TranscriptionResponse, TranscriptionMetrics


logger = logging.getLogger(__name__)


class AudioValidator:
    """Validates audio input before transcription."""
    
    # Magic bytes for audio format detection
    MAGIC_BYTES = {
        b'ID3': 'mp3',
        b'\xff\xfb': 'mp3',
        b'\xff\xfa': 'mp3',
        b'\xff\xf3': 'mp3',
        b'\xff\xf2': 'mp3',
        b'\x00\x00\x00\x20ftypisom': 'm4a',
        b'\x00\x00\x00\x18ftypaac': 'm4a',
        b'RIFF': 'wav',
        b'fLaC': 'flac',
        b'OggS': 'ogg',
    }
    
    def __init__(
        self,
        max_audio_size_mb: int = 25,
        supported_formats: Optional[list[str]] = None,
    ):
        self.max_audio_size_mb = max_audio_size_mb
        self.supported_formats = supported_formats or [
            "mp3", "aac", "wav", "flac", "ogg", "m4a"
        ]
    
    def detect_format(self, audio_bytes: bytes) -> Optional[str]:
        """Detect audio format from magic bytes."""
        for magic, fmt in self.MAGIC_BYTES.items():
            if audio_bytes.startswith(magic):
                return fmt
        return None
    
    def validate(self, audio_bytes: bytes, audio_format: str) -> None:
        """
        Validate audio input.
        
        Args:
            audio_bytes: Raw audio bytes
            audio_format: Audio format (e.g., 'mp3', 'aac')
            
        Raises:
            InvalidAudioError: If audio is empty
            InvalidFormatError: If format is not supported
            AudioSizeError: If audio exceeds size limit
        """
        if not audio_bytes:
            raise InvalidAudioError("Audio bytes cannot be empty")
        
        if len(audio_bytes) == 0:
            raise InvalidAudioError("Audio file is empty")
        
        # Validate format
        fmt = audio_format.lower().strip()
        if fmt not in self.supported_formats:
            raise InvalidFormatError(fmt, self.supported_formats)
        
        # Check size
        size_mb = len(audio_bytes) / (1024 * 1024)
        if size_mb > self.max_audio_size_mb:
            raise AudioSizeError(size_mb, self.max_audio_size_mb)
        
        # Log format detection attempt
        detected = self.detect_format(audio_bytes)
        if detected and detected != fmt:
            logger.warning(
                "Audio format mismatch",
                extra={
                    "detected_format": detected,
                    "provided_format": fmt,
                    "audio_size_bytes": len(audio_bytes)
                }
            )


class Transcriber:
    """Production-grade audio transcription service."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-audio-preview",
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        max_retry_delay_seconds: float = 32.0,
        request_timeout_seconds: int = 300,
        max_audio_size_mb: int = 25,
        supported_formats: Optional[list[str]] = None,
        client: Optional[OpenAI] = None,
        metrics_callback: Optional[Callable[[TranscriptionMetrics], None]] = None,
    ):
        """
        Initialize transcriber.
        
        Args:
            api_key: OpenAI API key (required)
            model: Model to use (default: gpt-4o-audio-preview)
            max_retries: Max retry attempts (default: 3)
            retry_delay_seconds: Initial retry delay (default: 1.0)
            max_retry_delay_seconds: Max retry delay (default: 32.0)
            request_timeout_seconds: Request timeout (default: 300)
            max_audio_size_mb: Max audio file size in MB (default: 25)
            supported_formats: List of supported formats
            client: OpenAI client instance (creates new one if None)
            metrics_callback: Callback for metrics collection
        """
        if not api_key:
            raise APIConfigError("OpenAI API key is required")
        if not model:
            raise APIConfigError("OpenAI model is required")
        
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.max_retry_delay_seconds = max_retry_delay_seconds
        self.request_timeout_seconds = request_timeout_seconds
        
        self.client = client or OpenAI(api_key=api_key)
        self.async_client = AsyncOpenAI(api_key=api_key)
        self.validator = AudioValidator(
            max_audio_size_mb=max_audio_size_mb,
            supported_formats=supported_formats,
        )
        self.metrics_callback = metrics_callback
        
        logger.info(
            "Transcriber initialized",
            extra={"model": self.model}
        )
    
    def _create_audio_file(self, audio_bytes: bytes, audio_format: str) -> io.BytesIO:
        """Create file-like object for OpenAI API."""
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio.{audio_format.lower()}"
        return audio_file
    
    def _record_metrics(
        self,
        request_id: str,
        duration_ms: float,
        audio_size: int,
        retries: int,
        success: bool,
    ) -> None:
        """Record transcription metrics."""
        if not self.metrics_callback:
            return
        
        metrics = TranscriptionMetrics(
            request_id=request_id,
            duration_ms=duration_ms,
            audio_size_bytes=audio_size,
            retry_count=retries,
            success=success,
            timestamp=datetime.utcnow(),
            model=self.model,
        )
        
        try:
            self.metrics_callback(metrics)
        except Exception as e:
            logger.error(
                "Failed to record metrics",
                extra={"error": str(e), "request_id": request_id}
            )
    
    async def _transcribe_with_retry(
        self,
        request: TranscriptionRequest,
        audio_file: io.BytesIO,
    ) -> str:
        """
        Transcribe with exponential backoff retry logic.
        
        Args:
            request: Transcription request
            audio_file: File-like audio object
            
        Returns:
            Transcription text
            
        Raises:
            RetryExhaustedError: If all retries fail
            TranscriptionTimeoutError: If timeout exceeded
        """
        last_error = None
        delay = self.retry_delay_seconds
        
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    "Transcription attempt",
                    extra={
                        "request_id": request.request_id,
                        "attempt": attempt + 1,
                        "max_attempts": self.max_retries,
                    }
                )
                
                audio_file.seek(0)
                
                response = await asyncio.wait_for(
                    self.async_client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file,
                        timeout=self.request_timeout_seconds,
                    ),
                    timeout=self.request_timeout_seconds
                )
                
                logger.info(
                    "Transcription successful",
                    extra={
                        "request_id": request.request_id,
                        "attempt": attempt + 1,
                    }
                )
                return response.text
                
            except asyncio.TimeoutError as e:
                last_error = e
                logger.error(
                    "Transcription timeout",
                    extra={
                        "request_id": request.request_id,
                        "attempt": attempt + 1,
                        "timeout_seconds": self.request_timeout_seconds,
                    }
                )
                raise TranscriptionTimeoutError(self.request_timeout_seconds)
                
            except OpenAIError as e:
                last_error = e
                logger.warning(
                    "Transcription API error",
                    extra={
                        "request_id": request.request_id,
                        "attempt": attempt + 1,
                        "error": str(e),
                    }
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, self.max_retry_delay_seconds)
                    
            except Exception as e:
                last_error = e
                logger.error(
                    "Unexpected error during transcription",
                    extra={
                        "request_id": request.request_id,
                        "attempt": attempt + 1,
                        "error": str(e),
                    }
                )
                raise TranscriptionError(
                    f"Unexpected error: {str(e)}",
                    original_error=e,
                    details={"attempt": attempt + 1}
                )
        
        # All retries exhausted
        raise RetryExhaustedError(
            f"Transcription failed after {self.max_retries} attempts",
            attempts=self.max_retries,
            last_error=last_error,
        )
    
    async def transcribe_async(
        self,
        audio_bytes: bytes,
        audio_format: str,
        request_id: Optional[str] = None,
    ) -> TranscriptionResponse:
        """
        Transcribe audio asynchronously.
        
        Args:
            audio_bytes: Raw audio bytes
            audio_format: Audio format (e.g., 'mp3', 'aac')
            request_id: Optional request ID for tracking
            
        Returns:
            TranscriptionResponse with transcribed text and metadata
            
        Raises:
            InvalidAudioError: If audio input is invalid
            InvalidFormatError: If format is not supported
            AudioSizeError: If audio exceeds size limit
            TranscriptionError: If transcription fails
            RetryExhaustedError: If all retries fail
        """
        start_time = time.time()
        request = TranscriptionRequest(
            audio_bytes=audio_bytes,
            audio_format=audio_format,
            request_id=request_id
        )
        
        try:
            # Validate input
            self.validator.validate(request.audio_bytes, request.audio_format)
            
            # Create file-like object
            audio_file = self._create_audio_file(
                request.audio_bytes,
                request.audio_format
            )
            
            # Transcribe with retries
            text = await self._transcribe_with_retry(request, audio_file)
            
            duration_ms = (time.time() - start_time) * 1000
            
            response = TranscriptionResponse(
                text=text,
                request_id=request.request_id,
                model=self.model,
                audio_size_bytes=len(request.audio_bytes),
                timestamp=datetime.utcnow(),
            )
            
            self._record_metrics(
                request.request_id,
                duration_ms,
                len(request.audio_bytes),
                retries=0,
                success=True,
            )
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._record_metrics(
                request.request_id,
                duration_ms,
                len(request.audio_bytes),
                retries=self.max_retries,
                success=False,
            )
            logger.error(
                "Transcription failed",
                extra={
                    "request_id": request.request_id,
                    "error": str(e),
                    "duration_ms": duration_ms,
                }
            )
            raise
    
    def transcribe(
        self,
        audio_bytes: bytes,
        audio_format: str,
        request_id: Optional[str] = None,
    ) -> TranscriptionResponse:
        """
        Transcribe audio synchronously (wrapper around async).
        
        Args:
            audio_bytes: Raw audio bytes
            audio_format: Audio format (e.g., 'mp3', 'aac')
            request_id: Optional request ID for tracking
            
        Returns:
            TranscriptionResponse with transcribed text and metadata
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.transcribe_async(audio_bytes, audio_format, request_id)
        )


# Convenience functions for backward compatibility
_transcriber_instance: Optional[Transcriber] = None


def _get_transcriber() -> Transcriber:
    """Get or create the default transcriber instance from main settings."""
    global _transcriber_instance
    if _transcriber_instance is None:
        from config import settings
        _transcriber_instance = Transcriber(
            api_key=settings.openai_api_key,
            model=settings.transcriber_model,
            max_retries=settings.transcriber_max_retries,
            retry_delay_seconds=settings.transcriber_retry_delay_seconds,
            max_retry_delay_seconds=settings.transcriber_max_retry_delay_seconds,
            request_timeout_seconds=settings.transcriber_request_timeout_seconds,
            max_audio_size_mb=settings.transcriber_max_audio_size_mb,
            supported_formats=settings.transcriber_supported_formats,
        )
    return _transcriber_instance


def transcribe_audio(audio_bytes: bytes, fmt: str) -> str:
    """
    Transcribe audio bytes (backward-compatible function).
    
    Args:
        audio_bytes: Raw audio bytes
        fmt: Audio format (e.g., 'mp3', 'aac')
        
    Returns:
        Transcript text
        
    Raises:
        InvalidAudioError: If audio input is invalid
        InvalidFormatError: If format is not supported
        AudioSizeError: If audio exceeds size limit
        TranscriptionError: If transcription fails
    """
    transcriber = _get_transcriber()
    response = transcriber.transcribe(audio_bytes, fmt)
    return response.text
