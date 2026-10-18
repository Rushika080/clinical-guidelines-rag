"""
Output safety guardrails.

Applied AFTER generation to catch any LLM output that
inadvertently sounds like personal medical advice.

This is a secondary safety layer — scope_detector.py is the primary one.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Phrases the LLM should never produce in a guideline answer
UNSAFE_OUTPUT_PATTERNS = [
    r"you should (take|inject|start|stop|increase|decrease)",
    r"i recommend (you|taking|starting)",
    r"your (dose|dosage|medication) should",
    r"based on your (symptoms|condition|history)",
]

DISCLAIMER_ADDITION = (
    "\n\n⚠️ Note: This information is drawn from indexed clinical guidelines "
    "and is for educational purposes only. It does not constitute personal "
    "medical advice."
)


def apply_output_guardrails(answer: str) -> str:
    """
    Scan the generated answer for unsafe patterns.
    If found, append a prominent disclaimer.
    Does not modify or redact the answer — we add a warning instead
    so the user sees both the information and the caution.
    """
    answer_lower = answer.lower()
    for pattern in UNSAFE_OUTPUT_PATTERNS:
        if re.search(pattern, answer_lower):
            logger.warning(
                f"Unsafe output pattern detected: '{pattern}'. "
                f"Appending disclaimer."
            )
            if DISCLAIMER_ADDITION not in answer:
                answer += DISCLAIMER_ADDITION
            break
    return answer