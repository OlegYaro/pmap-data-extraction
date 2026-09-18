from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DB_URL: str
    DB_POOL_SIZE: int = 5
    REDIS_URL: str
    SOURCE_BASE_URL: str = (
        "https://opendata.geoportal.gov.pl/InneDane/latest_exports/rcn_transakcje_ceny"
    )
    SOURCE_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    DOWNLOAD_DIR: Path = Path("data/rcn")
    DOWNLOAD_CONCURRENCY: int = 4
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
