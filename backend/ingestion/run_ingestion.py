"""
CLI entry point for the ingestion pipeline.

Usage:
    python -m ingestion.run_ingestion --dry-run          # Phase 2 mode
    python -m ingestion.run_ingestion                    # Phase 3: writes to Pinecone
    python -m ingestion.run_ingestion --guideline-id ada-standards-2024
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.core.logging import setup_logging
from ingestion.loaders.pdf_loader import load_pdf_pages
from ingestion.parsers.section_parser import parse_sections
from ingestion.chunking.splitter import build_chunks
from ingestion.metadata.registry import load_registry, get_guideline_by_id

setup_logging()
logger = logging.getLogger(__name__)


def resolve_pdf_path(guideline_id: str) -> Path | None:
    registry_path = Path("data/guideline_registry.json")
    if not registry_path.exists():
        raise FileNotFoundError(f"Registry not found: {registry_path}")

    with open(registry_path) as f:
        data = json.load(f)

    for entry in data["guidelines"]:
        if entry["guideline_id"] == guideline_id:
            return Path(entry.get("local_path", ""))
    return None


def run_pipeline(guideline_id: str, dry_run: bool) -> None:
    meta = get_guideline_by_id(guideline_id)
    if not meta:
        logger.error(f"Guideline '{guideline_id}' not found in registry.")
        return

    pdf_path = resolve_pdf_path(guideline_id)
    if not pdf_path or not pdf_path.exists():
        logger.warning(
            f"PDF not found at '{pdf_path}'. "
            f"Download it and place it at that path."
        )
        return

    logger.info(f"=== Ingesting: {meta.title} ===")

    # Step 1 — Load
    pages = load_pdf_pages(pdf_path)

    # Step 2 — Parse sections
    pages = parse_sections(pages)
    sections_found = {p["section"] for p in pages if p.get("section")}

    # Step 3 — Chunk
    chunks = build_chunks(pages, meta.to_dict())
    parent_chunks = chunks["parent_chunks"]
    child_chunks  = chunks["child_chunks"]

    # Step 4 — Print summary
    print(f"\n{'='*60}")
    print(f"INGESTION SUMMARY — {meta.title}")
    print(f"{'='*60}")
    print(f"Organization : {meta.organization}")
    print(f"Specialty    : {meta.specialty}")
    print(f"Year         : {meta.publication_year}")
    print(f"Pages        : {len(pages)}")
    print(f"Sections     : {len(sections_found)}")
    print(f"Parent chunks: {len(parent_chunks)}")
    print(f"Child chunks : {len(child_chunks)}")

    if child_chunks:
        sample = child_chunks[0]
        print(f"\nSample child metadata:")
        for k, v in sample.metadata.items():
            print(f"  {k}: {v}")

    if dry_run:
        print(f"\n[DRY RUN] Pinecone indexing skipped.")
        print(f"{'='*60}\n")
        return

        # Step 5 — Write to ChromaDB
    print(f"\nIndexing to ChromaDB...")
    from app.retrieval.vectorstore import get_vectorstore, get_chroma_client
    from app.retrieval.parent_retriever import save_parents

    save_parents(parent_chunks)
    logger.info(f"Saved {len(parent_chunks)} parents to docstore.")

    vectorstore = get_vectorstore(collection_name=guideline_id)

    batch_size = 50  # smaller batches for reliability
    for i in range(0, len(child_chunks), batch_size):
        batch     = child_chunks[i : i + batch_size]
        texts     = [d.page_content for d in batch]
        metadatas = [d.metadata for d in batch]
        ids = [
            d.metadata["parent_id"] + f"-{d.metadata.get('child_index', i+j)}"
            for j, d in enumerate(batch)
        ]
        vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        logger.info(f"Indexed batch {i//batch_size + 1} ({len(batch)} chunks)")

    # Verify persistence
    client = get_chroma_client()
    col = client.get_collection(guideline_id)
    actual_count = col.count()
    print(f"Verified: {actual_count} vectors in ChromaDB collection '{guideline_id}'")

    if actual_count == 0:
        print("WARNING: Vectors not persisted. Check ChromaDB path permissions.")
    else:
        print(f"Successfully indexed {actual_count} child chunks.")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Clinical Guidelines ingestion pipeline"
    )
    parser.add_argument("--guideline-id", help="Single guideline ID to ingest")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Process PDFs but skip Pinecone indexing",
    )
    args = parser.parse_args()

    if args.guideline_id:
        run_pipeline(args.guideline_id, dry_run=args.dry_run)
    else:
        guidelines = load_registry()
        if not guidelines:
            logger.warning("No guidelines in registry.")
            return
        for g in guidelines:
            run_pipeline(g.guideline_id, dry_run=args.dry_run)

if __name__ == "__main__":
    main()