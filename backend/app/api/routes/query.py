"""
POST /api/query — main RAG endpoint.

Accepts a clinical question with optional filters,
runs the full RAG pipeline, returns a structured response
with answer, citations, scope status, and disclaimer.

LangSmith tracing is active on answer_question() via the
@traceable decorator applied in chain.py — no additional
setup needed here. Every request is automatically traced
when LANGCHAIN_TRACING_V2=true in .env.
"""

import logging
import time
from fastapi import APIRouter, HTTPException, status
from app.models.request import QueryRequest
from app.models.response import QueryResponse, ScopeStatus
from app.generation.chain import answer_question

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a clinical guidelines question",
    description=(
        "Submit a clinical question and receive an evidence-grounded answer "
        "with structured provenance from indexed guidelines. "
        "This endpoint is for informational purposes only and does not "
        "provide personalised medical advice."
    ),
)
async def query_guidelines(request: QueryRequest) -> QueryResponse:
    """
    Full RAG pipeline:
      scope detection → retrieval → reranking → generation → provenance
    """
    start = time.time()
    logger.info(
        f"Query received | question='{request.question[:80]}' "
        f"specialty={request.specialty} org={request.organization} "
        f"year={request.year}"
    )

    try:
        response = answer_question(
            question=request.question,
            specialty=request.specialty,
            organization=request.organization,
            year=request.year,
            guideline_id=request.guideline_id,
        )
    except Exception as e:
        logger.error(f"Query pipeline failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your query. Please try again.",
        )

    elapsed = round(time.time() - start, 2)
    logger.info(
        f"Query complete | status={response.scope_status} "
        f"citations={len(response.citations)} elapsed={elapsed}s"
    )
    return response