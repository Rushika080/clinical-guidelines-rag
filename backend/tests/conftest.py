import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import os

# Set dummy env vars before importing the app
# This allows tests to run without real API keys
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("PINECONE_API_KEY", "test-key")
os.environ.setdefault("COHERE_API_KEY", "test-key")
os.environ.setdefault("LANGCHAIN_API_KEY", "test-key")
os.environ.setdefault("PINECONE_INDEX_NAME", "test-index")
os.environ.setdefault("PINECONE_ENVIRONMENT", "us-east-1-aws")


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture
def sample_metadata():
    from ingestion.metadata.schema import GuidelineMetadata
    return GuidelineMetadata(
        guideline_id="test-guideline-001",
        title="Test Clinical Guideline 2024",
        organization="Test Organization",
        specialty="diabetes",
        publication_year=2024,
        version="2024",
        source_url="https://example.org/guideline",
        evidence_system="Test A/B/C",
    )