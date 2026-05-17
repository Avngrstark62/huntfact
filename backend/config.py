from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SectionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")


class AppSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="APP_")
    app_name: str = "HuntFact API"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000


class AuthSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="AUTH_")
    disable_auth: bool = False
    supabase_jwks_url: str = ""
    supabase_issuer: str = ""
    supabase_audience: str | None = None


class DatabaseSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="DATABASE_")
    url: str


class RmqSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="RMQ_")
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    task_queue_name: str = "task_queue"
    workflow_queue_name: str = "workflow_queue"
    max_priority: int = 20
    prefetch_count: int = 1


class TranscriptionSettings(SectionSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_prefix="TRANSCRIPTION_",
    )
    deepgram_api_key: str = "deepgram_api_key"
    assemblyai_api_key: str = "assemblyai_api_key"
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    azure_speech_language: str = "en-US"
    azure_transcription_timeout_seconds: int = 300
    azure_speech_batch_api_version: str = "v3.2"
    azure_batch_poll_interval_seconds: int = 5
    azure_batch_input_container_sas_url: str = ""


class ModelsSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="MODELS_")
    reasoning_model: str = "gpt-4.1"
    cheap_model: str = "gpt-4.1-nano"
    llm_debug: bool = False


class SearchSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="SEARCH_")
    searxng_search_url: str = "http://localhost:8080/search"
    searxng_timeout_seconds: int = 10


class VectorStoreSettings(SectionSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_prefix="VECTOR_STORE_",
    )
    chroma_host: str = "localhost"
    chroma_port: int = 9275


class FirebaseSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="FIREBASE_")
    firebase_credentials_path: str = "serviceAccountKey.json"


class ExternalApisSettings(SectionSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_prefix="EXTERNAL_APIS_",
    )
    openai_api_key: str
    firecrawl_api_url: str = "https://firecrawl.huntfact.com"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        extra="allow",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    rmq: RmqSettings = Field(default_factory=RmqSettings)
    transcription: TranscriptionSettings = Field(default_factory=TranscriptionSettings)
    models: ModelsSettings = Field(default_factory=ModelsSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    firebase: FirebaseSettings = Field(default_factory=FirebaseSettings)
    external_apis: ExternalApisSettings = Field(default_factory=ExternalApisSettings)


app_settings = Settings()
settings = app_settings
