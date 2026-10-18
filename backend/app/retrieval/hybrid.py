import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

ORG_PATTERNS = {
    r"\bADA\b|american diabetes": "American Diabetes Association",
    r"\bAHA\b|american heart": "American Heart Association",
    r"\bACC\b|american college of cardiology": "American College of Cardiology",
    r"\bWHO\b|world health": "World Health Organization",
    r"\bCDC\b|centers for disease": "Centers for Disease Control",
    r"\bASCO\b|american society of clinical oncology": "American Society of Clinical Oncology",
}

SPECIALTY_PATTERNS = {
    r"\bdiabet": "diabetes",
    r"\bcardio|heart failure|hypertension": "cardiology",
    r"\bonco|cancer|tumor": "oncology",
    r"\binfectious|sepsis|antibiotic": "infectious_disease",
}


def detect_org_filter(query: str) -> Optional[str]:
    query_lower = query.lower()
    for pattern, org_value in ORG_PATTERNS.items():
        if re.search(pattern, query_lower, re.IGNORECASE):
            logger.info(f"Detected organisation filter: {org_value}")
            return org_value
    return None


def detect_specialty_filter(query: str, explicit_specialty: Optional[str]) -> Optional[str]:
    if explicit_specialty:
        return explicit_specialty.lower()
    query_lower = query.lower()
    for pattern, specialty in SPECIALTY_PATTERNS.items():
        if re.search(pattern, query_lower, re.IGNORECASE):
            logger.info(f"Detected specialty filter: {specialty}")
            return specialty
    return None


def build_pinecone_filter(
    query: str,
    specialty: Optional[str] = None,
    organization: Optional[str] = None,
    year: Optional[int] = None,
    guideline_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Build a ChromaDB metadata filter.

    ChromaDB WHERE clause syntax (NOT Pinecone):
      Single condition:   {"field": "value"}
      Multiple conditions: {"$and": [{"field": "value"}, {"field2": "value2"}]}

    IMPORTANT: ChromaDB does NOT support {"field": {"$eq": "value"}} syntax.
    Use flat {"field": "value"} instead.
    """
    conditions = []

    # guideline_id is most specific — use alone
    if guideline_id:
        return {"guideline_id": guideline_id}

    # Organisation
    org_filter = organization or detect_org_filter(query)
    if org_filter:
        conditions.append({"organization": org_filter})

    # Specialty
    specialty_filter = detect_specialty_filter(query, specialty)
    if specialty_filter:
        conditions.append({"specialty": specialty_filter})

    # Year
    if year:
        conditions.append({"publication_year": year})

    # Always filter to child chunks only
    conditions.append({"chunk_type": "child"})

    if len(conditions) == 1:
        return conditions[0]
    if len(conditions) > 1:
        return {"$and": conditions}
    return None