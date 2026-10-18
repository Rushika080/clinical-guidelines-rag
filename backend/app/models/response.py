"""
Pydantic response schemas.

These define the contract between backend and frontend.
Every field is typed and documented — no silent None values
slipping through to the UI.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ScopeStatus(str, Enum):
    """
    Whether the question is answerable from indexed guidelines.

    SUPPORTED:           Evidence found, answer generated.
    INSUFFICIENT:        Guidelines indexed but evidence too sparse.
    OUT_OF_SCOPE:        Question is outside clinical guideline scope
                         (diagnosis, personal advice, etc.)
    UNSAFE:              Question triggers a safety guardrail.
    """
    SUPPORTED     = "supported"
    INSUFFICIENT  = "insufficient"
    OUT_OF_SCOPE  = "out_of_scope"
    UNSAFE        = "unsafe"


class Citation(BaseModel):
    """A single guideline citation attached to the answer."""
    guideline_id:   str
    title:          str
    organization:   str
    specialty:      Optional[str]   = None
    year:           Optional[int]   = None
    version:        Optional[str]   = None
    section:        Optional[str]   = None
    subsection:     Optional[str]   = None
    page_number:    Optional[int]   = None
    evidence_grade: Optional[str]   = None
    source_url:     Optional[str]   = None
    rerank_score:   Optional[float] = None


class QueryResponse(BaseModel):
    """
    Full response from POST /api/query.

    answer:           The generated answer grounded in evidence.
    scope_status:     Whether the question was answerable.
    scope_message:    Human-readable explanation of scope status.
    citations:        Structured provenance for every source used.
    evidence_summary: Brief summary of what evidence was found.
    conflicting_guidelines: True if sources disagree.
    disclaimer:       Always present — this is not medical advice.
    """
    answer:                  str
    scope_status:            ScopeStatus
    scope_message:           Optional[str]   = None
    citations:               list[Citation]  = Field(default_factory=list)
    evidence_summary:        Optional[str]   = None
    conflicting_guidelines:  bool            = False
    disclaimer:              str = (
        "This response is generated from indexed clinical guidelines "
        "for informational and educational purposes only. It is not a "
        "substitute for professional medical judgment, diagnosis, or "
        "individualised treatment advice. Always consult a qualified "
        "healthcare professional."
    )