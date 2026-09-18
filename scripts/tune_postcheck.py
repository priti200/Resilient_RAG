"""Tune a post-check threshold from clean validation retrieval scores."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.defense.postcheck import CrossEncoderVerifier
from src.index.embedder import TextEmbedder
from src.index.vector_store import FaissVectorStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("index_dir", type=Path)
    parser.add_argument("queries", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--quantile", type=float, default=0.05)
    args = parser.parse_args()
    if not 0 < args.quantile < 1:
        parser.error("quantile must be between 0 and 1")

    embedder = TextEmbedder()
    store = FaissVectorStore.load(args.index_dir / "semantic.faiss")
    metadata = [json.loads(line) for line in (args.index_dir / "semantic_metadata.jsonl").open(encoding="utf-8")]
    verifier = CrossEncoderVerifier(device="cuda")
    scores = []
    with args.queries.open("r", encoding="utf-8") as handle:
        for line in handle:
            query = json.loads(line)
            vector = embedder.encode([query["query"]])
            _, ids = store.search(vector, k=args.top_k)
            contexts = [metadata[int(row)] for row in ids[0] if int(row) >= 0]
            ranked = verifier.rerank(query["query"], contexts)
            if ranked:
                scores.append(ranked[0].score)
    if not scores:
        raise RuntimeError("No validation scores were produced")
    threshold = float(np.quantile(np.asarray(scores), args.quantile))
    config = {
        "threshold": threshold,
        "quantile": args.quantile,
        "validation_queries": len(scores),
        "min_score": min(scores),
        "median_score": float(np.median(scores)),
        "max_score": max(scores),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    print(json.dumps(config, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
