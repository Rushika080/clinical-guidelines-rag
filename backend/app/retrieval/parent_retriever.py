"""
Parent document retrieval.

HOW IT WORKS:
  1. Vector search returns child chunks (small, precise).
  2. Each child chunk carries a parent_id in its metadata.
  3. We look up the parent_id in the parent docstore.
  4. We return the full parent document to the LLM instead of the child.

WHY:
  A child chunk like "HbA1c < 7% is recommended" lacks context.
  The parent chunk includes: who this applies to, what evidence grade,
  what exceptions exist, and what the surrounding recommendations say.
  Sending the parent to the LLM produces much more accurate answers.

DOCSTORE:
  In Phase 3 we use a JSON file on disk as the docstore.
  In production, swap this for Redis or a database.
  The interface (get/set by parent_id) stays the same either way.
"""

import json
import logging
from pathlib import Path
from langchain.schema import Document

logger = logging.getLogger(__name__)

# Path to the local parent docstore
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCSTORE_PATH = PROJECT_ROOT / "data" / "parent_docstore.json"

def save_parents(parent_chunks: list[Document]) -> None:
    """
    Persist parent chunks to the JSON docstore.
    Keyed by parent_id — each parent_id maps to
    {page_content, metadata} so we can reconstruct the Document.

    Appends to existing docstore rather than overwriting,
    so multiple ingestion runs accumulate correctly.
    """
    DOCSTORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load existing
    existing = {}
    if DOCSTORE_PATH.exists():
        with open(DOCSTORE_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)

    # Add new parents
    new_count = 0
    for doc in parent_chunks:
        parent_id = doc.metadata.get("parent_id")
        if not parent_id:
            logger.warning("Parent chunk missing parent_id — skipping.")
            continue
        if parent_id not in existing:
            existing[parent_id] = {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            }
            new_count += 1

    with open(DOCSTORE_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Docstore updated — {new_count} new parents added, "
        f"{len(existing)} total."
    )


def get_parent(parent_id: str) -> Document | None:
    """
    Retrieve a parent document by its parent_id.
    Returns None if not found (child chunk without parent is treated
    as its own context rather than raising an error).
    """
    if not DOCSTORE_PATH.exists():
        logger.warning("Parent docstore does not exist yet.")
        return None

    with open(DOCSTORE_PATH, "r", encoding="utf-8") as f:
        store = json.load(f)

    entry = store.get(parent_id)
    if not entry:
        return None

    return Document(
        page_content=entry["page_content"],
        metadata=entry["metadata"],
    )


def expand_to_parents(child_docs: list[Document]) -> list[Document]:
    """
    Given a list of child Documents (from vector search),
    return their corresponding parent Documents.

    If a parent is not found for a child (e.g. docstore out of sync),
    the child itself is returned as a fallback so the pipeline never
    silently drops evidence.

    Deduplication: multiple children from the same parent return
    the parent only once.
    """
    seen_parent_ids = set()
    parent_docs = []

    for child in child_docs:
        parent_id = child.metadata.get("parent_id")

        if not parent_id:
            # No parent_id — use child as fallback
            parent_docs.append(child)
            continue

        if parent_id in seen_parent_ids:
            # Already included this parent
            continue

        parent = get_parent(parent_id)
        if parent:
            parent_docs.append(parent)
            seen_parent_ids.add(parent_id)
        else:
            # Parent not in docstore — fall back to child
            logger.warning(
                f"Parent {parent_id} not found in docstore. "
                f"Using child chunk as fallback."
            )
            parent_docs.append(child)
            seen_parent_ids.add(parent_id)

    return parent_docs