"""Settings, read from environment variables prefixed with AP_ (or backend/.env)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AP_", env_file=BACKEND_DIR / ".env", extra="ignore"
    )

    database_url: str = (
        "postgresql+psycopg://automation:automation@localhost:5450/automation_portal"
    )
    # Default data folder (Data/ next to backend/). Admins can change it from the portal's Settings
    # screen; that choice is kept in the database and wins over this value.
    data_root: str = str(BACKEND_DIR.parent / "Data")
    # Uploads not used in a run are deleted after this many days.
    upload_keep_days: int = 7
    # Names the date and time folders under the data folder.
    timezone: str = "Asia/Bahrain"
    # Key for encrypting connector credentials (Fernet, urlsafe base64, 32 bytes).
    secret_key: str = "ZGV2LW9ubHkta2V5LWNoYW5nZS1tZS1wbGVhc2UhISE="
    cors_origins: list[str] = ["http://localhost:3500"]
    # True runs workflows inside the API process instead of the worker (tests, quick dev).
    run_inline: bool = False
    preview_row_limit: int = 1000
    max_upload_mb: int = 200

    @property
    def libpq_url(self) -> str:
        """The same database URL without the SQLAlchemy driver suffix (used by Procrastinate)."""
        return self.database_url.replace("postgresql+psycopg://", "postgresql://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
