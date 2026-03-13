from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = (
        "postgresql+asyncpg://user:password@localhost:5432/market_events"
    )

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Cache
    cache_ttl_seconds: int = 300  # 5 minutes

    # Sync
    sync_cooldown_seconds: int = 3600  # 1 hour

    # Provider keys
    provider_a_api_key: str = "test-key"
    provider_b_api_key: str = "test-key"

    # Application
    log_level: str = "INFO"
    env: str = "development"


settings = Settings()
