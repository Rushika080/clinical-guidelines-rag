"""
Tests for the parent-child chunking pipeline.
No PDF or API keys required — uses synthetic page dicts.
"""

import pytest
from langchain.schema import Document


def make_sample_pages(n: int = 3) -> list[dict]:
    """Create synthetic enriched page dicts for testing."""
    return [
        {
            "page_number": i + 1,
            "text": (
                f"Section {i+1} content. " * 50  # ~250 words per page
            ),
            "font_blocks": [],
            "section": f"Section {i+1}",
            "subsection": f"Subsection {i+1}.1",
        }
        for i in range(n)
    ]


def make_sample_metadata() -> dict:
    return {
        "guideline_id": "test-001",
        "title": "Test Guideline 2024",
        "organization": "Test Org",
        "specialty": "diabetes",
        "publication_year": 2024,
    }


def test_build_chunks_returns_both_types():
    from ingestion.chunking.splitter import build_chunks
    pages = make_sample_pages()
    meta = make_sample_metadata()
    result = build_chunks(pages, meta)
    assert "parent_chunks" in result
    assert "child_chunks" in result


def test_build_chunks_produces_documents():
    from ingestion.chunking.splitter import build_chunks
    pages = make_sample_pages()
    meta = make_sample_metadata()
    result = build_chunks(pages, meta)
    assert all(isinstance(d, Document) for d in result["parent_chunks"])
    assert all(isinstance(d, Document) for d in result["child_chunks"])


def test_child_chunks_have_parent_id():
    from ingestion.chunking.splitter import build_chunks
    pages = make_sample_pages()
    meta = make_sample_metadata()
    result = build_chunks(pages, meta)
    for child in result["child_chunks"]:
        assert "parent_id" in child.metadata, "Every child must reference a parent"


def test_parent_id_matches_a_parent():
    from ingestion.chunking.splitter import build_chunks
    pages = make_sample_pages()
    meta = make_sample_metadata()
    result = build_chunks(pages, meta)
    parent_ids = {p.metadata["parent_id"] for p in result["parent_chunks"]}
    for child in result["child_chunks"]:
        assert child.metadata["parent_id"] in parent_ids


def test_chunks_preserve_page_number():
    from ingestion.chunking.splitter import build_chunks
    pages = make_sample_pages(n=2)
    meta = make_sample_metadata()
    result = build_chunks(pages, meta)
    for chunk in result["parent_chunks"] + result["child_chunks"]:
        assert "page_number" in chunk.metadata
        assert chunk.metadata["page_number"] in (1, 2)


def test_chunks_preserve_guideline_metadata():
    from ingestion.chunking.splitter import build_chunks
    pages = make_sample_pages()
    meta = make_sample_metadata()
    result = build_chunks(pages, meta)
    for chunk in result["child_chunks"]:
        assert chunk.metadata["guideline_id"] == "test-001"
        assert chunk.metadata["organization"] == "Test Org"
        assert chunk.metadata["specialty"] == "diabetes"


def test_child_chunks_smaller_than_parents():
    from ingestion.chunking.splitter import build_chunks
    pages = make_sample_pages(n=5)
    meta = make_sample_metadata()
    result = build_chunks(pages, meta)
    avg_parent = sum(len(d.page_content) for d in result["parent_chunks"]) / max(len(result["parent_chunks"]), 1)
    avg_child  = sum(len(d.page_content) for d in result["child_chunks"])  / max(len(result["child_chunks"]), 1)
    assert avg_child < avg_parent, "Child chunks must be smaller than parent chunks"


def test_no_metadata_none_values():
    """
    Pinecone rejects None metadata values.
    Ensure no chunk carries a None in its metadata.
    """
    from ingestion.chunking.splitter import build_chunks
    pages = make_sample_pages()
    meta = make_sample_metadata()
    result = build_chunks(pages, meta)
    for chunk in result["parent_chunks"] + result["child_chunks"]:
        for key, val in chunk.metadata.items():
            assert val is not None, f"None found in metadata key '{key}'"