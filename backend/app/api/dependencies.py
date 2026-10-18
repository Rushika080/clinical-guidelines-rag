"""
Shared FastAPI dependencies.

Using FastAPI's dependency injection keeps route handlers clean —
they receive already-validated objects rather than re-reading
settings or constructing clients themselves.
"""

import logging
from functools import lru_cache
from fastapi import Header, HTTPException, status
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_app_settings():
    """Inject application settings into route handlers."""
    return get_settings()


async def verify_content_type(content_type: str = Header(default="application/json")):
    """
    Ensure POST requests carry JSON content type.
    Raises 415 Unsupported Media Type if not.
    """
    if "application/json" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Content-Type must be application/json",
        )