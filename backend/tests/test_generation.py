"""
Tests for generation chain — all LLM and retrieval calls are mocked.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.models.response import ScopeStatus, QueryResponse


def make_mock_retrieval(n_docs: int = 2):
    from langchain.schema import Document
    docs = [
        Document(
            page_content=f"HbA1c target < 7% is recommended for most adults. [Evidence {i}]",
            metadata={
                "guideline_id": "ada-standards-2024",
                "title": "ADA Standards 2024",
                "organization": "American Diabetes Association",
                "specialty": "diabetes",
                "publication_year": 2024,
                "page_number": i + 1,
                "rerank_score": 0.9 - i * 0.1,
            },
        )
        for i in range(n_docs)
    ]
    return {
        "documents": docs,
        "retrieval_count": n_docs,
        "reranked_count": n_docs,
        "filter_applied": None,
        "query": "HbA1c targets",
    }


MOCK_LLM_RESPONSE = """{
  "answer": "The ADA recommends an HbA1c target of less than 7% for most adults with diabetes.",
  "evidence_summary": "ADA 2024 Standards recommend HbA1c < 7% for most non-pregnant adults.",
  "conflicting_guidelines": false,
  "citations_used": [1]
}"""


def test_answer_question_supported():
    from app.generation.chain import answer_question
    with patch("app.generation.chain.retrieve_evidence",
               return_value=make_mock_retrieval()), \
         patch("app.generation.chain._init_gemini"), \
         patch("app.generation.chain._call_gemini",
               return_value=MOCK_LLM_RESPONSE):
        result = answer_question("What are HbA1c targets for adults?")
        assert isinstance(result, QueryResponse)
        assert result.scope_status == ScopeStatus.SUPPORTED
        assert len(result.answer) > 0
        assert len(result.citations) > 0


def test_answer_question_out_of_scope():
    from app.generation.chain import answer_question
    result = answer_question("I have diabetes, what should I eat?")
    assert result.scope_status == ScopeStatus.OUT_OF_SCOPE


def test_answer_question_unsafe():
    from app.generation.chain import answer_question
    result = answer_question("How much insulin should I inject?")
    assert result.scope_status == ScopeStatus.UNSAFE


def test_answer_question_no_evidence():
    from app.generation.chain import answer_question
    with patch("app.generation.chain.retrieve_evidence",
               return_value={"documents": [], "retrieval_count": 0,
                             "reranked_count": 0, "filter_applied": None,
                             "query": "test"}):
        result = answer_question("What is the treatment for rare tropical disease X?")
        assert result.scope_status == ScopeStatus.INSUFFICIENT
        assert result.citations == []


def test_answer_always_has_disclaimer():
    from app.generation.chain import answer_question
    with patch("app.generation.chain.retrieve_evidence",
               return_value=make_mock_retrieval()), \
         patch("app.generation.chain._init_gemini"), \
         patch("app.generation.chain._call_gemini",
               return_value=MOCK_LLM_RESPONSE):
        result = answer_question("What does ADA recommend for HbA1c?")
        assert len(result.disclaimer) > 0


def test_llm_failure_returns_graceful_response():
    from app.generation.chain import answer_question
    with patch("app.generation.chain.retrieve_evidence",
               return_value=make_mock_retrieval()), \
         patch("app.generation.chain._init_gemini"), \
         patch("app.generation.chain._call_gemini",
               side_effect=Exception("API timeout")):
        result = answer_question("What are HbA1c targets?")
        assert result.scope_status == ScopeStatus.INSUFFICIENT