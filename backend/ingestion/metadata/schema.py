from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GuidelineMetadata:
    """
    Structured metadata for a single clinical guideline document.

    All fields except guideline_id and title are Optional because
    not every public guideline document provides all fields.
    We use None rather than inventing values.

    This dataclass serializes to a dict for Pinecone metadata storage.
    Every chunk produced from this document inherits these fields
    plus chunk-level fields (section, page_number, evidence_grade).
    """

    # Required — every document must have these
    guideline_id: str          # e.g. "ada-smc-2024"
    title: str                 # Full official title
    organization: str          # e.g. "American Diabetes Association"
    specialty: str             # e.g. "diabetes"
    document_type: str = "clinical_guideline"

    # Strongly recommended — include where available
    publication_year: Optional[int] = None
    version: Optional[str] = None     # e.g. "2024 Standards of Care"
    source_url: Optional[str] = None
    evidence_system: Optional[str] = None  # e.g. "ADA A/B/C/E", "ACC Class I/IIa"
    last_updated: Optional[str] = None    # ISO date string

    def to_dict(self) -> dict:
        """
        Serialize to a flat dict suitable for Pinecone metadata.
        Pinecone metadata values must be str, int, float, bool, or list[str].
        None values are excluded to keep the metadata clean.
        """
        return {
            k: v
            for k, v in {
                "guideline_id": self.guideline_id,
                "title": self.title,
                "organization": self.organization,
                "specialty": self.specialty,
                "document_type": self.document_type,
                "publication_year": self.publication_year,
                "version": self.version,
                "source_url": self.source_url,
                "evidence_system": self.evidence_system,
                "last_updated": self.last_updated,
            }.items()
            if v is not None
        }