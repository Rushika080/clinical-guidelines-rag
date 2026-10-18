"""
Tests for the PDF loader.
Uses a minimal synthetic PDF created in-memory — no real PDF file needed.
"""

import pytest
from pathlib import Path
import tempfile


def create_minimal_pdf(path: Path, text: str = "Test clinical guideline content.") -> None:
    """Create a minimal single-page PDF using PyMuPDF for testing."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), text, fontsize=12)
    doc.save(str(path))
    doc.close()


def test_load_pdf_pages_returns_list():
    from ingestion.loaders.pdf_loader import load_pdf_pages
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "test.pdf"
        create_minimal_pdf(pdf_path)
        pages = load_pdf_pages(pdf_path)
        assert isinstance(pages, list)
        assert len(pages) >= 1


def test_load_pdf_pages_has_required_keys():
    from ingestion.loaders.pdf_loader import load_pdf_pages
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "test.pdf"
        create_minimal_pdf(pdf_path)
        pages = load_pdf_pages(pdf_path)
        page = pages[0]
        assert "page_number" in page
        assert "text" in page
        assert "font_blocks" in page


def test_load_pdf_pages_page_number_is_one_indexed():
    from ingestion.loaders.pdf_loader import load_pdf_pages
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "test.pdf"
        create_minimal_pdf(pdf_path)
        pages = load_pdf_pages(pdf_path)
        assert pages[0]["page_number"] == 1


def test_load_pdf_pages_file_not_found():
    from ingestion.loaders.pdf_loader import load_pdf_pages
    with pytest.raises(FileNotFoundError):
        load_pdf_pages("/nonexistent/path/file.pdf")


def test_load_pdf_pages_text_is_nonempty():
    from ingestion.loaders.pdf_loader import load_pdf_pages
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "test.pdf"
        create_minimal_pdf(pdf_path, text="HbA1c targets for diabetes management.")
        pages = load_pdf_pages(pdf_path)
        assert any(len(p["text"]) > 0 for p in pages)