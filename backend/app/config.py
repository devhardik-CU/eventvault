"""Application settings, read from environment variables (or a local .env file)."""
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEV_KEY = "dev-only-insecure-key-change-me-0123456789"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"  # development | production | test
    database_url: str = "sqlite:///./eventvault.db"
    secret_key: str = INSECURE_DEV_KEY
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173"

    storage_backend: str = "local"  # local | azure
    upload_dir: str = "./uploads"
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "event-posters"
    max_upload_bytes: int = 2 * 1024 * 1024

    @field_validator("storage_backend")
    @classmethod
    def _check_backend(cls, v: str) -> str:
        if v not in ("local", "azure"):
            raise ValueError("STORAGE_BACKEND must be 'local' or 'azure'")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_for_runtime(self) -> None:
        """Fail fast on unsafe production configuration."""
        if self.environment == "production":
            if self.secret_key == INSECURE_DEV_KEY or len(self.secret_key) < 32:
                raise RuntimeError("SECRET_KEY must be set to a random value of 32+ characters in production.")
            if "*" in self.cors_origin_list:
                raise RuntimeError("CORS_ORIGINS must not contain '*' in production.")
        if self.storage_backend == "azure" and not self.azure_storage_connection_string:
            raise RuntimeError("STORAGE_BACKEND=azure requires AZURE_STORAGE_CONNECTION_STRING.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
