from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DB_URL: str
    DB_POOL_SIZE: int = 5
    REDIS_URL: str
    DOWNLOAD_DIR: Path = Path("data/rcn")
    DOWNLOAD_CONCURRENCY: int = 4
    LOG_LEVEL: str = "INFO"
    S3_BUCKET_RAW: str | None = None
    S3_REGION: str = "eu-north-1"
    # Clients send it in the X-API-Key header. Not set: every endpoint except
    # /health answers 503, so a missing key never leaves the API open.
    API_KEY: SecretStr | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
