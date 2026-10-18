"""
Local cross-encoder reranking using HuggingFace sentence-transformers.

WHY CROSS-ENCODER OVER COHERE?
  - Runs 100% locally — no API key, no cost, no rate limits
  - cross-encoder/ms-marco-MiniLM-L-6-v2 is trained on MS MARCO
    (a large passage retrieval dataset) — strong general relevance scorer
  - For production with budget, swap back to Cohere by changing this file only

HOW CROSS-ENCODERS WORK:
  Unlike bi-encoders (which embed query and document separately),
  a cross-encoder reads the query + document TOGETHER and outputs
  a single relevance score. This is slower but more accurate — exactly
  what we need for a final reranking step over a small candidate set.
"""

import logging
from typing import Optional

from langchain.schema import Document

from app.config import get_settings

logger = logging.getLogger(__name__)

# Module-level cache — load model once, reuse across requests
_cross_encoder = None


def get_cross_encoder():
    """Load the cross-encoder model once and cache it."""
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        settings = get_settings()
        logger.info(f"Loading cross-encoder: {settings.rerank_model}")
        _cross_encoder = CrossEncoder(settings.rerank_model)
        logger.info("Cross-encoder loaded.")
    return _cross_encoder


def rerank_documents(
    query: str,
    documents: list[Document],
    top_n: Optional[int] = None,
) -> list[Document]:
    """
    Rerank documents using a local cross-encoder model.

    Same interface as the Cohere version — drop-in replacement.
    Adds "rerank_score" to each document's metadata.

    Falls back to original order if model fails.
    """
    settings = get_settings()
    top_n = top_n or settings.rerank_top_n

    if not documents:
        return []

    try:
        model = get_cross_encoder()

        # Cross-encoder scores [query, document] pairs
        pairs = [[query, doc.page_content] for doc in documents]
        scores = model.predict(pairs)

        # Sort by score descending
        scored = sorted(
            zip(scores, documents),
            key=lambda x: x[0],
            reverse=True,
        )

        reranked = []
        for score, doc in scored[:top_n]:
            reranked.append(Document(
                page_content=doc.page_content,
                metadata={**doc.metadata, "rerank_score": round(float(score), 4)},
            ))

        logger.info(
            f"Reranked {len(documents)} docs → kept {len(reranked)}. "
            f"Top score: {reranked[0].metadata['rerank_score'] if reranked else 'N/A'}"
        )
        return reranked

    except Exception as e:
        logger.error(f"Reranking failed: {e}. Using original order.")
        return documents[:top_n]