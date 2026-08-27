from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "AI Data Analyst"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://ai_data_analyst:password@localhost:5432/ai_data_analyst"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Uploads
    MAX_UPLOAD_SIZE_MB: int = 20
    MAX_ROWS_PER_DATASET: int = 200_000
    PREVIEW_ROWS: int = 25

    # AI
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_MAX_TOKENS: int = 1024
    GROQ_TIMEOUT_SECONDS: int = 60

    # Storage
    STORAGE_DIR: Path = BACKEND_DIR / "storage"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
