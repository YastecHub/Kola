from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.endpoints import groups, scores, webhooks
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="KOLA Backend",
        description="Core API for KOLA, Nigeria's informal credit bureau for Ajo groups.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(groups.router, prefix="/api/groups", tags=["groups"])
    app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
    app.include_router(scores.router, prefix="/api/scores", tags=["scores"])

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        logger.debug("Health check requested")
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
