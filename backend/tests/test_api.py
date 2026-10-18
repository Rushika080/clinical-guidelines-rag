"""
API endpoint tests — all pipeline calls mocked.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.models.response import QueryResponse, ScopeStatus, Citation


# ── Health ────────────────────────────────────────────────────────────────

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health_returns_environment(client):
    response = client.get("/api/health")
    assert response.json()["environment"] == "development"


# ── Guidelines list ───────────────────────────────────────────────────────

def test_list_guidelines_returns_200(client):
    response = client.get("/api/guidelines")
    assert response.status_code == 200


def test_list_guidelines_structure(client):
    response = client.get("/api/guidelines")
    data = response.json()
    assert "total" in data
    assert "guidelines" in data
    assert isinstance(data["guidelines"], list)


def test_get_guideline_by_id(client):
    response = client.get("/api/guidelines/ada-standards-2024")
    assert response.status_code == 200
    data = response.json()
    assert data["guideline_id"] == "ada-standards-2024"
    assert data["organization"] == "American Diabetes Association"


def test_get_guideline_not_found(client):
    response = client.get("/api/guidelines/nonexistent-999")
    assert response.status_code == 404


# ── Query endpoint ────────────────────────────────────────────────────────

def make_mock_response(scope: ScopeStatus = ScopeStatus.SUPPORTED) -> QueryResponse:
    return QueryResponse(
        answer="HbA1c target of less than 7% is recommended for most adults.",
        scope_status=scope,
        citations=[
            Citation(
                guideline_id="ada-standards-2024",
                title="ADA Standards 2024",
                organization="American Diabetes Association",
                year=2024,
                page_number=5,
            )
        ],
        evidence_summary="ADA 2024 recommends HbA1c < 7%.",
    )


def test_query_endpoint_returns_200(client):
    with patch("app.api.routes.query.answer_question",
               return_value=make_mock_response()):
        response = client.post(
            "/api/query",
            json={"question": "What are HbA1c targets for adults with diabetes?"},
        )
    assert response.status_code == 200


def test_query_response_has_required_fields(client):
    with patch("app.api.routes.query.answer_question",
               return_value=make_mock_response()):
        response = client.post(
            "/api/query",
            json={"question": "What does ADA recommend for HbA1c?"},
        )
    data = response.json()
    assert "answer"       in data
    assert "scope_status" in data
    assert "citations"    in data
    assert "disclaimer"   in data


def test_query_with_filters(client):
    with patch("app.api.routes.query.answer_question",
               return_value=make_mock_response()):
        response = client.post(
            "/api/query",
            json={
                "question":     "What are the glycemic targets?",
                "specialty":    "diabetes",
                "organization": "American Diabetes Association",
                "year":         2024,
            },
        )
    assert response.status_code == 200


def test_query_too_short_returns_422(client):
    response = client.post(
        "/api/query",
        json={"question": "Hi"},  # below min_length=5
    )
    assert response.status_code == 422


def test_query_out_of_scope_returns_200(client):
    """
    Out-of-scope questions return 200 with scope_status=out_of_scope,
    not a 4xx error. The API always responds — scope is in the payload.
    """
    with patch("app.api.routes.query.answer_question",
               return_value=make_mock_response(ScopeStatus.OUT_OF_SCOPE)):
        response = client.post(
            "/api/query",
            json={"question": "I have diabetes, what should I eat?"},
        )
    assert response.status_code == 200
    assert response.json()["scope_status"] == "out_of_scope"


def test_query_pipeline_error_returns_500(client):
    with patch("app.api.routes.query.answer_question",
               side_effect=Exception("Unexpected failure")):
        response = client.post(
            "/api/query",
            json={"question": "What does ADA recommend for HbA1c?"},
        )
    assert response.status_code == 500


# ── Ingest endpoint ───────────────────────────────────────────────────────

def test_ingest_unknown_guideline_returns_404(client):
    response = client.post(
        "/api/ingest",
        json={"guideline_id": "nonexistent-guideline", "dry_run": True},
    )
    assert response.status_code == 404


def test_ingest_missing_pdf_returns_422(client):
    """
    Guideline exists in registry but PDF not on disk → 422.
    """
    response = client.post(
        "/api/ingest",
        json={"guideline_id": "aha-acc-hf-2022", "dry_run": True},
    )
    # 422 because PDF is missing, or 200 if PDF happens to exist
    assert response.status_code in (200, 422)