from pydantic import BaseSettings, AnyUrl


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    REDIS_URL: AnyUrl = "redis://localhost:6379/0"
    REDIS_LOCK_TTL_SECONDS: int = 86400
    APP_NAME: str = "stripe-webhook-processor"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
