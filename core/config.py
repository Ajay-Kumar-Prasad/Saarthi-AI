from functools import lru_cache
import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = Field(default="Saarthi AI")
    app_description: str = Field(default="Multi-agent personal intelligence system.")
    app_version: str = Field(default="1.0.0")
    app_env: str = Field(default="development")
    app_log_level: str = Field(default="INFO")
    default_user_id: str = Field(default="00000000-0000-0000-0000-000000000001")
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])


def _parse_csv_env(name: str, fallback: list[str]) -> list[str]:
    value = os.getenv(name, "").strip()
    if not value:
        return fallback
    parsed = [item.strip() for item in value.split(",") if item.strip()]
    return parsed or fallback


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings(
        app_name=os.getenv("APP_NAME", "Saarthi AI"),
        app_description=os.getenv(
            "APP_DESCRIPTION",
            "Multi-agent personal intelligence system.",
        ),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        app_env=os.getenv("APP_ENV", "development"),
        app_log_level=os.getenv("APP_LOG_LEVEL", "INFO").upper(),
        default_user_id=os.getenv(
            "DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000001"
        ),
        cors_allow_origins=_parse_csv_env("CORS_ALLOW_ORIGINS", ["*"]),
        cors_allow_methods=_parse_csv_env("CORS_ALLOW_METHODS", ["*"]),
        cors_allow_headers=_parse_csv_env("CORS_ALLOW_HEADERS", ["*"]),
    )
    if settings.app_env.lower() == "production" and (
        "*" in settings.cors_allow_origins
        or "*" in settings.cors_allow_methods
        or "*" in settings.cors_allow_headers
    ):
        raise ValueError(
            "Wildcard CORS values are not allowed in production. "
            "Set explicit CORS_ALLOW_ORIGINS/CORS_ALLOW_METHODS/CORS_ALLOW_HEADERS."
        )
    return settings
