"""Settings for the application."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # --- Constants & Configuration ---
    # You didn't think I'd hardcode this shit, did you?
    BASE_URL: str = "https://prod-api.hingeaws.net"
    SENDBIRD_APP_ID: str = "3CDAD91C-1E0D-4A0D-BBEE-9671988BF9E9"
    SENDBIRD_API_URL: str = f"https://api-{SENDBIRD_APP_ID.lower()}.sendbird.com"
    SENDBIRD_WS_URL: str = f"wss://ws-{SENDBIRD_APP_ID.lower()}.sendbird.com"
    HINGE_APP_VERSION: str = "9.82.0"
    HINGE_BUILD_NUMBER: str = "11616"
    OS_VERSION: str = "26.0"
    
    # Debug configuration
    DEBUG: bool = True


@lru_cache()
def get_settings() -> Settings:
    """Get app settings.

    Returns:
        Settings: (Settings) App settings

    """
    return Settings()
