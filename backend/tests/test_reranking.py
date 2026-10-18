"""
Tests for local cross-encoder reranking.

The cross-encoder is mocked so tests do not download or load
the HuggingFace model.
"""

from unittest.mock import MagicMock, patch

from langchain.schema import Document


def make_docs(n: int) -> list[Document]:
    return [
        Document(
            page_content=f"Clinical evidence passage {i}. HbA1c targets vary.",
            metadata={
                "guideline_id": "test-001",
                "page_number": i,
                "parent_id": f"parent-{i}",
                "chunk_type": "parent",
            },
        )
        for i in range(n)
    ]


def test_rerank_returns_top_n():
    from app.reranking.cohere_reranker import rerank_documents

    docs = make_docs(10)

    # Higher scores should appear first.
    mock_model = MagicMock()
    mock_model.predict.return_value = [
        0.10, 0.20, 0.95, 0.30, 0.40,
        0.50, 0.60, 0.88, 0.70, 0.80,
    ]

    with patch(
        "app.reranking.cohere_reranker.get_cross_encoder",
        return_value=mock_model,
    ):
        result = rerank_documents(
            "HbA1c targets diabetes",
            docs,
            top_n=5,
        )

    assert len(result) == 5

    # Highest scoring documents should come first.
    assert result[0].page_content == docs[2].page_content
    assert result[1].page_content == docs[7].page_content


def test_rerank_attaches_score_to_metadata():
    from app.reranking.cohere_reranker import rerank_documents

    docs = make_docs(3)

    mock_model = MagicMock()
    mock_model.predict.return_value = [0.81, 0.92, 0.54]

    with patch(
        "app.reranking.cohere_reranker.get_cross_encoder",
        return_value=mock_model,
    ):
        result = rerank_documents("query", docs, top_n=3)

    for doc in result:
        assert "rerank_score" in doc.metadata
        assert isinstance(doc.metadata["rerank_score"], float)


def test_rerank_preserves_metadata():
    from app.reranking.cohere_reranker import rerank_documents

    docs = make_docs(3)

    mock_model = MagicMock()
    mock_model.predict.return_value = [0.50, 0.90, 0.20]

    with patch(
        "app.reranking.cohere_reranker.get_cross_encoder",
        return_value=mock_model,
    ):
        result = rerank_documents("query", docs, top_n=1)

    assert len(result) == 1

    assert result[0].metadata["guideline_id"] == "test-001"
    assert result[0].metadata["chunk_type"] == "parent"
    assert result[0].metadata["page_number"] == 1


def test_rerank_falls_back_on_model_error():
    from app.reranking.cohere_reranker import rerank_documents

    docs = make_docs(5)

    mock_model = MagicMock()
    mock_model.predict.side_effect = Exception("Model error")

    with patch(
        "app.reranking.cohere_reranker.get_cross_encoder",
        return_value=mock_model,
    ):
        result = rerank_documents("query", docs, top_n=3)

    # Fallback should preserve original order.
    assert len(result) == 3
    assert result[0].page_content == docs[0].page_content
    assert result[1].page_content == docs[1].page_content
    assert result[2].page_content == docs[2].page_content


def test_rerank_empty_input():
    from app.reranking.cohere_reranker import rerank_documents

    result = rerank_documents("query", [], top_n=5)

    assert result == []


def test_rerank_top_n_capped_at_input_length():
    from app.reranking.cohere_reranker import rerank_documents

    docs = make_docs(2)

    mock_model = MagicMock()
    mock_model.predict.return_value = [0.90, 0.70]

    with patch(
        "app.reranking.cohere_reranker.get_cross_encoder",
        return_value=mock_model,
    ):
        result = rerank_documents("query", docs, top_n=10)

    assert len(result) == 2


# ---------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------

def test_retrieve_evidence_returns_expected_keys():
    from app.retrieval.pipeline import retrieve_evidence

    mock_child = make_docs(3)
    mock_parent = make_docs(3)
    mock_reranked = make_docs(2)

    with patch(
        "app.retrieval.pipeline.get_vectorstore"
    ) as mock_vs, patch(
        "app.retrieval.pipeline.expand_to_parents",
        return_value=mock_parent,
    ), patch(
        "app.retrieval.pipeline.rerank_documents",
        return_value=mock_reranked,
    ):

        mock_vs.return_value.similarity_search.return_value = mock_child

        result = retrieve_evidence(
            "What is the HbA1c target for adults?"
        )

        assert "documents" in result
        assert "query" in result
        assert "retrieval_count" in result
        assert "reranked_count" in result
        assert "filter_applied" in result


def test_retrieve_evidence_empty_vector_results():
    from app.retrieval.pipeline import retrieve_evidence

    with patch(
        "app.retrieval.pipeline.get_vectorstore"
    ) as mock_vs:

        mock_vs.return_value.similarity_search.return_value = []

        result = retrieve_evidence(
            "What is the treatment for sepsis?"
        )

        assert result["documents"] == []
        assert result["retrieval_count"] == 0


def test_retrieve_evidence_handles_vector_search_error():
    from app.retrieval.pipeline import retrieve_evidence

    with patch(
        "app.retrieval.pipeline.get_vectorstore"
    ) as mock_vs:

        mock_vs.return_value.similarity_search.side_effect = (
            Exception("Connection error")
        )

        result = retrieve_evidence("Any query")

        assert result["documents"] == []
        assert "error" in result