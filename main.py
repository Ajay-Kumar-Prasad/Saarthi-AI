import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth.google_oauth import router as auth_router
from core.config import get_settings
from core.logging import configure_logging
from routers.finance import router as finance_router
from routers.health import router as health_router
from routers.learning import router as learning_router
from routers.orchestrator import router as orchestrator_router
from routers.social import router as social_router
from routers.system import router as system_router
from routers.work import router as work_router

if os.getenv("APP_ENV", "development").lower() != "production":
    load_dotenv()
settings = get_settings()
configure_logging(settings.app_log_level)
logger = logging.getLogger("saarthi.api")


class ErrorResponse(BaseModel):
    detail: str
    error_type: str


def _error_payload(detail: str, error_type: str) -> dict:
    return ErrorResponse(detail=detail, error_type=error_type).model_dump()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(_: Request, exc: RequestValidationError):
        logger.warning("Request validation failed: %s", exc.errors())
        return JSONResponse(
            status_code=422,
            content=_error_payload("Request validation failed.", "validation_error"),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        logger.warning("HTTP exception raised: status=%s detail=%s", exc.status_code, exc.detail)
        detail = str(exc.detail) if exc.detail else "HTTP error"
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(detail, "http_error"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        logger.exception("Unhandled exception in API", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_error_payload("Internal server error", "internal_error"),
        )

    app.include_router(auth_router)
    app.include_router(system_router)
    app.include_router(orchestrator_router)
    app.include_router(learning_router)
    app.include_router(work_router)
    app.include_router(health_router)
    app.include_router(finance_router)
    app.include_router(social_router)

    return app


app = create_app()
