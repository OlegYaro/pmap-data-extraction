from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DB_URL: str
    DB_POOL_SIZE: int = 5
    REDIS_URL: str
    DOWNLOAD_DIR: Path = Path("data/rcn")
    DOWNLOAD_CONCURRENCY: int = 4
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
