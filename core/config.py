from functools import lru_cache
import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = Field(default="Saarthi AI")
    app_description: str = Field(default="Multi-agent personal intelligence system.")
    app_version: str = Field(default="1.0.0")
    app_env: str = Field(default="development")
    app_log_level: str = Field(default="INFO")
    default_user_id: str = Field(default="chjoshna145@gmail.com")
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])


class DBSettings(BaseModel):
    debug: bool = Field(default=False)

    # Direct DB connection settings
    db_host: str = Field(default="")
    db_port: int = Field(default=5432)
    db_user: str = Field(default="")
    db_pass: str = Field(default="")
    db_name: str = Field(default="")
    db_ssl: bool = Field(default=False)

    # Pool/connect tuning
    db_connect_timeout_seconds: float = Field(default=10.0)
    db_pool_min_size: int = Field(default=1)
    db_pool_max_size: int = Field(default=10)
    db_pool_max_idle_seconds: float = Field(default=300.0)
    db_pool_acquire_timeout_seconds: float = Field(default=10.0)
    db_retry_attempts: int = Field(default=3)

    def validate_for_startup(self) -> None:
        direct_fully_configured = bool(self.db_host and self.db_user and self.db_name)

        if not direct_fully_configured:
            raise ValueError(
                "Direct DB connection requires DB_HOST, DB_USER, and DB_NAME."
            )

        if self.db_pool_min_size < 1:
            raise ValueError("DB_POOL_MIN_SIZE must be >= 1.")
        if self.db_pool_max_size < self.db_pool_min_size:
            raise ValueError("DB_POOL_MAX_SIZE must be >= DB_POOL_MIN_SIZE.")
        if self.db_connect_timeout_seconds <= 0:
            raise ValueError("DB_CONNECT_TIMEOUT_SECONDS must be > 0.")
        if self.db_pool_acquire_timeout_seconds <= 0:
            raise ValueError("DB_POOL_ACQUIRE_TIMEOUT_SECONDS must be > 0.")
        if self.db_retry_attempts < 1:
            raise ValueError("DB_RETRY_ATTEMPTS must be >= 1.")


def _parse_csv_env(name: str, fallback: list[str]) -> list[str]:
    value = os.getenv(name, "").strip()
    if not value:
        return fallback
    parsed = [item.strip() for item in value.split(",") if item.strip()]
    return parsed or fallback


def _parse_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


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
            "DEFAULT_USER_ID", "chjoshna145@gmail.com"
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


@lru_cache(maxsize=1)
def get_db_settings() -> DBSettings:
    settings = DBSettings(
        debug=_parse_bool_env("DB_DEBUG", default=False),
        db_host=os.getenv("DB_HOST", "").strip(),
        db_port=int(os.getenv("DB_PORT", "5432").strip() or "5432"),
        db_user=os.getenv("DB_USER", "").strip(),
        db_pass=os.getenv("DB_PASS", "").strip(),
        db_name=os.getenv("DB_NAME", "").strip(),
        db_ssl=_parse_bool_env("DB_SSL", default=False),
        db_connect_timeout_seconds=float(
            os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "10").strip() or "10"
        ),
        db_pool_min_size=int(os.getenv("DB_POOL_MIN_SIZE", "1").strip() or "1"),
        db_pool_max_size=int(os.getenv("DB_POOL_MAX_SIZE", "10").strip() or "10"),
        db_pool_max_idle_seconds=float(
            os.getenv("DB_POOL_MAX_IDLE_SECONDS", "300").strip() or "300"
        ),
        db_pool_acquire_timeout_seconds=float(
            os.getenv("DB_POOL_ACQUIRE_TIMEOUT_SECONDS", "10").strip() or "10"
        ),
        db_retry_attempts=int(os.getenv("DB_RETRY_ATTEMPTS", "3").strip() or "3"),
    )
    return settings
