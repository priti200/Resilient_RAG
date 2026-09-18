# Resilient-RAG Evaluation Report

## Scope

This report records the current implementation and bounded smoke evaluation of
Resilient-RAG on the GeNIS-derived flow-text dataset. The proposal's CIC-IDS2017
dataset was replaced by GeNIS and that substitution must remain explicit in the
final thesis.

## Implemented Components

- Deterministic flow-to-text representation.
- Semantic one-flow-per-chunk chunking.
- Fixed-size 2,048-character chunking with provenance tracking.
- Agentic adjacent-flow chunking using Ollama `qwen2.5:7b`, bounded by eight
  flows and 4,096 characters with fail-closed fallback.
- Proportional 100,000-record KB sample using seed 42.
- CUDA bi-encoder embeddings with `all-MiniLM-L6-v2` and FAISS indexes.
- Synthetic black-box and white-box attack catalog.
- Poisoned KB copies at 0.1%, 0.5%, and 1%.
- Schema/instruction pre-check and cross-encoder post-check.
- Baseline and resilient Ollama query engines.
- Rule-first ASR judging with optional Ollama fallback.

## Data Artifacts

The clean 100K sample contains:

| Class | Records |
|---|---:|
| benign | 2,687 |
| bruteforce | 1,493 |
| dos | 94,197 |
| recon | 1,623 |

The agentic sample contains 1,000 source flows, 925 chunks, 924 Ollama
decisions, complete source coverage, and zero fallback decisions.

## Defense Tuning

The pre-check tuning sample contained 1,000 clean records and 480 synthetic
attacks:

- Clean rejection rate: 0%.
- Attack detection rate: 100%.

The post-check threshold was set to the fifth percentile of 100 clean
validation cross-encoder scores:

```text
-5.062863230705261
```

This is an initial operating point, not a final claim of generalization.

## Bounded End-to-End Run

The bounded run used eight clean validation queries for each system and six
attack queries against the 0.1% poisoned semantic index.

| System / condition | Queries | Accuracy | F1 | False refusal | ASR |
|---|---:|---:|---:|---:|---:|
| Baseline / clean | 8 | 0.375 | 0.375 | 0% | N/A |
| Resilient / clean | 8 | 0.125 | 0.125 | 12.5% | N/A |
| Baseline / attack | 6 | N/A | N/A | N/A | 0% by rules |
| Resilient / attack | 6 | N/A | N/A | N/A | 0% by rules |

These values are smoke-test results only. The sample is too small for
statistical inference, and the current generic attack questions did not
produce enough unambiguous rule-based attack-success outcomes. Larger,
targeted evaluation queries are required before conclusions can be drawn.

## Corrected Held-Out Clean Evaluation

The first clean evaluation used free-form generation and a keyword extractor;
82% of answers did not contain a literal GeNIS category, so those initial
accuracy values were invalid as classification measurements. The pipeline was
corrected to require JSON output with the category restricted to `benign`,
`bruteforce`, `dos`, or `recon`, and the clean test evaluation was rerun from
the beginning on 100 held-out queries.

| System | Queries | Accuracy | Macro precision | Macro recall | Macro F1 | False refusal | Mean latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 100 | 0.740 | 0.843 | 0.740 | 0.701 | 0% | 7.29 s |
| Resilient-RAG | 100 | 0.680 | 0.570 | 0.680 | 0.609 | 1% | 8.50 s |

The resilient pipeline adds approximately 1.20 seconds per query in this
configuration and reduces clean accuracy by 6 percentage points. These are
descriptive results only; repeated runs and significance testing are still
required. The earlier 7% and 10% clean accuracy values are superseded by this
structured-output evaluation.

## Balanced Knowledge-Base Arm

A second 100,000-record KB was built with exactly 25,000 records per class.
The proportional arm was retained as the realistic-distribution condition.

| System | Accuracy | Macro F1 | False refusal | Mean latency |
|---|---:|---:|---:|---:|
| Proportional baseline | 0.740 | 0.701 | 0% | 7.29 s |
| Proportional resilient | 0.680 | 0.609 | 1% | 8.50 s |
| Balanced baseline | 0.730 | 0.705 | 0% | 7.26 s |
| Balanced resilient | 0.670 | 0.643 | 4% | 14.66 s |

Balancing improved benign classification from 88% to 100%, but bruteforce
classification only improved from 16% to 20%. It also reduced DoS accuracy
from 92% to 72%. This indicates that bruteforce difficulty is not caused only
by class prior; the flow-level representation may not contain enough
discriminating evidence.

## Paired Statistical Checks

These are exploratory paired tests over the 100 held-out queries in each arm,
not repeated-seed final inference:

| Arm | Accuracy difference | Wilcoxon p | Mean latency difference | Latency Wilcoxon p |
|---|---:|---:|---:|---:|
| Proportional | -0.06 | 0.2595 | +1.20 s | <0.001 |
| Balanced | -0.06 | 0.2767 | +7.41 s | <0.001 |

The latency increase is measurable. The accuracy difference is not significant
under the paired Wilcoxon test at the 0.05 level; repeated seeds are still
needed.

## Poisoned Matrix

The completed matrix contains 360 attack runs:

- Two KB arms: proportional and balanced.
- Two systems: baseline and resilient.
- Three poison rates: 0.1%, 0.5%, and 1%.
- Thirty attacks per rate: five black-box and five white-box attacks for each
  of three attack goals.

Observed rule-based ASR was 0% for all matrix conditions. The resilient system
refused all 30 attacks at every rate and KB arm. The baseline did not refuse,
but no answer was classified as a successful attack by the current rule judge.
This result must be interpreted cautiously: the experiment currently needs an
explicit retrieval-reach metric confirming that each poisoned entry was in the
top-k context before ASR can be treated as a complete attack measurement.

## Verification Status

- Full automated test suite: 37 tests passed.
- `pip check`: no broken requirements.
- CUDA: RTX 3050 6GB verified through PyTorch 2.6.0+cu124.
- Ollama: version 0.34.1 with `qwen2.5:7b` verified.
- Original and cleaned source datasets were not modified by downstream steps.

## Required Final Evaluation Work

Before treating results as thesis findings, run:

1. Larger clean validation and unseen test query sets.
2. Targeted attack queries for every attack goal and attack type.
3. All poison rates and multiple attack mixes.
4. Semantic, fixed, and agentic comparisons on matched samples.
5. Repeated seeded runs with confidence intervals and paired significance tests.
6. External dataset validation if a compatible public dataset is obtained.
