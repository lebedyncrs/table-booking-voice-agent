from functools import cache
from typing import Literal

from pydantic.functional_validators import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings.main import SettingsConfigDict

from gas.core.schema import Schema


class RedisSettings(Schema):
    HOST: str
    PORT: int = 6379
    DB: int = 0
    PASSWORD: str | None = None


class SettingsSchema(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", frozen=True, case_sensitive=True)

    LOG_LEVEL: Literal["debug", "info", "warn", "error", "critical"] = "debug"
    PROXY_PATH_PREFIX: str = ""
    REDIS: RedisSettings
    GOOGLE_MAPS_API_KEY: str
    SENTRY_DSN: str | None = None
    ENVIRONMENT: str = "local"

    @field_validator("PROXY_PATH_PREFIX")
    @staticmethod
    def validate_proxy_path_prefix(value: str):
        if value and not value.startswith("/"):
            return f"/{value}"
        return value


@cache
def get_settings() -> SettingsSchema:
    return SettingsSchema()  # type: ignore
