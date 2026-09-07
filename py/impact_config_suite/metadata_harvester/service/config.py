from __future__ import annotations

from typing import Optional

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Env-driven settings for the Metadata Harvester tab's embedded service."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="METADATA_HARVESTER_", extra="ignore")

    db_path: str = "metadata_harvester.db"
    contact_email: Optional[EmailStr] = None
    num_workers: int = 6
    request_timeout_seconds: float = 30.0
    ror_max_pages: int = 5
    ror_page_delay_seconds: float = 0.15
    log_dir: str = "logs"
    log_level: str = "INFO"


settings = Settings()
