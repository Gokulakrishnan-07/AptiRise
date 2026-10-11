import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AptiRise"
    APP_ENV: str = "development"
    SECRET_KEY: str = "aptirise-dev-secret-key-32-chars-minimum-security-token"
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Database
    DATABASE_URL: str = "sqlite:///./aptirise.db"

    # AI Integration (Hugging Face)
    HF_TOKEN: Optional[str] = ""

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = ""
    GOOGLE_CLIENT_SECRET: Optional[str] = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # Initial Admin Bootstrap
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@aptirise.internal"
    ADMIN_PASSWORD: str = "AdminSecurePass123!"

    # Game Mechanics Defaults
    DEFAULT_TIMER_SECONDS: int = 45
    BASE_CORRECT_XP: int = 100
    SPEED_BONUS_UNDER_50: int = 50
    SPEED_BONUS_UNDER_25: int = 100
    PERFECT_LEVEL_BONUS_XP: int = 250
    DAILY_CHALLENGE_BONUS_XP: int = 500
    MAX_UPLOAD_SIZE_MB: int = 25

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
