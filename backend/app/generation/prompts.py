"""
Prompt templates for evidence-grounded clinical guideline answers.

PROMPT ENGINEERING DECISIONS:

1. EVIDENCE-ONLY INSTRUCTION
   The LLM is explicitly told: use ONLY the evidence below.
   Do not use general medical knowledge.
   This is the most important constraint — without it, the LLM will
   confidently answer from its pretrained knowledge, which may be
   outdated, from a different population, or simply hallucinated.

2. STRUCTURED OUTPUT REQUEST
   We ask for a JSON response so we can parse citations programmatically.
   The alternative (parsing free-text citations) is brittle and unreliable.

3. CONFLICT DETECTION
   If multiple sources disagree, the prompt requires the LLM to report
   them separately rather than picking one and hiding the disagreement.
   This is critical for clinical safety.

4. UNCERTAINTY EXPRESSION
   The LLM is instructed to say "The indexed guidelines do not contain
   sufficient evidence to answer this question" rather than fabricating
   an answer. This is more valuable to a clinician than a confident wrong answer.
"""

SYSTEM_PROMPT = """You are a clinical guidelines information assistant.

Your role is to help healthcare professionals and researchers find evidence-based 
recommendations from indexed clinical guidelines.

CRITICAL RULES — you must follow these without exception:
1. Answer ONLY using the evidence passages provided below. Do not use your general 
   medical knowledge or training data.
2. Do not fabricate citations, guideline sections, page numbers, or evidence grades.
3. If the evidence is insufficient to answer the question, say so explicitly.
4. If different guidelines disagree, present BOTH recommendations separately 
   with their sources. Never choose one and hide the other.
5. Never provide personalised medical advice, diagnosis, or treatment decisions.
6. Always attribute every claim to its source passage.
7. Mention the guideline year and version when making recommendations — 
   older guidelines may have been superseded.

You are an information retrieval assistant, NOT a treating clinician.
"""

EVIDENCE_GROUNDED_PROMPT = """EVIDENCE PASSAGES (retrieved from indexed clinical guidelines):

{evidence_text}

---

QUESTION: {question}

---

Using ONLY the evidence passages above, provide a structured answer.

If the evidence supports an answer, respond with this JSON:
{{
  "answer": "Your evidence-grounded answer here",
  "evidence_summary": "Brief summary of what the evidence says",
  "conflicting_guidelines": false,
  "citations_used": [1, 2]
}}

If guidelines conflict, set conflicting_guidelines to true and present 
each source's position separately in the answer.

If the evidence is insufficient, respond with:
{{
  "answer": "The indexed guidelines do not contain sufficient evidence to answer this question.",
  "evidence_summary": "No relevant evidence found in indexed guidelines.",
  "conflicting_guidelines": false,
  "citations_used": []
}}

Respond with valid JSON only. No preamble, no markdown fences.
"""


def format_evidence_text(documents: list) -> str:
    """
    Format retrieved documents into numbered evidence passages
    for inclusion in the prompt.

    Each passage is numbered so the LLM can reference it in citations_used.
    Metadata (org, year, section, page) is included so the LLM can
    cite it accurately without fabricating details.
    """
    if not documents:
        return "No evidence passages retrieved."

    passages = []
    for i, doc in enumerate(documents, 1):
        meta = doc.metadata
        header_parts = [f"[{i}]"]

        if meta.get("organization"):
            header_parts.append(meta["organization"])
        if meta.get("title"):
            header_parts.append(f'"{meta["title"]}"')
        if meta.get("publication_year"):
            header_parts.append(f"({meta['publication_year']})")
        if meta.get("section"):
            header_parts.append(f"Section: {meta['section']}")
        if meta.get("page_number"):
            header_parts.append(f"Page {meta['page_number']}")
        if meta.get("evidence_grade"):
            header_parts.append(f"Evidence grade: {meta['evidence_grade']}")

        header = " | ".join(header_parts)
        passage = f"{header}\n{doc.page_content}"
        passages.append(passage)

    return "\n\n---\n\n".join(passages)