from typing import Optional


class TranscriberException(Exception):
    """Base exception for transcriber service."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "TRANSCRIBER_ERROR",
        details: Optional[dict] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class InvalidAudioError(TranscriberException):
    """Raised when audio input is invalid."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "INVALID_AUDIO", details)


class InvalidFormatError(TranscriberException):
    """Raised when audio format is not supported."""
    
    def __init__(self, fmt: str, supported: list[str]):
        message = f"Unsupported audio format: {fmt}. Supported formats: {', '.join(supported)}"
        details = {"format": fmt, "supported_formats": supported}
        super().__init__(message, "INVALID_FORMAT", details)


class AudioSizeError(TranscriberException):
    """Raised when audio file exceeds size limit."""
    
    def __init__(self, size_mb: float, max_size_mb: int):
        message = f"Audio file size ({size_mb:.2f}MB) exceeds maximum ({max_size_mb}MB)"
        details = {"size_mb": size_mb, "max_size_mb": max_size_mb}
        super().__init__(message, "AUDIO_SIZE_EXCEEDED", details)


class TranscriptionError(TranscriberException):
    """Raised when transcription API call fails."""
    
    def __init__(
        self, 
        message: str, 
        original_error: Optional[Exception] = None,
        details: Optional[dict] = None
    ):
        full_details = details or {}
        if original_error:
            full_details["original_error"] = str(original_error)
        super().__init__(message, "TRANSCRIPTION_FAILED", full_details)


class TranscriptionTimeoutError(TranscriberException):
    """Raised when transcription request times out."""
    
    def __init__(self, timeout_seconds: int):
        message = f"Transcription request timed out after {timeout_seconds} seconds"
        details = {"timeout_seconds": timeout_seconds}
        super().__init__(message, "TRANSCRIPTION_TIMEOUT", details)


class APIConfigError(TranscriberException):
    """Raised when API configuration is missing or invalid."""
    
    def __init__(self, message: str):
        super().__init__(message, "API_CONFIG_ERROR", {})


class RetryExhaustedError(TranscriberException):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(self, message: str, attempts: int, last_error: Optional[Exception] = None):
        details = {
            "attempts": attempts,
            "last_error": str(last_error) if last_error else None
        }
        super().__init__(message, "RETRIES_EXHAUSTED", details)
