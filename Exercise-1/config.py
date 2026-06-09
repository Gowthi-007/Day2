from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./inventory.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Lock and reservation timeouts
    LOCK_ACQUIRE_TIMEOUT_SECONDS: float = 2.0
    RESERVATION_TTL_SECONDS: int = 900  # 15 minutes
    
    # Connection pools
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    REDIS_SOCKET_TIMEOUT: int = 5
    
    APP_NAME: str = "inventory-reservation-system"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
