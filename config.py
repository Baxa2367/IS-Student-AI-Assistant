from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Central app settings loaded from environment variables."""
    GEMINI_API_KEY: str
    GEMINI_MODEL: str
    APP_DB_PATH: str


def get_settings() -> Settings:
    """Read settings from environment with safe defaults."""
    return Settings(
        GEMINI_API_KEY=os.getenv("GEMINI_API_KEY", "").strip(),
        GEMINI_MODEL=os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip(),
        APP_DB_PATH=os.getenv("APP_DB_PATH", "app_data.db").strip(),
    )