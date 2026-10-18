"""
Pydantic request schemas for the API.
"""

from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    """
    Request body for POST /api/query.

    Filters are optional — the system works without them but
    they improve retrieval precision when the user knows the source.
    """
    question: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="The clinical question to answer.",
        examples=["What does ADA recommend for HbA1c targets in adults?"],
    )
    specialty: Optional[str] = Field(
        None,
        description="Filter by medical specialty (e.g. 'diabetes', 'cardiology').",
    )
    organization: Optional[str] = Field(
        None,
        description="Filter by issuing organization (e.g. 'American Diabetes Association').",
    )
    year: Optional[int] = Field(
        None,
        ge=1990,
        le=2030,
        description="Filter by publication year.",
    )
    guideline_id: Optional[str] = Field(
        None,
        description="Filter by specific guideline ID for precise retrieval.",
    )