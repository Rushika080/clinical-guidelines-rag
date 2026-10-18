class ClinicalRAGException(Exception):
    """Base exception for all application errors."""


class GuidelineNotFoundError(ClinicalRAGException):
    """Raised when a requested guideline ID does not exist in the registry."""


class OutOfScopeError(ClinicalRAGException):
    """Raised when the user query is outside the system's supported scope."""


class InsufficientEvidenceError(ClinicalRAGException):
    """Raised when retrieval returns no sufficiently relevant evidence."""


class IngestionError(ClinicalRAGException):
    """Raised when document ingestion fails."""


class RetrievalError(ClinicalRAGException):
    """Raised when vector retrieval fails."""