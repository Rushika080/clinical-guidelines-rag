"""
Tests for retrieval components.
All tests use mocks — no Pinecone API key required.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from langchain.schema import Document


# ── Hybrid / filter tests ─────────────────────────────────────────────────

def test_build_filter_with_guideline_id():
    from app.retrieval.hybrid import build_pinecone_filter
    f = build_pinecone_filter("any query", guideline_id="ada-001")
    assert f == {"guideline_id": {"$eq": "ada-001"}}


def test_build_filter_detects_ada_org():
    from app.retrieval.hybrid import build_pinecone_filter
    f = build_pinecone_filter("What does ADA recommend for HbA1c?")
    assert f is not None
    filter_str = json.dumps(f)
    assert "American Diabetes Association" in filter_str


def test_build_filter_detects_specialty():
    from app.retrieval.hybrid import build_pinecone_filter
    f = build_pinecone_filter("diabetes management targets")
    assert f is not None
    filter_str = json.dumps(f)
    assert "diabetes" in filter_str


def test_build_filter_explicit_year():
    from app.retrieval.hybrid import build_pinecone_filter
    f = build_pinecone_filter("treatment guidelines", year=2024)
    assert f is not None
    filter_str = json.dumps(f)
    assert "2024" in filter_str


def test_build_filter_always_includes_child_type():
    from app.retrieval.hybrid import build_pinecone_filter
    f = build_pinecone_filter("what is the recommended HbA1c target")
    assert f is not None
    filter_str = json.dumps(f)
    assert "child" in filter_str


def test_detect_org_filter_aha():
    from app.retrieval.hybrid import detect_org_filter
    result = detect_org_filter("What does AHA say about heart failure?")
    assert result == "American Heart Association"


def test_detect_org_filter_none():
    from app.retrieval.hybrid import detect_org_filter
    result = detect_org_filter("What is the treatment for hypertension?")
    assert result is None


# ── Parent retriever tests ────────────────────────────────────────────────

def test_save_and_get_parent():
    from app.retrieval.parent_retriever import save_parents, get_parent
    doc = Document(
        page_content="Test parent content",
        metadata={
            "parent_id": "test-uuid-001",
            "guideline_id": "test-001",
            "page_number": 5,
            "chunk_type": "parent",
        },
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch(
            "app.retrieval.parent_retriever.DOCSTORE_PATH",
            Path(tmpdir) / "docstore.json",
        ):
            save_parents([doc])
            result = get_parent("test-uuid-001")
            assert result is not None
            assert result.page_content == "Test parent content"
            assert result.metadata["guideline_id"] == "test-001"


def test_get_parent_returns_none_for_missing():
    from app.retrieval.parent_retriever import get_parent
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch(
            "app.retrieval.parent_retriever.DOCSTORE_PATH",
            Path(tmpdir) / "nonexistent.json",
        ):
            result = get_parent("nonexistent-id")
            assert result is None


def test_expand_to_parents_deduplicates():
    from app.retrieval.parent_retriever import expand_to_parents
    parent_id = "shared-parent-001"
    child1 = Document(
        page_content="child 1",
        metadata={"parent_id": parent_id}
    )
    child2 = Document(
        page_content="child 2",
        metadata={"parent_id": parent_id}
    )
    parent_doc = Document(
        page_content="full parent content",
        metadata={"parent_id": parent_id, "chunk_type": "parent"}
    )
    with patch("app.retrieval.parent_retriever.get_parent", return_value=parent_doc):
        results = expand_to_parents([child1, child2])
        # Both children map to the same parent — should return only one doc
        assert len(results) == 1
        assert results[0].page_content == "full parent content"


def test_expand_to_parents_falls_back_to_child():
    from app.retrieval.parent_retriever import expand_to_parents
    child = Document(
        page_content="child content",
        metadata={"parent_id": "missing-parent-id"}
    )
    with patch("app.retrieval.parent_retriever.get_parent", return_value=None):
        results = expand_to_parents([child])
        assert len(results) == 1
        assert results[0].page_content == "child content"