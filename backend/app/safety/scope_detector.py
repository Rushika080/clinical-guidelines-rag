"""
Scope detection — determines whether a question is answerable
from the indexed clinical guidelines.

THREE OUTCOMES:
  1. SUPPORTED     — question is about clinical guidelines; proceed
  2. OUT_OF_SCOPE  — question is personal advice / diagnosis / outside medicine
  3. UNSAFE        — question asks for something the system must never do

WHY THIS MATTERS:
  Without scope detection, the LLM would either hallucinate an answer
  from its pretrained knowledge (violating evidence-grounding) or
  return a confusing "I don't know" without explaining why.

  Explicit scope detection lets us return a clear, honest message:
  "This system answers questions about clinical guidelines. Your question
  appears to be asking for personal medical advice, which is outside scope."

APPROACH:
  Rule-based pattern matching first (fast, no LLM call needed).
  This handles the obvious cases (diagnosis requests, personal advice).
  For ambiguous cases we let retrieval proceed — if evidence is found,
  the question is in scope; if not, we return INSUFFICIENT.
"""

import re
import logging
from app.models.response import ScopeStatus

logger = logging.getLogger(__name__)

# Patterns that indicate a request for personal diagnosis or treatment
PERSONAL_ADVICE_PATTERNS = [
    r"\b(my|i have|i am|i've been|i feel|i'm experiencing)\b",
    r"\bdo i have\b",
    r"\bshould i take\b",
    r"\bwhat should i (do|take|eat|drink)\b",
    r"\bam i (diabetic|hypertensive|at risk)\b",
    r"\bdiagnose me\b",
    r"\bmy symptoms\b",
    r"\bmy doctor\b.*\btold me\b",
]

# Patterns that indicate a request the system must never fulfil
UNSAFE_PATTERNS = [
    r"\bprescribe\b.*\bme\b",
    r"\bwhat (dose|dosage) should i\b",
    r"\bhow much (insulin|metformin|medication) should i (take|inject)\b",
    r"\btreat my\b",
    r"\bcure (my|for my)\b",
]

# Patterns that indicate a question IS about clinical guidelines
# (positive signal — if any match, we lean toward SUPPORTED)
GUIDELINE_PATTERNS = [
    r"\b(guideline|recommendation|recommend|advise|evidence|standard of care)\b",
    r"\b(ADA|WHO|CDC|AHA|ACC|ASCO)\b",
    r"\baccording to\b",
    r"\bwhat does .*(recommend|say|state|advise)\b",
    r"\b(first.line|second.line|treatment protocol)\b",
    r"\b(HbA1c|glycemic|blood pressure|lipid|cholesterol)\b.*\btarget\b",
    r"\b(diabetes|cardiology|oncology|hypertension|heart failure)\b",
]


def detect_scope(question: str) -> tuple[ScopeStatus, str]:
    """
    Analyse a question and return (ScopeStatus, explanation_message).

    The explanation message is shown to the user when the question
    is not supported — it should be helpful, not dismissive.

    Returns:
        (ScopeStatus.UNSAFE, message)        — if safety pattern matched
        (ScopeStatus.OUT_OF_SCOPE, message)  — if personal advice pattern matched
        (ScopeStatus.SUPPORTED, message)     — if guideline pattern matched
        (ScopeStatus.SUPPORTED, "")          — if ambiguous (let retrieval decide)
    """
    q = question.lower().strip()

    # Check unsafe patterns first — highest priority
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            logger.info(f"Unsafe pattern matched: '{pattern}'")
            return (
                ScopeStatus.UNSAFE,
                "This system cannot provide personalised dosage, "
                "prescription, or treatment decisions. Please consult "
                "a qualified healthcare professional for individual "
                "medical advice.",
            )

    # Check for personal advice
    personal_matches = [
        p for p in PERSONAL_ADVICE_PATTERNS
        if re.search(p, q, re.IGNORECASE)
    ]
    if personal_matches:
        logger.info(f"Personal advice pattern matched: {personal_matches[0]}")
        return (
            ScopeStatus.OUT_OF_SCOPE,
            "This system provides information from clinical guidelines "
            "and cannot give personalised medical advice. Your question "
            "appears to be asking about your individual situation. "
            "Please consult a healthcare professional.",
        )

    # Check for positive guideline signals
    for pattern in GUIDELINE_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            return (ScopeStatus.SUPPORTED, "")

    # Ambiguous — let retrieval decide
    # If retrieval returns evidence → SUPPORTED
    # If retrieval returns nothing  → INSUFFICIENT (handled in chain.py)
    logger.info("Ambiguous question — proceeding to retrieval.")
    return (ScopeStatus.SUPPORTED, "")