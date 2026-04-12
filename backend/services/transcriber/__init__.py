"""
Production-grade audio transcription service.

This module provides a robust, observable, and configurable transcription service
built on top of OpenAI's audio transcription API.

Example usage:
    from services.transcriber import Transcriber, TranscriptionResponse
    
    # Initialize transcriber with explicit config
    transcriber = Transcriber(
        api_key="sk-...",
        model="gpt-4o-audio-preview",
        max_retries=3,
    )
    
    # Transcribe audio
    response = transcriber.transcribe(audio_bytes, "mp3")
    print(response.text)  # Transcribed text
    print(response.request_id)  # For tracking
    print(response.timestamp)  # When it was transcribed
    
    # Or use async
    response = await transcriber.transcribe_async(audio_bytes, "mp3")

Configuration is done via environment variables in the main settings (backend/config.py):
    OPENAI_API_KEY: OpenAI API key (required, shared with app)
    TRANSCRIBER_MODEL: Model to use (default: gpt-4o-audio-preview)
    TRANSCRIBER_MAX_RETRIES: Max retry attempts (default: 3)
    TRANSCRIBER_REQUEST_TIMEOUT_SECONDS: Timeout per request (default: 300)
    TRANSCRIBER_MAX_AUDIO_SIZE_MB: Max audio file size (default: 25)

Exception handling:
    All transcription errors are subclassed from TranscriberException, allowing
    you to catch and handle specific error types:
    
    from services.transcriber.exceptions import (
        InvalidAudioError,
        AudioSizeError,
        TranscriptionTimeoutError,
        RetryExhaustedError,
    )
    
    try:
        response = transcriber.transcribe(audio_bytes, "mp3")
    except AudioSizeError as e:
        # Handle oversized audio
        print(f"Audio too large: {e.details['size_mb']}MB")
    except RetryExhaustedError as e:
        # All retries failed
        print(f"Failed after {e.details['attempts']} attempts")
    except TranscriberException as e:
        # Any other transcriber error
        print(f"Error: {e.error_code} - {e.message}")
"""

from services.transcriber.transcriber import (
    Transcriber,
    AudioValidator,
    transcribe_audio,
)
from services.transcriber.models import (
    TranscriptionRequest,
    TranscriptionResponse,
    TranscriptionMetrics,
)
from services.transcriber.exceptions import (
    TranscriberException,
    InvalidAudioError,
    InvalidFormatError,
    AudioSizeError,
    TranscriptionError,
    TranscriptionTimeoutError,
    APIConfigError,
    RetryExhaustedError,
)

__all__ = [
    # Main classes
    "Transcriber",
    "AudioValidator",
    # Models
    "TranscriptionRequest",
    "TranscriptionResponse",
    "TranscriptionMetrics",
    # Exceptions
    "TranscriberException",
    "InvalidAudioError",
    "InvalidFormatError",
    "AudioSizeError",
    "TranscriptionError",
    "TranscriptionTimeoutError",
    "APIConfigError",
    "RetryExhaustedError",
    # Backward-compatible function
    "transcribe_audio",
]
