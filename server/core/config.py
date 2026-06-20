"""Server configuration management."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    """Server configuration (Pydantic model)."""

    model_config = SettingsConfigDict(
        env_prefix="TUX_SERVER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 18420
    debug: bool = False

    # CORS
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:18422",
            "http://127.0.0.1:18422",
        ]
    )

    # Security
    secret_key: str = Field(default="change-me-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # File storage
    storage_dir: Path = Path("./wallpapers")
    thumbnails_dir: Path = Path("./wallpapers/thumbnails")
    temp_dir: Path = Path("./temp")
    max_upload_size: int = 500 * 1024 * 1024  # 500 MB

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    def ensure_directories(self) -> None:
        """Create necessary directories on startup."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


_settings: Optional[ServerSettings] = None


def get_settings() -> ServerSettings:
    """Get singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = ServerSettings()
        _settings.ensure_directories()
    return _settings
