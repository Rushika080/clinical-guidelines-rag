"""
RAG generation chain.

Assembles scope detection + retrieval + LLM generation + provenance
into one callable: answer_question().

This is the single entry point the FastAPI route will call in Phase 6.

GEMINI INTEGRATION:
  We use google-generativeai directly rather than langchain-google-genai
  for the generation step. This gives us cleaner control over the
  JSON response parsing without fighting LangChain's output parsers.
"""

import json
import logging
import re
from typing import Optional

import google.generativeai as genai
from langchain.schema import Document
from langsmith import traceable

from app.config import get_settings
from app.models.response import QueryResponse, ScopeStatus, Citation
from app.safety.scope_detector import detect_scope
from app.safety.guardrails import apply_output_guardrails
from app.generation.prompts import (
    SYSTEM_PROMPT,
    EVIDENCE_GROUNDED_PROMPT,
    format_evidence_text,
)
from app.provenance.tracker import build_citations
from app.retrieval.pipeline import retrieve_evidence

logger = logging.getLogger(__name__)


def _init_gemini() -> None:
    """Configure the Gemini API client once."""
    settings = get_settings()
    if not settings.google_api_key:
        raise ValueError(
            "GOOGLE_API_KEY is not set. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )
    genai.configure(api_key=settings.google_api_key)


def _parse_llm_json(raw: str) -> dict:
    """
    Parse JSON from LLM output robustly.

    LLMs sometimes wrap JSON in markdown fences (```json ... ```)
    even when instructed not to. We strip those before parsing.
    """
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed: {e}. Raw: {raw[:200]}")
        # Return a safe fallback structure
        return {
            "answer": raw,  # return raw text as answer
            "evidence_summary": "Unable to parse structured response.",
            "conflicting_guidelines": False,
            "citations_used": [],
        }


def _call_gemini(system: str, user: str) -> str:
    """
    Call Gemini 1.5 Flash with system + user prompt.
    Returns the raw text response.
    """
    settings = get_settings()
    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=system,
    )
    response = model.generate_content(
        user,
        generation_config=genai.types.GenerationConfig(
            temperature=0.0,   # zero temperature = deterministic, fact-focused
            max_output_tokens=1500,
        ),
    )
    return response.text


@traceable(name="answer-question", tags=["generation", "clinical-rag"])
def answer_question(
    question: str,
    specialty:     Optional[str] = None,
    organization:  Optional[str] = None,
    year:          Optional[int] = None,
    guideline_id:  Optional[str] = None,
) -> QueryResponse:
    """
    Full RAG pipeline: scope check → retrieve → generate → provenance.

    Args:
        question:     The clinical question
        specialty:    Optional specialty filter
        organization: Optional org filter
        year:         Optional year filter
        guideline_id: Optional specific guideline filter

    Returns:
        QueryResponse with answer, citations, scope status, and disclaimer.
    """
    logger.info(f"Processing question: '{question[:100]}'")

    # ── Step 1: Scope detection ──────────────────────────────────────────
    scope_status, scope_message = detect_scope(question)

    if scope_status in (ScopeStatus.UNSAFE, ScopeStatus.OUT_OF_SCOPE):
        logger.info(f"Question rejected by scope detector: {scope_status}")
        return QueryResponse(
            answer=scope_message,
            scope_status=scope_status,
            scope_message=scope_message,
            citations=[],
        )

    # ── Step 2: Retrieve evidence ────────────────────────────────────────
    retrieval_result = retrieve_evidence(
        query=question,
        specialty=specialty,
        organization=organization,
        year=year,
        guideline_id=guideline_id,
    )

    documents: list[Document] = retrieval_result["documents"]

    if not documents:
        logger.info("No evidence retrieved — returning INSUFFICIENT response.")
        return QueryResponse(
            answer=(
                "I could not find relevant evidence in the indexed clinical "
                "guidelines to answer this question. The currently indexed "
                "sources may not cover this topic."
            ),
            scope_status=ScopeStatus.INSUFFICIENT,
            scope_message=(
                "No relevant evidence found in the indexed guidelines. "
                "Consider checking if the relevant guideline has been ingested."
            ),
            citations=[],
        )

    # ── Step 3: Format evidence for prompt ───────────────────────────────
    evidence_text = format_evidence_text(documents)
    user_prompt = EVIDENCE_GROUNDED_PROMPT.format(
        evidence_text=evidence_text,
        question=question,
    )

    # ── Step 4: Generate answer ───────────────────────────────────────────
    try:
        _init_gemini()
        raw_response = _call_gemini(SYSTEM_PROMPT, user_prompt)
        parsed = _parse_llm_json(raw_response)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return QueryResponse(
            answer="Generation failed due to an internal error. Please try again.",
            scope_status=ScopeStatus.INSUFFICIENT,
            citations=[],
        )

    answer          = parsed.get("answer", "")
    evidence_summary = parsed.get("evidence_summary", "")
    conflicting     = parsed.get("conflicting_guidelines", False)
    citations_used  = parsed.get("citations_used", [])

    # ── Step 5: Apply output safety guardrails ────────────────────────────
    answer = apply_output_guardrails(answer)

    # ── Step 6: Build provenance citations ───────────────────────────────
    citations = build_citations(documents, citations_used)

    # ── Step 7: Assemble final response ──────────────────────────────────
    return QueryResponse(
        answer=answer,
        scope_status=ScopeStatus.SUPPORTED,
        scope_message=None,
        citations=citations,
        evidence_summary=evidence_summary,
        conflicting_guidelines=bool(conflicting),
    )