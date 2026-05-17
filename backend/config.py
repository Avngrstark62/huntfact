from functools import cached_property

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class AppConfig(BaseModel):
    app_name: str
    debug: bool
    host: str
    port: int


class AuthConfig(BaseModel):
    disable_auth: bool
    supabase_jwks_url: str
    supabase_issuer: str
    supabase_audience: str | None


class DatabaseConfig(BaseModel):
    database_url: str


class RmqConfig(BaseModel):
    rabbitmq_url: str
    task_queue_name: str
    workflow_queue_name: str
    max_priority: int
    prefetch_count: int


class TranscriptionConfig(BaseModel):
    deepgram_api_key: str
    assemblyai_api_key: str
    azure_speech_key: str
    azure_speech_region: str
    azure_speech_language: str
    azure_transcription_timeout_seconds: int
    azure_speech_batch_api_version: str
    azure_batch_poll_interval_seconds: int
    azure_batch_input_container_sas_url: str


class ModelConfig(BaseModel):
    reasoning_model: str
    cheap_model: str
    llm_debug: bool


class SearchConfig(BaseModel):
    searxng_search_url: str
    searxng_timeout_seconds: int


class VectorStoreConfig(BaseModel):
    chroma_host: str
    chroma_port: int


class FirebaseConfig(BaseModel):
    firebase_credentials_path: str


class ExternalApisConfig(BaseModel):
    openai_api_key: str
    firecrawl_api_url: str


class Settings(BaseSettings):
    app_name: str = "HuntFact API"
    debug: bool = False
    disable_auth: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str
    supabase_jwks_url: str = ""
    supabase_issuer: str = ""
    supabase_audience: str | None = None

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    task_queue_name: str = "task_queue"
    workflow_queue_name: str = "workflow_queue"
    max_priority: int = 20
    prefetch_count: int = 1

    openai_api_key: str
    firecrawl_api_url: str = "https://firecrawl.huntfact.com"

    deepgram_api_key: str = "deepgram_api_key"
    assemblyai_api_key: str = "assemblyai_api_key"
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    azure_speech_language: str = "en-US"
    azure_transcription_timeout_seconds: int = 300
    azure_speech_batch_api_version: str = "v3.2"
    azure_batch_poll_interval_seconds: int = 5
    azure_batch_input_container_sas_url: str = ""

    # Model settings
    # reasoning_model: str = "gpt-4o-mini"
    reasoning_model: str = "gpt-4.1"
    cheap_model: str = "gpt-4.1-nano"
    # cheap_model: str = "gpt-4o-mini"
    llm_debug: bool = False

    # URL fetcher (SearxNG) settings
    searxng_search_url: str = "http://localhost:8080/search"
    searxng_timeout_seconds: int = 10

    # ChromaDB settings
    chroma_host: str = "localhost"
    chroma_port: int = 9275

    # Firebase settings
    firebase_credentials_path: str = "serviceAccountKey.json"

    @cached_property
    def app(self) -> AppConfig:
        return AppConfig(
            app_name=self.app_name,
            debug=self.debug,
            host=self.host,
            port=self.port,
        )

    @cached_property
    def auth(self) -> AuthConfig:
        return AuthConfig(
            disable_auth=self.disable_auth,
            supabase_jwks_url=self.supabase_jwks_url,
            supabase_issuer=self.supabase_issuer,
            supabase_audience=self.supabase_audience,
        )

    @cached_property
    def database(self) -> DatabaseConfig:
        return DatabaseConfig(database_url=self.database_url)

    @cached_property
    def rmq(self) -> RmqConfig:
        return RmqConfig(
            rabbitmq_url=self.rabbitmq_url,
            task_queue_name=self.task_queue_name,
            workflow_queue_name=self.workflow_queue_name,
            max_priority=self.max_priority,
            prefetch_count=self.prefetch_count,
        )

    @cached_property
    def transcription(self) -> TranscriptionConfig:
        return TranscriptionConfig(
            deepgram_api_key=self.deepgram_api_key,
            assemblyai_api_key=self.assemblyai_api_key,
            azure_speech_key=self.azure_speech_key,
            azure_speech_region=self.azure_speech_region,
            azure_speech_language=self.azure_speech_language,
            azure_transcription_timeout_seconds=self.azure_transcription_timeout_seconds,
            azure_speech_batch_api_version=self.azure_speech_batch_api_version,
            azure_batch_poll_interval_seconds=self.azure_batch_poll_interval_seconds,
            azure_batch_input_container_sas_url=self.azure_batch_input_container_sas_url,
        )

    @cached_property
    def models(self) -> ModelConfig:
        return ModelConfig(
            reasoning_model=self.reasoning_model,
            cheap_model=self.cheap_model,
            llm_debug=self.llm_debug,
        )

    @cached_property
    def search(self) -> SearchConfig:
        return SearchConfig(
            searxng_search_url=self.searxng_search_url,
            searxng_timeout_seconds=self.searxng_timeout_seconds,
        )

    @cached_property
    def vector_store(self) -> VectorStoreConfig:
        return VectorStoreConfig(
            chroma_host=self.chroma_host,
            chroma_port=self.chroma_port,
        )

    @cached_property
    def firebase(self) -> FirebaseConfig:
        return FirebaseConfig(firebase_credentials_path=self.firebase_credentials_path)

    @cached_property
    def external_apis(self) -> ExternalApisConfig:
        return ExternalApisConfig(
            openai_api_key=self.openai_api_key,
            firecrawl_api_url=self.firecrawl_api_url,
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
