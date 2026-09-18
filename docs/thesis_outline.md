# Resilient-RAG Thesis and Paper Outline

## 1. Introduction

- Motivation: LLM-assisted network intrusion detection and RAG trust risks.
- Problem statement: poisoned knowledge and indirect prompt injection.
- Research question and hypothesis from the approved proposal.
- Contributions: network-specific benchmark, layered defense, chunking comparison,
  and safety/latency evaluation.

## 2. Background and Related Work

- RAG and dense retrieval.
- Network intrusion detection and GeNIS.
- Knowledge poisoning and indirect prompt injection.
- Schema validation, perplexity/anomaly detection, and refusal policies.
- Bi-encoder retrieval and cross-encoder re-ranking.

## 3. Threat Model

- Attacker goals and capabilities.
- Black-box and white-box assumptions.
- Poison placement and experimental safety boundaries.
- Reference: `docs/attack_model.md`.

## 4. Dataset and Representation

- GeNIS source splits and preprocessing.
- Label distribution and class imbalance.
- Deterministic flow-to-text schema.
- Proportional and balanced KB construction.

## 5. Resilient-RAG Design

- Semantic, fixed-size, and agentic chunking.
- Bi-encoder and FAISS retrieval.
- Schema/language pre-check.
- Cross-encoder post-check.
- Refuse-to-answer policy.
- Baseline system for controlled comparison.

## 6. Attack Benchmark

- Three attack goals.
- Black-box and white-box generation.
- Poisoning rates and attack mixes.
- Catalog format and reproducibility.

## 7. Experimental Method

- Clean and poisoned conditions.
- Proportional versus balanced KB arms.
- Held-out test queries.
- Metrics: ASR, precision, recall, F1, false refusal, false clearance, latency.
- Statistical tests and limitations.

## 8. Results

- Clean classification and latency tables.
- Per-class confusion analysis, especially bruteforce.
- ASR and refusal plots.
- Chunking comparison.
- Statistical significance results.

## 9. Discussion

- Security benefit and operational cost.
- Effect of KB class prior.
- Why bruteforce remains difficult.
- Generalization limits and external validity.

## 10. Conclusion and Future Work

- Answer to the research question.
- Practical deployment recommendations.
- External datasets, larger agentic studies, and SIEM integration.
