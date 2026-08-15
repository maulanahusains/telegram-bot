from __future__ import annotations

from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.health import router as health_router
from app.api.user_auth import router as user_auth_router
from app.api.webhook import router as webhook_router
from app.modules.life.api import router as life_router
from app.core.config import get_settings
from app.core.lifespan import lifespan
from app.core.middleware import RequestContextMiddleware, install_exception_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env == "development" else None,
    )
    application.add_middleware(RequestContextMiddleware)
    install_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(admin_router)
    application.include_router(user_auth_router)
    application.include_router(life_router)
    application.include_router(webhook_router)
    return application


app = create_app()
