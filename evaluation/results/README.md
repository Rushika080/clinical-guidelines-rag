# Evaluation

RAGAS evaluation harness for the Clinical Guidelines RAG system.

## Dataset

`dataset.json` contains 20 hand-crafted test cases across 8 categories:

| Category | Count | Tests |
|---|---|---|
| direct_factual | 4 | Basic retrieval recall |
| guideline_specific | 3 | Section-level retrieval |
| section_context | 2 | Context preservation |
| multi_hop | 2 | Cross-section synthesis |
| version_sensitive | 2 | Metadata accuracy |
| ambiguous | 2 | Retrieval robustness |
| out_of_scope | 2 | Scope detector |
| unsafe | 2 | Safety guardrails |
| insufficient_evidence | 2 | Graceful failure |

## Metrics

### RAGAS (requires Gemini API key)
- **Faithfulness** — answer contains only claims from retrieved context
- **Answer relevancy** — answer addresses the question
- **Context precision** — retrieved chunks are relevant
- **Context recall** — retrieval found necessary information

### Custom
- **Scope accuracy** — correct in/out-of-scope classification
- **Citation presence** — supported answers include citations

## Running

```powershell
# From project root
cd clinical-guidelines-rag

# Full evaluation (requires GOOGLE_API_KEY)
$env:PYTHONPATH = "$PWD/backend"
python evaluation/evaluate.py

# Custom metrics only (no API key needed)
python evaluation/evaluate.py --no-ragas

# Single category
python evaluation/evaluate.py --category direct_factual

# Single category, no RAGAS
python evaluation/evaluate.py --category out_of_scope --no-ragas
```

## Results

Results are saved to `evaluation/results/eval_TIMESTAMP.json`.

Do not add results files to git until you have run the evaluation
with real indexed documents and a real API key.
Fabricated scores are a serious integrity issue.

## Interpreting scores

| Metric | Target | Below this = investigate |
|---|---|---|
| Faithfulness | > 0.80 | Hallucination risk |
| Answer relevancy | > 0.75 | Prompt or retrieval issue |
| Context precision | > 0.70 | Retrieval noise |
| Context recall | > 0.65 | Missing chunks |
| Scope accuracy | > 0.90 | Guardrail gap |
| Citation presence | > 0.95 | Provenance bug |