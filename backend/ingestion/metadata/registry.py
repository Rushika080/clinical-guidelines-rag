import json
import logging
from pathlib import Path
from typing import Optional
from ingestion.metadata.schema import GuidelineMetadata

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).resolve().parents[3] / "data" / "guideline_registry.json"

def load_registry() -> list[GuidelineMetadata]:
    """
    Load all registered guidelines from the JSON registry file.
    Returns a list of GuidelineMetadata objects.
    Skips entries with missing local_path or required fields.
    """
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Registry not found at {REGISTRY_PATH}")

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    guidelines = []
    for entry in data.get("guidelines", []):
        try:
            meta = GuidelineMetadata(
                guideline_id=entry["guideline_id"],
                title=entry["title"],
                organization=entry["organization"],
                specialty=entry["specialty"],
                document_type=entry.get("document_type", "clinical_guideline"),
                publication_year=entry.get("publication_year"),
                version=entry.get("version"),
                source_url=entry.get("source_url"),
                evidence_system=entry.get("evidence_system"),
                last_updated=entry.get("last_updated"),
            )
            guidelines.append(meta)
            logger.info(f"Registered guideline: {meta.guideline_id}")
        except KeyError as e:
            logger.warning(f"Skipping malformed registry entry — missing field: {e}")

    logger.info(f"Loaded {len(guidelines)} guidelines from registry")
    return guidelines


def get_guideline_by_id(guideline_id: str) -> Optional[GuidelineMetadata]:
    """Return a single guideline metadata object by ID, or None if not found."""
    for g in load_registry():
        if g.guideline_id == guideline_id:
            return g
    return None