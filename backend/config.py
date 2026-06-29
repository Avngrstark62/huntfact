from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SectionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")


class AppSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="APP_")
    name: str = "HuntFact API"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000


class AuthSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="AUTH_")
    disable: bool = False
    supabase_jwks_url: str = ""
    supabase_issuer: str = ""
    supabase_audience: str | None = None


class DatabaseSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="DATABASE_")
    url: str

class OpenAISettings(SectionSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_prefix="OPENAI_",
    )
    api_key: str


class RabbitMQSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="RABBITMQ_")
    url: str = "amqp://guest:guest@localhost:5672/"
    task_queue_name: str = "task_queue"
    workflow_queue_name: str = "workflow_queue"
    dead_letter_exchange_name: str = "huntfact.dead_letter"
    task_dead_letter_queue_name: str = "task_queue.dead_letter"
    workflow_dead_letter_queue_name: str = "workflow_queue.dead_letter"
    task_dead_letter_routing_key: str = "task.dead_letter"
    workflow_dead_letter_routing_key: str = "workflow.dead_letter"
    max_priority: int = 20
    prefetch_count: int = 1

class AssemblyAISettings(SectionSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_prefix="ASSEMBLYAI_",
    )
    api_key: str

class LLMSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="LLM_")
    reasoning_model: str = "gpt-4.1"
    cheap_model: str = "gpt-4.1-nano"
    debug: bool = False


class SearXNGSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="SEARXNG_")
    url: str = "http://localhost:8080/search"
    timeout: int = 10


class ChromaDBSettings(SectionSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_prefix="CHROMADB_",
    )
    host: str = "localhost"
    port: int = 9275


class FirebaseSettings(SectionSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow", env_prefix="FIREBASE_")
    credentials_path: str = "serviceAccountKey.json"


class FirecrawlSettings(SectionSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_prefix="FIRECRAWL_",
    )
    api_url: str = "https://firecrawl.huntfact.com"
    api_key: str = ""


class WorkflowAdmissionSettings(SectionSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_prefix="WORKFLOW_ADMISSION_",
    )
    retry_count: int = 3
    retry_base_delay_ms: int = 300


class WorkflowCleanupSettings(SectionSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_prefix="WORKFLOW_CLEANUP_",
    )
    processing_stale_minutes: int = 5
    queued_stale_minutes: int = 30
    interval_seconds: int = 30


class SecuritySettings(SectionSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_prefix="SECURITY_",
    )
    allowed_cdn_host_suffixes: list[str] = ["fbcdn.net", "cdninstagram.com"]


class LoggingSettings(SectionSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_prefix="LOG_",
    )
    level: str = "INFO"
    format: str = "text"
    include_source: bool = False
    service_name: str = "huntfact-backend"
    log_dir: str = "logs"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        extra="allow",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)
    assemblyai: AssemblyAISettings = Field(default_factory=AssemblyAISettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    searxng: SearXNGSettings = Field(default_factory=SearXNGSettings)
    chromadb: ChromaDBSettings = Field(default_factory=ChromaDBSettings)
    firebase: FirebaseSettings = Field(default_factory=FirebaseSettings)
    firecrawl: FirecrawlSettings = Field(default_factory=FirecrawlSettings)
    workflow_admission: WorkflowAdmissionSettings = Field(default_factory=WorkflowAdmissionSettings)
    workflow_cleanup: WorkflowCleanupSettings = Field(default_factory=WorkflowCleanupSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

settings = Settings()
