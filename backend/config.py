from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "HuntFact API"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    queue_name: str = "task_queue"
    max_priority: int = 20
    prefetch_count: int = 1

    google_api_key: str
    openai_api_key: str

    # Transcriber service settings
    transcriber_model: str = "gpt-4o-audio-preview"
    transcriber_max_retries: int = 3
    transcriber_retry_delay_seconds: float = 1.0
    transcriber_max_retry_delay_seconds: float = 32.0
    transcriber_request_timeout_seconds: int = 300
    transcriber_max_audio_size_mb: int = 25
    transcriber_supported_formats: list[str] = [
        "mp3", "aac", "wav", "flac", "ogg", "m4a"
    ]
    deepgram_api_key: str = "deepgram_api_key"
    assemblyai_api_key: str = "assemblyai_api_key"

    # Claim extraction service settings
    claim_extraction_model_provider: str = "openai"
    claim_extraction_model_name: str = "gpt-4o-mini"

    # Reasoning model service settings
    reasoning_model_provider: str = "openai"
    reasoning_model_name: str = "gpt-4o-mini"

    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # ChromaDB settings
    chroma_host: str = "localhost"
    chroma_port: int = 9275

    # Firebase settings
    firebase_credentials_path: str = "serviceAccountKey.json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
