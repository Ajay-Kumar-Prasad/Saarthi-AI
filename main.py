from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

load_dotenv()
settings = get_settings()
configure_logging(settings.app_log_level)


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
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, __: Exception):
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

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
