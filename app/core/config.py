from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "temple-identity-service"
    environment: str = "dev"
    database_url: str = "sqlite:///./temple_identity.db"
    jwt_secret: str = "change-me"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
