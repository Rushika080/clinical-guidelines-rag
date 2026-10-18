"""
RAGAS evaluation harness for the Clinical Guidelines RAG system.
Uses RAGAS 0.2.0 API.

METRICS EVALUATED:

Standard RAGAS metrics:
  - Faithfulness:      Does the answer contain only claims supported by the context?
  - Answer Relevancy:  Does the answer address the question asked?
  - Context Precision: Are the retrieved chunks actually relevant to the question?
  - Context Recall:    Did retrieval find the chunks needed to answer correctly?

Custom metrics:
  - Scope accuracy:    Did the system correctly classify in/out of scope questions?
  - Citation presence: Did supported answers include at least one citation?

HOW TO RUN:
  cd clinical-guidelines-rag/clinical-guidelines-rag
  $env:PYTHONPATH = "$PWD/backend"
  python evaluation/evaluate.py

  # Run only specific categories:
  python evaluation/evaluate.py --category direct_factual

  # Run without RAGAS (scope + citation metrics only, no API needed):
  python evaluation/evaluate.py --no-ragas

IMPORTANT:
  RAGAS metrics require the Gemini API key (GOOGLE_API_KEY in .env).
  Without it, only scope_accuracy and citation_presence are computed.
  Do not fabricate scores — run the script to get real numbers.
"""

import argparse
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import time

# ── Path setup ───────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv
load_dotenv(BACKEND / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).parent / "dataset.json"
RESULTS_DIR  = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ── Load dataset ─────────────────────────────────────────────────────────

def load_dataset(category: str = None) -> list[dict]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    cases = data["test_cases"]
    if category:
        cases = [c for c in cases if c["category"] == category]
        logger.info(f"Filtered to category '{category}': {len(cases)} cases")
    return cases


# ── Run pipeline on test cases ────────────────────────────────────────────

def run_pipeline_on_cases(test_cases: list[dict]) -> list[dict]:
    """
    Run the full RAG pipeline on each test case.
    Returns a list of result dicts with question, answer, contexts, ground_truth.
    """
    from app.generation.chain import answer_question

    results = []
    for i, tc in enumerate(test_cases):
        logger.info(f"[{i+1}/{len(test_cases)}] Running: {tc['id']} — {tc['question'][:60]}")
        try:
            response = answer_question(tc["question"])
            results.append({
                "id":             tc["id"],
                "category":       tc["category"],
                "question":       tc["question"],
                "ground_truth":   tc["ground_truth"],
                "answer":         response.answer,
                "scope_status":   response.scope_status.value,
                "expected_scope": tc["expected_scope"],
                "citations":      [c.model_dump() for c in response.citations],
                "contexts":       [],  # filled below for RAGAS
                "error":          None,
            })
        except Exception as e:
            logger.error(f"Pipeline failed for {tc['id']}: {e}")
            results.append({
                "id":             tc["id"],
                "category":       tc["category"],
                "question":       tc["question"],
                "ground_truth":   tc["ground_truth"],
                "answer":         "",
                "scope_status":   "error",
                "expected_scope": tc["expected_scope"],
                "citations":      [],
                "contexts":       [],
                "error":          str(e),
            })
        if tc["expected_scope"] not in ("out_of_scope", "unsafe"):
            logger.info("Waiting 15s for Gemini rate limit...")
            time.sleep(15)
    return results


def enrich_with_contexts(results: list[dict]) -> list[dict]:
    """
    For RAGAS we need the retrieved context chunks alongside the answer.
    Re-run retrieval to get them (retrieval is fast after model is cached).
    """
    from app.retrieval.pipeline import retrieve_evidence

    for r in results:
        if r["scope_status"] in ("out_of_scope", "unsafe", "error"):
            r["contexts"] = []
            continue
        try:
            retrieval = retrieve_evidence(r["question"])
            r["contexts"] = [
                doc.page_content
                for doc in retrieval.get("documents", [])
            ]
        except Exception as e:
            logger.warning(f"Context retrieval failed for {r['id']}: {e}")
            r["contexts"] = []
    return results


# ── Custom metrics ────────────────────────────────────────────────────────

def compute_scope_accuracy(results: list[dict]) -> dict:
    """
    Measure how accurately the system classifies question scope.

    scope_accuracy = correct_scope_predictions / total_cases

    A prediction is correct when:
      expected_scope == "supported"    and system returned "supported"
      expected_scope == "out_of_scope" and system returned "out_of_scope"
      expected_scope == "unsafe"       and system returned "unsafe"
      expected_scope == "insufficient" and system returned "insufficient"
    """
    total   = len(results)
    correct = 0
    errors  = []

    for r in results:
        expected = r["expected_scope"]
        actual   = r["scope_status"]

        # Allow "supported" and "insufficient" to be somewhat interchangeable
        # (retrieval may or may not find evidence for ambiguous questions)
        is_correct = (
            expected == actual or
            (expected == "supported"    and actual == "insufficient") or
            (expected == "insufficient" and actual == "supported")
        )

        if is_correct:
            correct += 1
        else:
            errors.append({
                "id":       r["id"],
                "expected": expected,
                "actual":   actual,
                "question": r["question"][:80],
            })

    accuracy = correct / total if total > 0 else 0.0
    return {
        "score":   round(accuracy, 3),
        "correct": correct,
        "total":   total,
        "errors":  errors,
    }


def compute_citation_presence(results: list[dict]) -> dict:
    """
    For questions where scope_status == 'supported',
    what fraction include at least one citation?

    citation_presence = supported_with_citations / total_supported
    """
    supported = [r for r in results if r["scope_status"] == "supported"]
    if not supported:
        return {"score": 0.0, "supported_count": 0, "with_citations": 0}

    with_citations = sum(1 for r in supported if len(r["citations"]) > 0)
    score = with_citations / len(supported)

    return {
        "score":           round(score, 3),
        "supported_count": len(supported),
        "with_citations":  with_citations,
    }


# ── RAGAS metrics ─────────────────────────────────────────────────────────

def compute_ragas_metrics(results: list[dict]) -> dict:
    """
    Run RAGAS 0.2.0 evaluation on supported questions only.
    Skips out_of_scope / unsafe / error cases (no context to evaluate).
    """
    try:
        from ragas import evaluate, EvaluationDataset
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as e:
        logger.error(f"RAGAS import failed: {e}")
        return {"error": str(e)}

    # Filter to only supported cases with contexts
    eval_cases = [
        r for r in results
        if r["scope_status"] == "supported"
        and r["contexts"]
        and r["answer"]
    ]

    if not eval_cases:
        logger.warning("No supported cases with contexts found for RAGAS evaluation.")
        return {"error": "No evaluable cases"}

    logger.info(f"Running RAGAS on {len(eval_cases)} supported cases...")

    # Build RAGAS 0.2.0 dataset format
    ragas_data = []
    for r in eval_cases:
        ragas_data.append({
            "user_input":          r["question"],
            "response":            r["answer"],
            "retrieved_contexts":  r["contexts"],
            "reference":           r["ground_truth"],
        })

    try:
        dataset = EvaluationDataset.from_list(ragas_data)
    except Exception as e:
        logger.error(f"Failed to build RAGAS dataset: {e}")
        return {"error": str(e)}

    # Use Gemini as the evaluation LLM
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not google_api_key:
        return {
            "error": (
                "GOOGLE_API_KEY not set. "
                "RAGAS metrics require an LLM judge. "
                "Set GOOGLE_API_KEY in backend/.env and rerun."
            )
        }

    try:
        llm = LangchainLLMWrapper(
            ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=google_api_key,
            )
        )
        embeddings = LangchainEmbeddingsWrapper(
            HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        )

        score_result = evaluate(
            dataset=dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ],
            llm=llm,
            embeddings=embeddings,
        )

        df = score_result.to_pandas()
        return {
            "faithfulness":      round(float(df["faithfulness"].mean()),      3),
            "answer_relevancy":  round(float(df["answer_relevancy"].mean()),  3),
            "context_precision": round(float(df["context_precision"].mean()), 3),
            "context_recall":    round(float(df["context_recall"].mean()),    3),
            "evaluated_cases":   len(eval_cases),
            "per_question":      df.to_dict(orient="records"),
        }

    except Exception as e:
        logger.error(f"RAGAS evaluation failed: {e}", exc_info=True)
        return {"error": str(e)}


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RAGAS evaluation for Clinical Guidelines RAG"
    )
    parser.add_argument(
        "--category",
        help="Evaluate only a specific category (e.g. direct_factual)",
    )
    parser.add_argument(
        "--no-ragas",
        action="store_true",
        help="Skip RAGAS metrics — only compute scope accuracy and citation presence",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        default=True,
        help="Save results to evaluation/results/ (default: True)",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Clinical Guidelines RAG — RAGAS Evaluation")
    logger.info("=" * 60)

    # Load test cases
    test_cases = load_dataset(category=args.category)
    logger.info(f"Loaded {len(test_cases)} test cases")

    # Run pipeline
    logger.info("\nStep 1: Running RAG pipeline on all test cases...")
    results = run_pipeline_on_cases(test_cases)

    # Enrich with contexts for RAGAS
    if not args.no_ragas:
        logger.info("\nStep 2: Retrieving contexts for RAGAS evaluation...")
        results = enrich_with_contexts(results)

    # Custom metrics — no API needed
    logger.info("\nStep 3: Computing custom metrics...")
    scope_metrics     = compute_scope_accuracy(results)
    citation_metrics  = compute_citation_presence(results)

    # RAGAS metrics
    ragas_metrics = {}
    if not args.no_ragas:
        logger.info("\nStep 4: Computing RAGAS metrics (requires Gemini API)...")
        ragas_metrics = compute_ragas_metrics(results)

    # ── Print report ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    print("\n── Custom Metrics ──")
    print(f"Scope accuracy:    {scope_metrics['score']:.3f}  "
          f"({scope_metrics['correct']}/{scope_metrics['total']} correct)")
    print(f"Citation presence: {citation_metrics['score']:.3f}  "
          f"({citation_metrics['with_citations']}/{citation_metrics['supported_count']} "
          f"supported answers have citations)")

    if scope_metrics["errors"]:
        print(f"\nScope misclassifications ({len(scope_metrics['errors'])}):")
        for e in scope_metrics["errors"]:
            print(f"  {e['id']}: expected={e['expected']} got={e['actual']}")
            print(f"    '{e['question']}'")

    print("\n── RAGAS Metrics ──")
    if "error" in ragas_metrics:
        print(f"RAGAS skipped: {ragas_metrics['error']}")
    else:
        print(f"Faithfulness:      {ragas_metrics.get('faithfulness',      'N/A')}")
        print(f"Answer relevancy:  {ragas_metrics.get('answer_relevancy',  'N/A')}")
        print(f"Context precision: {ragas_metrics.get('context_precision', 'N/A')}")
        print(f"Context recall:    {ragas_metrics.get('context_recall',    'N/A')}")
        print(f"Evaluated cases:   {ragas_metrics.get('evaluated_cases',   'N/A')}")

    print("\n── Per-category breakdown ──")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "scope_correct": 0, "with_citations": 0}
        categories[cat]["total"] += 1
        expected = r["expected_scope"]
        actual   = r["scope_status"]
        if expected == actual or \
           (expected == "supported" and actual == "insufficient") or \
           (expected == "insufficient" and actual == "supported"):
            categories[cat]["scope_correct"] += 1
        if r["scope_status"] == "supported" and r["citations"]:
            categories[cat]["with_citations"] += 1

    for cat, stats in sorted(categories.items()):
        scope_acc = stats["scope_correct"] / stats["total"]
        print(f"  {cat:<25} scope={scope_acc:.2f}  n={stats['total']}")

    # ── Save results ──────────────────────────────────────────────────────
    if args.save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = {
            "timestamp":        timestamp,
            "total_cases":      len(test_cases),
            "category_filter":  args.category,
            "scope_accuracy":   scope_metrics,
            "citation_presence": citation_metrics,
            "ragas_metrics":    ragas_metrics,
            "per_case_results": results,
        }
        out_path = RESULTS_DIR / f"eval_{timestamp}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {out_path}")

    print("=" * 60)


if __name__ == "__main__":
    main()