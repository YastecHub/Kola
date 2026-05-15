from __future__ import annotations

from app.core.runtime import configure_windows_event_loop

configure_windows_event_loop()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from loguru import logger

from app.api.endpoints import groups, scores, squad, webhooks
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="KOLA Backend",
        description="Core API for KOLA, Nigeria's informal credit bureau for Ajo groups.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(groups.router, prefix="/api/groups", tags=["groups"])
    app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
    app.include_router(scores.router, prefix="/api/scores", tags=["scores"])
    app.include_router(squad.router, prefix="/api/squad", tags=["squad"])

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        logger.debug("Health check requested")
        return {"status": "ok", "environment": settings.environment}

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": "KOLA Backend",
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    @app.get("/api/docs", include_in_schema=False)
    async def api_docs_redirect() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app


app = create_app()
