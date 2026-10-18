"""
Provenance tracker — builds Citation objects from retrieved documents.

WHY THIS IS A SEPARATE MODULE:
  Provenance extraction is distinct from generation.
  The LLM tells us WHICH passages it used (via citations_used indices).
  This module extracts the structured metadata from those passages
  and builds Citation objects for the response.

  This means citations are always grounded in real metadata from
  the ingested documents — the LLM cannot fabricate a citation because
  it only provides indices, not the citation content itself.
"""

import logging
from langchain.schema import Document
from app.models.response import Citation

logger = logging.getLogger(__name__)


def build_citations(
    documents: list[Document],
    used_indices: list[int],
) -> list[Citation]:
    """
    Build Citation objects for the documents the LLM actually used.

    Args:
        documents:    The reranked documents passed to the LLM (1-indexed in prompt)
        used_indices: List of 1-based indices the LLM cited (from JSON response)

    Returns:
        List of Citation objects with metadata from the source documents.
        If used_indices is empty, returns citations for ALL documents
        (conservative fallback — better to over-cite than under-cite).
    """
    if not documents:
        return []

    # Convert 1-indexed to 0-indexed; filter out-of-range indices
    if used_indices:
        indices_0 = [i - 1 for i in used_indices if 1 <= i <= len(documents)]
    else:
        # LLM didn't specify — cite all documents as potential sources
        indices_0 = list(range(len(documents)))

    citations = []
    seen_guideline_ids = set()

    for idx in indices_0:
        doc = documents[idx]
        meta = doc.metadata

        guideline_id = meta.get("guideline_id", f"unknown-{idx}")

        # Deduplicate by guideline_id + page_number to avoid identical citations
        dedup_key = f"{guideline_id}:{meta.get('page_number', '')}"
        if dedup_key in seen_guideline_ids:
            continue
        seen_guideline_ids.add(dedup_key)

        citation = Citation(
            guideline_id   = guideline_id,
            title          = meta.get("title", "Unknown guideline"),
            organization   = meta.get("organization", "Unknown organization"),
            specialty      = meta.get("specialty"),
            year           = meta.get("publication_year"),
            version        = meta.get("version"),
            section        = meta.get("section"),
            subsection     = meta.get("subsection"),
            page_number    = meta.get("page_number"),
            evidence_grade = meta.get("evidence_grade"),
            source_url     = meta.get("source_url"),
            rerank_score   = meta.get("rerank_score"),
        )
        citations.append(citation)

    logger.info(f"Built {len(citations)} citations from {len(used_indices)} cited indices")
    return citations