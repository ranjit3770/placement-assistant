from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "staging", "production"] = "development"
    database_url: SecretStr
    redis_url: SecretStr
    qdrant_url: str
    embedding_provider_url: str = "http://dummy"
    embedding_model: str = "dummy-model"
    embedding_dimensions: int = 1536
    embedding_api_key: str | None = None
    jwt_secret: SecretStr
    jwt_issuer: str = "placement-api"
    jwt_audience: str = "placement-web"
    dependency_timeout_seconds: float = Field(default=2, gt=0, le=10)

    @field_validator("jwt_secret")
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database(cls, value: SecretStr) -> SecretStr:
        if make_url(value.get_secret_value()).drivername != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        return value

    @field_validator("qdrant_url")
    @classmethod
    def validate_qdrant(cls, value: str) -> str:
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("QDRANT_URL must be an HTTP(S) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("QDRANT_URL must not contain credentials, query or fragment")
        return value.rstrip("/")
