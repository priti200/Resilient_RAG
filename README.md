# Resilient-RAG

This project evaluates layered defenses against knowledge poisoning and
indirect prompt injection in a RAG-based network intrusion detection assistant.
The current implementation uses the GeNIS dataset and local Ollama generation.

## Environment

Use the verified Anaconda environment:

```powershell
conda activate resilient-rag-anaconda
```

Verify the stack:

```powershell
python scripts/setup_check.py
python -m pip check
python -m pytest tests -q
```

The verified stack includes PyTorch `2.6.0+cu124`, CUDA on the RTX 3050,
FAISS, sentence-transformers, and Ollama `qwen2.5:7b`.

## Main Artifacts

- Clean KB sample: `data/processed/kb/clean_sample_100k.jsonl`
- Attack catalog: `data/processed/attacks/attack_catalog.jsonl`
- Poisoned KB copies: `data/processed/kb/poisoned_*.jsonl`
- FAISS indexes: `data/processed/index/`
- Validation queries: `data/processed/queries/validation_queries.jsonl`
- Evaluation results: `experiments/`
- Proposal checklist: `docs/proposal_traceability.md`

## Reproducibility

All sampling and poisoning scripts accept explicit seeds. Clean source files in
`data/original/` and `data/cleaned/` are treated as immutable downstream inputs.
Agentic chunking is bounded and uses Ollama with deterministic temperature 0.
