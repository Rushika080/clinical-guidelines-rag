"""
PDF loader using PyMuPDF (fitz).

Why PyMuPDF over LangChain's built-in loaders?
- Page numbers are preserved accurately per block
- We can extract font size / boldness for section detection
- Text extraction is faster and more reliable for dense clinical PDFs
- We get full control over how text is assembled per page

Output: list of dicts, one per page, each containing:
  - page_number (1-indexed, matching the PDF's printed page)
  - text
  - font_info: list of (text, size, flags) tuples for section detection
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_pdf_pages(pdf_path: str | Path) -> list[dict[str, Any]]:
    """
    Load a PDF and return a list of page dicts.

    Each dict:
        {
            "page_number": int,      # 1-indexed
            "text": str,             # full page text
            "font_blocks": list      # [(text, font_size, font_flags), ...]
        }

    font_flags: PyMuPDF integer where bit 4 = bold, bit 1 = italic.
    We use font_size and bold flag downstream to detect section headings.

    Raises:
        FileNotFoundError: if the PDF does not exist at pdf_path
        RuntimeError: if PyMuPDF fails to open the file
    """
    try:
        import fitz  # PyMuPDF imports as fitz
    except ImportError:
        raise ImportError("PyMuPDF is required. Run: pip install pymupdf")

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info(f"Loading PDF: {pdf_path.name}")

    pages = []
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        raise RuntimeError(f"Failed to open PDF {pdf_path}: {e}")

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1  # convert to 1-indexed

        # Extract plain text for the page
        text = page.get_text("text").strip()

        # Extract block-level font information for heading detection.
        # get_text("dict") returns blocks → lines → spans, each span
        # has font size and flags. We flatten to (span_text, size, flags).
        font_blocks = []
        try:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get("type") != 0:  # type 0 = text block
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_text = span.get("text", "").strip()
                        if span_text:
                            font_blocks.append((
                                span_text,
                                span.get("size", 0),
                                span.get("flags", 0),
                            ))
        except Exception as e:
            # Non-fatal: fall back to text-only if font extraction fails
            logger.warning(f"Font extraction failed on page {page_number}: {e}")

        if text:  # skip completely blank pages
            pages.append({
                "page_number": page_number,
                "text": text,
                "font_blocks": font_blocks,
            })

    doc.close()
    logger.info(f"Loaded {len(pages)} non-empty pages from {pdf_path.name}")
    return pages