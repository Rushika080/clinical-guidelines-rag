"""
FastAPI application entry point.
All routes registered here.
LangSmith tracing activates automatically when
LANGCHAIN_TRACING_V2=true in .env — no extra code needed.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting Clinical Guidelines RAG — env={settings.app_env}")

    # Set LangSmith env vars from settings at startup
    if settings.langchain_api_key:
        os.environ["LANGCHAIN_API_KEY"]       = settings.langchain_api_key
        os.environ["LANGCHAIN_TRACING_V2"]    = settings.langchain_tracing_v2
        os.environ["LANGCHAIN_PROJECT"]       = settings.langchain_project
        logger.info(
            f"LangSmith tracing: {settings.langchain_tracing_v2} "
            f"project='{settings.langchain_project}'"
        )
    else:
        logger.info("LangSmith tracing disabled (no API key set).")

    yield
    logger.info("Shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Clinical Guidelines Assistant",
        description=(
            "Evidence-grounded retrieval over indexed clinical guidelines. "
            "NOT a diagnostic or treatment decision system. "
            "For informational and educational use only."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register all routers
    from app.api.routes.health     import router as health_router
    from app.api.routes.query      import router as query_router
    from app.api.routes.ingest     import router as ingest_router
    from app.api.routes.guidelines import router as guidelines_router

    app.include_router(health_router,     prefix="/api")
    app.include_router(query_router,      prefix="/api")
    app.include_router(ingest_router,     prefix="/api")
    app.include_router(guidelines_router, prefix="/api")

    return app


app = create_app()