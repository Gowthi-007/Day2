from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    
    # AI Provider endpoints
    PRIMARY_AI_PROVIDER_URL: str = "http://127.0.0.1:8002/summarize"
    BACKUP_AI_PROVIDER_URL: str = "http://127.0.0.1:8002/summarize"
    
    # Primary provider API key (in production, use secrets management)
    PRIMARY_AI_API_KEY: str = "sk-primary-key"
    BACKUP_AI_API_KEY: str = "sk-backup-key"
    
    # Timeout and rate limiting
    AI_CALL_TIMEOUT_SECONDS: float = 5.0
    RATE_LIMIT_TOKENS_PER_MINUTE: int = 10000
    CACHE_TTL_SECONDS: int = 3600  # 1 hour
    
    # Circuit breaker configuration
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS: int = 60
    
    APP_NAME: str = "ai-gateway"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
