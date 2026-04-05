from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "HuntFact API"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    queue_name: str = "task_queue"
    max_priority: int = 10
    prefetch_count: int = 1

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
