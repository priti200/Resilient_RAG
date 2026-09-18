# Proposal Traceability Checklist

| Proposal requirement | Implementation evidence | Status |
|---|---|---|
| Step 1: define attack and threat model | `docs/attack_model.md` | Complete, bibliography expansion recommended |
| Step 2: collect and clean data | `data/cleaned/`, preprocessing reports | Complete; GeNIS used instead of CIC-IDS2017 |
| Step 3: convert network records to text | `src/representation/`, processed JSONL | Complete |
| Step 4: compare chunking methods | semantic, fixed, agentic modules and tests | Complete; agentic evaluated on 1,000-flow sample |
| Step 5: clean knowledge base | 100K proportional and balanced FAISS indexes | Complete |
| Step 6: create attack samples | 480-record attack catalog | Complete |
| Step 7: poison KB copies | 0.1%, 0.5%, 1% proportional and balanced copies | Complete |
| Step 8: pre-check filter | schema/instruction filter, tuned config | Complete on current samples |
| Step 9: post-check verification | cross-encoder and refusal rule | Complete; threshold tuned on validation |
| Step 10: undefended baseline | shared query engine with defense disabled | Complete |
| Step 11: run experiments | 200 clean test runs + 360 attack runs | Complete for single-seed bounded matrix |
| Step 12: analyze and report | summaries, paired tests, evaluation report | Complete for current runs; repeated-seed work remains |

## Proposal Deliverables

- Attack benchmark: `data/processed/attacks/attack_catalog.jsonl`.
- Defense system: `src/chunking/`, `src/defense/`, and `src/pipeline/`.
- Reusable code and tests: `src/`, `scripts/`, and `tests/`.
- Evaluation results: `experiments/` and `docs/evaluation_report.md`.
- Thesis/paper source text: not generated as a complete institution-formatted
  document; the report contains the verified implementation and results.

## Limitations to State in Submission

- GeNIS replaces CIC-IDS2017.
- Results use one main random seed and bounded attack samples.
- External-dataset validation was not performed.
- Agentic chunking was evaluated on a 1,000-flow sample because per-decision
  Ollama calls are expensive at full KB scale.
- ASR results require an explicit poisoned-entry retrieval-reach metric before
  being treated as definitive attack-success evidence.
- The literature bibliography must be expanded and formatted according to the
  institution's required citation style.
