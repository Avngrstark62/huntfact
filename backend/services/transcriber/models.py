from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid


class TranscriptionRequest(BaseModel):
    """Request model for transcription."""
    
    audio_bytes: bytes
    audio_format: str
    request_id: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.request_id:
            self.request_id = str(uuid.uuid4())


class TranscriptionResponse(BaseModel):
    """Response model for transcription."""
    
    text: str
    request_id: str
    model: str
    language: Optional[str] = None
    duration_seconds: Optional[float] = None
    audio_size_bytes: int
    timestamp: datetime
    confidence: Optional[float] = None
    
    class Config:
        from_attributes = True


class TranscriptionMetrics(BaseModel):
    """Metrics for a transcription operation."""
    
    request_id: str
    duration_ms: float
    audio_size_bytes: int
    retry_count: int
    success: bool
    timestamp: datetime
    model: str
    
    class Config:
        from_attributes = True
