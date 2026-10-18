"""
Parent-child document chunking for clinical guidelines.

WHY PARENT-CHILD CHUNKING?
  A naive chunker splits the document into equal-size chunks and embeds them.
  Problem: a 400-token chunk may semantically match the query ("HbA1c targets")
  but lacks the surrounding clinical context that makes the recommendation
  meaningful ("For adults with type 2 diabetes and cardiovascular disease...").

  Solution:
    - CHILD chunks (small, ~400 tokens) → stored in Pinecone for vector search
      These are precise and semantically focused — good for retrieval.
    - PARENT chunks (large, ~2000 tokens) → stored in a docstore
      When a child chunk is retrieved, we look up its parent and send the
      full parent section to the LLM instead.
  
  This gives us retrieval precision (child) + generation context (parent).

OUTPUT FORMAT:
  Returns a dict with two keys:
    "parent_chunks": list of LangChain Document objects (large)
    "child_chunks":  list of LangChain Document objects (small)
  
  Every child chunk carries a "parent_id" in its metadata so we can
  look up the parent during retrieval.
"""

import logging
import uuid
from typing import Any

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.config import get_settings

logger = logging.getLogger(__name__)


def build_chunks(
    pages: list[dict[str, Any]],
    guideline_metadata: dict,
) -> dict[str, list[Document]]:
    """
    Split enriched pages into parent and child Document chunks.

    Args:
        pages:              output of parse_sections() — pages with section info
        guideline_metadata: dict from GuidelineMetadata.to_dict()

    Returns:
        {
            "parent_chunks": [...],   # LangChain Documents, large context
            "child_chunks":  [...],   # LangChain Documents, small for embedding
        }

    Metadata on every chunk includes:
        - all guideline-level fields (org, year, specialty, etc.)
        - page_number
        - section / subsection
        - evidence_grade (if detectable)
        - parent_id (child chunks only, links back to parent)
        - chunk_type: "parent" or "child"
    """
    settings = get_settings()

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.parent_chunk_size,
        chunk_overlap=settings.parent_chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.child_chunk_size,
        chunk_overlap=settings.child_chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    parent_chunks: list[Document] = []
    child_chunks: list[Document] = []

    for page in pages:
        page_text = page.get("text", "").strip()
        if not page_text:
            continue

        page_number = page.get("page_number", 0)
        section = page.get("section")
        subsection = page.get("subsection")

        # Build the base metadata shared by all chunks from this page.
        # None values are excluded — Pinecone rejects None metadata values.
        base_metadata = {
            k: v for k, v in {
                **guideline_metadata,
                "page_number": page_number,
                "section": section,
                "subsection": subsection,
            }.items()
            if v is not None
        }

        # Split this page into parent-sized chunks
        parent_texts = parent_splitter.split_text(page_text)

        for parent_text in parent_texts:
            parent_id = str(uuid.uuid4())

            # Attempt to detect an evidence grade in the parent text.
            # Import here to avoid circular import.
            from ingestion.parsers.section_parser import extract_evidence_grade
            evidence_grade = extract_evidence_grade(parent_text)

            parent_metadata = {
                **base_metadata,
                "chunk_type": "parent",
                "parent_id": parent_id,
                **({"evidence_grade": evidence_grade} if evidence_grade else {}),
            }

            parent_doc = Document(
                page_content=parent_text,
                metadata=parent_metadata,
            )
            parent_chunks.append(parent_doc)

            # Split this parent into child chunks.
            # Each child carries the parent_id so retrieval can look up
            # the full parent context.
            child_texts = child_splitter.split_text(parent_text)

            for i, child_text in enumerate(child_texts):
                child_metadata = {
                    **parent_metadata,
                    "chunk_type": "child",
                    "child_index": i,
                    # parent_id is already in parent_metadata
                }
                child_doc = Document(
                    page_content=child_text,
                    metadata=child_metadata,
                )
                child_chunks.append(child_doc)

    logger.info(
        f"Chunking complete — "
        f"{len(parent_chunks)} parent chunks, "
        f"{len(child_chunks)} child chunks"
    )

    return {
        "parent_chunks": parent_chunks,
        "child_chunks": child_chunks,
    }