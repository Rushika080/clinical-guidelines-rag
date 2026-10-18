"""
Section/heading detector for clinical guideline PDFs.

Clinical guidelines have a consistent structure:
  - Section headings (large bold text, e.g. "SECTION 3. GLYCEMIC TARGETS")
  - Subsection headings (medium bold, e.g. "3.1 A1C Goals")
  - Body text
  - Recommendation boxes (often ALL CAPS or prefixed with evidence grade)

Strategy:
  We use font size + bold flag heuristics to detect headings.
  This is intentionally simple and robust — ML-based parsers are overkill
  and brittle across different PDF layouts.

  For each page we assign a "current_section" and "current_subsection"
  that gets attached to every chunk produced from that page.
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Evidence grade patterns seen in major guidelines
# ADA: "A", "B", "C", "E"
# ACC/AHA: "Class I", "Class IIa", "Class IIb", "Class III"
# WHO: "Strong", "Conditional"
EVIDENCE_GRADE_PATTERNS = [
    r"\b(Grade\s+[A-C]|Level\s+[1-3]|Class\s+I{1,3}[ab]?|Class\s+III)\b",
    r"\b(Strong recommendation|Conditional recommendation)\b",
    r"^\s*([A-E])\s*$",  # standalone letter grades in ADA style
]
EVIDENCE_GRADE_RE = re.compile(
    "|".join(EVIDENCE_GRADE_PATTERNS), re.IGNORECASE
)


def detect_headings(font_blocks: list[tuple]) -> dict[str, float]:
    """
    Analyse font sizes across all blocks to determine heading thresholds.

    Returns a dict with:
        "body":       most common font size (body text baseline)
        "subsection": font size threshold for subsection headings
        "section":    font size threshold for section headings
    """
    if not font_blocks:
        return {"body": 10.0, "subsection": 12.0, "section": 14.0}

    sizes = [size for _, size, _ in font_blocks if size > 0]
    if not sizes:
        return {"body": 10.0, "subsection": 12.0, "section": 14.0}

    # Body text = most frequent size
    from collections import Counter
    size_counts = Counter(round(s, 1) for s in sizes)
    body_size = size_counts.most_common(1)[0][0]

    return {
        "body": body_size,
        "subsection": body_size + 1.5,
        "section": body_size + 3.0,
    }


def is_bold(flags: int) -> bool:
    """
    Check if a font span is bold.
    PyMuPDF font flags: bit 4 (value 16) = bold.
    """
    return bool(flags & 16)


def parse_sections(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Walk through all pages and attach section/subsection metadata.

    Input:  pages from load_pdf_pages()
    Output: same list with two new keys per page:
              - "section":    current section heading (str or None)
              - "subsection": current subsection heading (str or None)

    We carry section state forward across pages — a section that starts
    on page 5 is still the current section on page 6 until a new one appears.
    """
    # First pass: compute heading thresholds from the whole document
    all_blocks = []
    for page in pages:
        all_blocks.extend(page.get("font_blocks", []))
    thresholds = detect_headings(all_blocks)

    logger.info(
        f"Heading thresholds — body: {thresholds['body']:.1f}pt, "
        f"subsection: {thresholds['subsection']:.1f}pt, "
        f"section: {thresholds['section']:.1f}pt"
    )

    current_section = None
    current_subsection = None
    enriched_pages = []

    for page in pages:
        font_blocks = page.get("font_blocks", [])

        for text, size, flags in font_blocks:
            text_clean = text.strip()
            if not text_clean or len(text_clean) < 3:
                continue

            if size >= thresholds["section"] and is_bold(flags):
                current_section = text_clean[:200]   # cap length
                current_subsection = None             # new section resets subsection
            elif size >= thresholds["subsection"] and is_bold(flags):
                current_subsection = text_clean[:200]

        enriched_pages.append({
            **page,
            "section": current_section,
            "subsection": current_subsection,
        })

    return enriched_pages


def extract_evidence_grade(text: str) -> str | None:
    """
    Attempt to extract an evidence grade from a chunk of text.

    Returns the grade string if found (e.g. "Class I", "Grade A"),
    or None if no recognizable grade pattern is present.

    IMPORTANT: We never invent a grade. If nothing matches, return None.
    """
    match = EVIDENCE_GRADE_RE.search(text)
    if match:
        return match.group(0).strip()
    return None