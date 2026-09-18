# Resilient-RAG Developer Guide

## 1. Project Overview

Resilient-RAG is a step-by-step defense system that detects and stops data-poisoning
and hidden prompt-injection attacks in AI-based network intrusion detection. It is
implemented as a Python package with a local Ollama LLM, FAISS vector index, and
layered pre-check/post-check defenses.

The project replaces the proposal's CIC-IDS 2017 dataset with the GeNIS dataset
and evaluates two knowledge-base arms: a proportional-distribution KB and a
balanced-per-class KB.

## 2. Architecture

```
src/
  chunking/        # Semantic, fixed-size, and agentic chunking
  index/           # Bi-encoder embedding and FAISS vector store
  attacks/         # Black-box and white-box attack generation
  defense/         # Pre-check filter and post-check verifier
  pipeline/        # Baseline and resilient query engines
  evaluation/      # Metrics, ASR judging, and aggregation
  representation/  # Flow-to-text deterministic template

scripts/           # Standalone pipeline scripts (16 total)
tests/             # Unit and integration tests (9 files, 39 tests)
data/              # Original, cleaned, and processed artifacts
experiments/       # JSONL experiment outputs and summaries
docs/              # Reports, figures, thesis outline, traceability
```

### Data Flow

```
Raw GeNIS CSV → Cleaned CSV → Flow JSONL → Chunks → Embeddings → FAISS index
                                                                ↓
                                                Baseline/Resilient queries → Metrics
```

### Defense Pipeline

```
Ingestion → Schema check → Language check → Index → Retrieve → Cross-encoder → Refuse/Answer
```

## 3. Environment Setup

### Prerequisites

- Windows 10/11 with NVIDIA GPU (RTX 3050 6GB verified)
- Anaconda or Miniconda installed
- Ollama 0.34.1+ installed and running

### Create the Environment

```powershell
# Use the existing Anaconda environment (recommended)
conda activate resilient-rag-anaconda

# Verify everything
python scripts/setup_check.py
python -m pip check
python -m pytest tests -q
```

### Key Dependencies

| Package | Version | Purpose |
|---|---|---|
| torch | 2.6.0+cu124 | CUDA embedding and generation |
| sentence-transformers | 6.0.1 | Bi-encoder and cross-encoder |
| faiss-cpu | 1.15.0 | Vector index |
| transformers | 5.17.0 | Perplexity scoring (optional) |
| ollama | 0.6.2 | Local LLM client |
| pytest | 9.1.1 | Testing |

### Ollama Model

```powershell
ollama pull qwen2.5:7b
```

## 4. Data Pipeline

### 4.1 Raw Data

Original GeNIS files are in `data/original/` and are never modified.

### 4.2 Cleaned Data

Preprocessing produced cleaned, split datasets in `data/cleaned/`:

```
data/cleaned/train.csv          # 3,660,514 rows, 78 columns
data/cleaned/validation.csv     #   784,396 rows
data/cleaned/test.csv           #   784,396 rows
data/cleaned/train_balanced.csv #   218,532 rows (undersampled)
```

### 4.3 Flow-to-Text

Deterministic template converts each CSV row to natural language:

```powershell
python scripts/generate_flow_text.py
```

Output: `data/processed/text/{train,validation,test}_text.jsonl`

### 4.4 Knowledge Base Sampling

Two KB arms are available:

```powershell
# Proportional (realistic distribution, 94% dos)
python scripts/build_kb_sample.py data/processed/text/train_text.jsonl data/processed/kb/clean_sample_100k.jsonl --sample-size 100000 --seed 42 --strategy proportional

# Balanced (25,000 per class)
python scripts/build_kb_sample.py data/processed/text/train_text.jsonl data/processed/kb/clean_sample_100k_balanced.jsonl --sample-size 100000 --seed 42 --strategy balanced
```

### 4.5 Chunking

Three methods are implemented:

```python
from src.chunking.semantic import chunk_records as semantic_chunks
from src.chunking.fixed_size import chunk_records as fixed_chunks
from src.chunking.agentic import chunk_records as agentic_chunks
from src.chunking.agentic import OllamaBoundaryAgent

# Semantic: one flow = one chunk (recommended primary)
chunks = list(semantic_chunks(records, split_name="train"))

# Fixed-size: 2048-char windows with provenance tracking
chunks = list(fixed_chunks(records, split_name="train", max_chars=2048))

# Agentic: Ollama decides adjacency (bounded, fail-closed)
agent = OllamaBoundaryAgent(model="qwen2.5:7b")
chunks = list(agentic_chunks(records, boundary_decider=agent, max_records=8, max_chars=4096))
```

### 4.6 Embedding and Indexing

```powershell
# Build semantic index for clean KB
python scripts/build_index.py data/processed/kb/clean_sample_100k.jsonl data/processed/index --method semantic --model sentence-transformers/all-MiniLM-L6-v2 --batch-size 64

# Build index from pre-chunked data
python scripts/build_index.py data/processed/chunks/agentic/train_sample.jsonl data/processed/index --method agentic --input-is-chunks
```

Output per index:
- `semantic.faiss` (FAISS vector store)
- `semantic_metadata.jsonl` (chunk metadata with labels)
- `semantic_summary.json` (build stats)

## 5. Attack Generation

### 5.1 Build Attack Catalog

```powershell
python scripts/build_attack_catalog.py data/processed/kb/clean_sample_100k.jsonl data/processed/attacks/attack_catalog.jsonl --targets 20 --variants 4
```

Catalog contains 480 attacks:
- 3 goals: alert_suppression, misclassification, analyst_misdirection
- 2 types: black_box, white_box
- 4 variants per goal × 20 target records = 480

### 5.2 Create Poisoned KB Copies

```powershell
python scripts/poison_kb.py data/processed/kb/clean_sample_100k.jsonl data/processed/attacks/attack_catalog.jsonl data/processed/kb/poisoned_0.1pct.jsonl --rate 0.001 --seed 42
python scripts/poison_kb.py data/processed/kb/clean_sample_100k.jsonl data/processed/attacks/attack_catalog.jsonl data/processed/kb/poisoned_0.5pct.jsonl --rate 0.005 --seed 43
python scripts/poison_kb.py data/processed/kb/clean_sample_100k.jsonl data/processed/attacks/attack_catalog.jsonl data/processed/kb/poisoned_1pct.jsonl --rate 0.01 --seed 44
```

Rebuild FAISS indexes for each poisoned copy using `scripts/build_index.py`.

### 5.3 Stratified Attack Subset

For bounded experiments, select 30 attacks (5 per goal × type):

```powershell
python scripts/build_attack_subset.py data/processed/attacks/attack_catalog.jsonl data/processed/attacks/attack_subset_30.jsonl --per-goal-type 5 --seed 42
```

## 6. Defense Layers

### 6.1 Pre-Check Filter

Located in `src/defense/precheck.py`:

```python
from src.defense.precheck import check_text

result = check_text(chunk_text)
if not result.accepted:
    print("Rejected:", result.reasons)
```

Checks performed:
- Schema validation (protocol, flags, states, ports)
- Instruction-pattern detection (regex hits)
- Language score (pattern count threshold)
- Perplexity scoring (optional, requires GPT-2 download)

### 6.2 Post-Check Verifier

Located in `src/defense/postcheck.py`:

```python
from src.defense.postcheck import CrossEncoderVerifier, verify_retrieval

verifier = CrossEncoderVerifier(device="cuda")
result = verify_retrieval(query, retrieved_chunks, verifier=verifier, threshold=-5.06)
if not result.accepted:
    print("Refusal reason:", result.reason)
```

Checks performed:
- Cross-encoder re-ranking of retrieved chunks
- Threshold-based refusal (tuned to 5th percentile of clean scores)
- Flagged-chunk exclusion

## 7. Query Pipeline

### 7.1 Baseline (Undefended)

```python
from src.pipeline.query_engine import QueryEngine

engine = QueryEngine(Path("data/processed/index"))
result = engine.query("Classify this network flow", top_k=5, resilient=False)
print(result.answer)
```

### 7.2 Resilient (Defended)

```python
from src.pipeline.query_engine import QueryEngine
from src.defense.postcheck import CrossEncoderVerifier

engine = QueryEngine(
    Path("data/processed/index"),
    verifier=CrossEncoderVerifier(device="cuda"),
    postcheck_threshold=-5.06,
)
result = engine.query("Classify this network flow", top_k=5, resilient=True)
if result.refused:
    print("Refused:", result.refusal_reason)
else:
    print(result.answer)
```

### 7.3 Structured Output

Both systems use Ollama JSON format with schema:

```json
{
  "category": "benign|bruteforce|dos|recon",
  "alert_required": true,
  "justification": "..."
}
```

## 8. Evaluation

### 8.1 Build Query Sets

```powershell
# From validation data
python scripts/build_query_set.py data/processed/text/validation_text.jsonl data/processed/queries/validation_queries.jsonl --per-class 25 --seed 42

# From held-out test data
python scripts/build_query_set.py data/processed/text/test_text.jsonl data/processed/queries/test_queries.jsonl --per-class 25 --seed 84
```

### 8.2 Run Experiments

```powershell
$env:HF_HUB_OFFLINE='1'

# Clean baseline
python scripts/run_experiments.py data/processed/index data/processed/queries/test_queries.jsonl experiments/test_baseline.jsonl --system baseline --limit 100 --top-k 5

# Clean resilient
python scripts/run_experiments.py data/processed/index data/processed/queries/test_queries.jsonl experiments/test_resilient.jsonl --system resilient --limit 100 --top-k 5

# Poisoned attack run
python scripts/run_experiments.py data/processed/index/poisoned_0.1pct data/processed/queries/test_queries.jsonl experiments/test_attack.jsonl --system baseline --attacks data/processed/attacks/attack_subset_30.jsonl --attack-limit 30 --top-k 5
```

Each run writes one JSONL row per query with: query_id, answer, refused, retrieved_ids, timings_ms, and (for attacks) attack_succeeded, judge_method.

### 8.3 Analyze Results

```powershell
python scripts/analyze_results.py experiments/test_baseline.jsonl experiments/test_resilient.jsonl experiments/summary.json
```

### 8.4 Statistical Analysis

```powershell
python scripts/statistical_analysis.py experiments/test_baseline.jsonl experiments/test_resilient.jsonl experiments/stats.json
```

Outputs: paired accuracy difference, Wilcoxon p-value, t-test p-value, latency comparison.

### 8.5 Generate Figures

```powershell
python scripts/generate_figures.py
```

Produces SVG figures in `docs/figures/`:
- `clean_accuracy_f1.svg`
- `clean_latency.svg`
- `clean_false_refusal.svg`
- `attack_asr.svg`
- `attack_refusal.svg`

## 9. Experiment Matrix (Completed)

| KB Arm | System | Poison Rate | Attacks | Result File |
|---|---|---|---|---|
| Proportional | Baseline | Clean | 100 queries | `test_clean_baseline.jsonl` |
| Proportional | Resilient | Clean | 100 queries | `test_clean_resilient.jsonl` |
| Balanced | Baseline | Clean | 100 queries | `test_clean_balanced_baseline.jsonl` |
| Balanced | Resilient | Clean | 100 queries | `test_clean_balanced_resilient.jsonl` |
| Proportional | Baseline | 0.1% | 30 attacks | `test_attack_prop_0.1_baseline.jsonl` |
| Proportional | Resilient | 0.1% | 30 attacks | `test_attack_prop_0.1_resilient.jsonl` |
| Proportional | Baseline | 0.5% | 30 attacks | `test_attack_prop_0.5_baseline.jsonl` |
| Proportional | Resilient | 0.5% | 30 attacks | `test_attack_prop_0.5_resilient.jsonl` |
| Proportional | Baseline | 1.0% | 30 attacks | `test_attack_prop_1.0_baseline.jsonl` |
| Proportional | Resilient | 1.0% | 30 attacks | `test_attack_prop_1.0_resilient.jsonl` |
| Balanced | Baseline | 0.1% | 30 attacks | `test_attack_bal_0.1_baseline.jsonl` |
| Balanced | Resilient | 0.1% | 30 attacks | `test_attack_bal_0.1_resilient.jsonl` |
| Balanced | Baseline | 0.5% | 30 attacks | `test_attack_bal_0.5_baseline.jsonl` |
| Balanced | Resilient | 0.5% | 30 attacks | `test_attack_bal_0.5_resilient.jsonl` |
| Balanced | Baseline | 1.0% | 30 attacks | `test_attack_bal_1.0_baseline.jsonl` |
| Balanced | Resilient | 1.0% | 30 attacks | `test_attack_bal_1.0_resilient.jsonl` |

## 10. Adding New Components

### New Chunking Method

1. Create `src/chunking/new_method.py` with `chunk_records(records, split_name="data", **kwargs) -> Iterator[Chunk]`
2. Add tests in `tests/test_chunking.py`
3. Export from `src/chunking/__init__.py`

### New Defense Layer

1. Create module in `src/defense/`
2. Follow the `CheckResult` or `PostcheckResult` dataclass pattern
3. Integrate into `src/pipeline/query_engine.py`
4. Tune thresholds with a new tuning script in `scripts/`

### New Attack Goal

1. Add to `ATTACK_GOALS` and `PAYLOADS` in `src/attacks/templates.py`
2. Update `rule_attack_success` in `src/evaluation/metrics.py`
3. Rebuild catalog with `scripts/build_attack_catalog.py`

## 11. Known Issues and Workarounds

### Windows Application Control Blocking DLLs

Matplotlib's native `_image` DLL and some PyTorch DLLs are blocked on this machine. The figure generator uses dependency-free SVG instead. All core functionality works.

### Ollama CUDA Server Crash

Occasionally the `llama-server` process crashes with CUDA shared-object errors. Workaround:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" stop qwen2.5:7b
# Then rerun the experiment; Ollama will reload the model automatically
```

### HF Hub Rate Limits

Set `HF_HUB_OFFLINE=1` before running experiments to use cached models and avoid rate-limit warnings:

```powershell
$env:HF_HUB_OFFLINE='1'
```

### Bruteforce Classification

Bruteforce accuracy remains low (16-20%) because retrieved reference examples rarely include bruteforce flows (only 1.5% of the proportional KB). This is a data-characteristic finding, not a code defect.

## 12. Testing

```powershell
# Run all tests
python -m pytest tests -q

# Run specific test file
python -m pytest tests/test_chunking.py -v

# With coverage
python -m pytest tests --cov=src --cov-report=term
```

Current: **39 tests passing**, covering chunking, KB sampling, index, attacks, defenses, pipeline, evaluation, and statistics.

## 13. File Inventory

```
4-preprocessed/
├── configs/
│   ├── baseline.yaml
│   ├── chunking.yaml
│   ├── postcheck.yaml
│   ├── postcheck_balanced.yaml
│   ├── precheck.yaml
│   └── resilient.yaml
├── src/
│   ├── chunking/ (semantic, fixed_size, agentic, model, common)
│   ├── index/ (embedder, vector_store)
│   ├── attacks/ (templates, black_box, white_box)
│   ├── defense/ (precheck, postcheck)
│   ├── pipeline/ (prompts, query_engine, baseline)
│   ├── evaluation/ (metrics, judge)
│   └── representation/ (flow_to_text)
├── scripts/ (16 pipeline scripts)
├── tests/ (9 test modules)
├── data/ (original, cleaned, processed)
├── experiments/ (26 result files)
├── docs/
│   ├── evaluation_report.md
│   ├── proposal_traceability.md
│   ├── thesis_outline.md
│   ├── attack_model.md
│   ├── chunking.md
│   ├── flow_text_representation.md
│   ├── flow_text_schema.md
│   └── figures/ (5 SVG charts)
├── requirements.txt
└── README.md
```

## 14. Quick-Start Reproduction

To reproduce the full project from scratch on a new machine:

```powershell
# 1. Set up environment
conda activate resilient-rag-anaconda
ollama pull qwen2.5:7b

# 2. Verify
python scripts/setup_check.py
python -m pytest tests -q

# 3. Build KBs (if starting from cleaned CSV)
python scripts/generate_flow_text.py          # CSV → JSONL
python scripts/build_kb_sample.py ...         # JSONL → 100K sample
python scripts/build_index.py ...             # Sample → FAISS index

# 4. Build attacks
python scripts/build_attack_catalog.py ...

# 5. Build poisoned copies
python scripts/poison_kb.py ...

# 6. Run experiments
$env:HF_HUB_OFFLINE='1'
python scripts/run_experiments.py ...

# 7. Analyze and generate figures
python scripts/analyze_results.py ...
python scripts/statistical_analysis.py ...
python scripts/generate_figures.py
```
