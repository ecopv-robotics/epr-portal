from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EPR Portal API"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://epr:epr_dev_password@localhost:5432/epr_portal"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://localhost:5174"
    storage_path: str = "storage"
    max_upload_size_mb: int = 20
    openai_api_key: str | None = None
    openai_translation_model: str = "gpt-5-mini"

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
