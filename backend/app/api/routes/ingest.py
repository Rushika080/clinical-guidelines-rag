"""
POST /api/ingest — trigger document ingestion.

Allows ingesting a registered guideline via API call
rather than the CLI. Useful for scheduled re-indexing
or triggering ingestion from a deployment pipeline.

In production this would be an async background task.
Here it runs synchronously (acceptable for a portfolio project).
"""

import logging
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ingestion"])


class IngestRequest(BaseModel):
    guideline_id: str
    dry_run: bool = False


class IngestResponse(BaseModel):
    guideline_id:  str
    status:        str
    message:       str
    parent_chunks: Optional[int] = None
    child_chunks:  Optional[int] = None


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest a registered guideline",
    description=(
        "Trigger ingestion of a guideline that is registered in "
        "guideline_registry.json and has its PDF file in place. "
        "Use dry_run=true to validate without writing to the vectorstore."
    ),
)
async def ingest_guideline(request: IngestRequest) -> IngestResponse:
    """
    Run the ingestion pipeline for a single registered guideline.
    The guideline_id must exist in data/guideline_registry.json
    and the PDF must be present at the registered local_path.
    """
    import json
    from pathlib import Path
    from ingestion.metadata.registry import get_guideline_by_id

    meta = get_guideline_by_id(request.guideline_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guideline '{request.guideline_id}' not found in registry.",
        )

    # Check PDF exists
    from ingestion.metadata.registry import REGISTRY_PATH
    registry_path = REGISTRY_PATH
    with open(registry_path) as f:
        data = json.load(f)

    pdf_path = None
    for entry in data["guidelines"]:
        if entry["guideline_id"] == request.guideline_id:
            pdf_path = Path(entry.get("local_path", ""))
            break

    if not pdf_path or not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"PDF not found at '{pdf_path}'. "
                f"Download the guideline PDF and place it at that path."
            ),
        )

    try:
        from ingestion.loaders.pdf_loader import load_pdf_pages
        from ingestion.parsers.section_parser import parse_sections
        from ingestion.chunking.splitter import build_chunks

        pages = load_pdf_pages(pdf_path)
        pages = parse_sections(pages)
        chunks = build_chunks(pages, meta.to_dict())
        parent_chunks = chunks["parent_chunks"]
        child_chunks  = chunks["child_chunks"]

        if not request.dry_run:
                    from app.retrieval.vectorstore import get_vectorstore, get_chroma_client
                    from app.retrieval.parent_retriever import save_parents

                    save_parents(parent_chunks)
                    vectorstore = get_vectorstore(collection_name=request.guideline_id)

                    batch_size = 50
                    for i in range(0, len(child_chunks), batch_size):
                        batch     = child_chunks[i : i + batch_size]
                        texts     = [d.page_content for d in batch]
                        metadatas = [d.metadata for d in batch]
                        ids = [
                            d.metadata["parent_id"]
                            + f"-{d.metadata.get('child_index', i + j)}"
                            for j, d in enumerate(batch)
                        ]
                        vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        return IngestResponse(
            guideline_id  = request.guideline_id,
            status        = "success" if not request.dry_run else "dry_run",
            message       = (
                f"Successfully indexed {len(child_chunks)} chunks."
                if not request.dry_run
                else f"Dry run complete. {len(child_chunks)} chunks would be indexed."
            ),
            parent_chunks = len(parent_chunks),
            child_chunks  = len(child_chunks),
        )

    except Exception as e:
        logger.error(f"Ingestion failed for '{request.guideline_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )