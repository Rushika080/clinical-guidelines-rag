"""
GET /api/guidelines        — list all registered guidelines
GET /api/guidelines/{id}   — get single guideline metadata
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(tags=["guidelines"])


class GuidelineMetaResponse(BaseModel):
    guideline_id:    str
    title:           str
    organization:    str
    specialty:       str
    publication_year: Optional[int]  = None
    version:         Optional[str]   = None
    source_url:      Optional[str]   = None
    evidence_system: Optional[str]   = None
    last_updated:    Optional[str]   = None
    document_type:   str             = "clinical_guideline"


class GuidelinesListResponse(BaseModel):
    total:      int
    guidelines: list[GuidelineMetaResponse]


@router.get(
    "/guidelines",
    response_model=GuidelinesListResponse,
    summary="List all registered guidelines",
    description="Returns metadata for all guidelines registered in the registry.",
)
async def list_guidelines() -> GuidelinesListResponse:
    from ingestion.metadata.registry import load_registry
    guidelines = load_registry()
    return GuidelinesListResponse(
        total=len(guidelines),
        guidelines=[
            GuidelineMetaResponse(**g.to_dict())
            for g in guidelines
        ],
    )


@router.get(
    "/guidelines/{guideline_id}",
    response_model=GuidelineMetaResponse,
    summary="Get a single guideline by ID",
)
async def get_guideline(guideline_id: str) -> GuidelineMetaResponse:
    from ingestion.metadata.registry import get_guideline_by_id
    meta = get_guideline_by_id(guideline_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guideline '{guideline_id}' not found in registry.",
        )
    return GuidelineMetaResponse(**meta.to_dict())