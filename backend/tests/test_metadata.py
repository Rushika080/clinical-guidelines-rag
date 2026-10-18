from ingestion.metadata.schema import GuidelineMetadata


def test_metadata_to_dict_excludes_none(sample_metadata):
    d = sample_metadata.to_dict()
    # None fields must not appear in the Pinecone metadata dict
    assert all(v is not None for v in d.values())


def test_metadata_to_dict_contains_required_fields(sample_metadata):
    d = sample_metadata.to_dict()
    assert d["guideline_id"] == "test-guideline-001"
    assert d["organization"] == "Test Organization"
    assert d["specialty"] == "diabetes"


def test_metadata_without_optional_fields():
    meta = GuidelineMetadata(
        guideline_id="minimal-001",
        title="Minimal Guideline",
        organization="Org",
        specialty="cardiology",
    )
    d = meta.to_dict()
    # Optional fields with None should be absent
    assert "publication_year" not in d
    assert "source_url" not in d