"""Application configuration via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from env vars / .env file.

    Constants for the Hinge / Sendbird API surface plus runtime concerns
    (DB URL, debug flag, default phone). Values are sourced from environment
    variables and `.env` (env vars win).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Hinge API constants ---
    BASE_URL: str = "https://prod-api.hingeaws.net"
    HINGE_APP_VERSION: str = "9.82.0"
    HINGE_BUILD_NUMBER: str = "11616"
    OS_VERSION: str = "26.0"

    # --- Sendbird (chat) constants ---
    SENDBIRD_APP_ID: str = "3CDAD91C-1E0D-4A0D-BBEE-9671988BF9E9"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///hinge.db"

    # --- Auth defaults ---
    HINGE_PHONE_NUMBER: str = ""

    # --- Debug ---
    DEBUG: bool = True

    @property
    def SENDBIRD_API_URL(self) -> str:  # noqa: N802 — keeps existing call sites stable
        """Sendbird REST base URL derived from the app ID."""
        return f"https://api-{self.SENDBIRD_APP_ID.lower()}.sendbird.com"

    @property
    def SENDBIRD_WS_URL(self) -> str:  # noqa: N802
        """Sendbird WebSocket base URL derived from the app ID."""
        return f"wss://ws-{self.SENDBIRD_APP_ID.lower()}.sendbird.com"


@lru_cache
def get_settings() -> Settings:
    """Singleton settings instance."""
    return Settings()
