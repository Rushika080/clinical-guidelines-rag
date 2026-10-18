from langchain.schema import Document
from app.models.response import Citation


def make_doc(i: int, org: str = "ADA", year: int = 2024) -> Document:
    return Document(
        page_content=f"Evidence passage {i}",
        metadata={
            "guideline_id":    f"test-{i:03d}",
            "title":           f"Test Guideline {i}",
            "organization":    org,
            "specialty":       "diabetes",
            "publication_year": year,
            "version":         "2024",
            "section":         f"Section {i}",
            "page_number":     i * 2,
            "evidence_grade":  "A",
            "source_url":      f"https://example.org/{i}",
            "rerank_score":    0.9 - i * 0.1,
        },
    )


def test_build_citations_returns_citation_objects():
    from app.provenance.tracker import build_citations
    docs = [make_doc(1), make_doc(2)]
    citations = build_citations(docs, used_indices=[1, 2])
    assert len(citations) == 2
    assert all(isinstance(c, Citation) for c in citations)


def test_build_citations_correct_metadata():
    from app.provenance.tracker import build_citations
    docs = [make_doc(1)]
    citations = build_citations(docs, used_indices=[1])
    c = citations[0]
    assert c.organization == "ADA"
    assert c.year == 2024
    assert c.evidence_grade == "A"
    assert c.page_number == 2


def test_build_citations_empty_used_cites_all():
    from app.provenance.tracker import build_citations
    docs = [make_doc(1), make_doc(2), make_doc(3)]
    citations = build_citations(docs, used_indices=[])
    assert len(citations) == 3


def test_build_citations_deduplicates():
    from app.provenance.tracker import build_citations
    # Same guideline_id + page — should deduplicate
    doc = make_doc(1)
    citations = build_citations([doc, doc], used_indices=[1, 2])
    assert len(citations) == 1


def test_build_citations_empty_docs():
    from app.provenance.tracker import build_citations
    citations = build_citations([], used_indices=[])
    assert citations == []


def test_build_citations_out_of_range_index_ignored():
    from app.provenance.tracker import build_citations
    docs = [make_doc(1)]
    # Index 99 is out of range — should not crash
    citations = build_citations(docs, used_indices=[1, 99])
    assert len(citations) == 1