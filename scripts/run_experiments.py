"""Run baseline or resilient RAG experiments and persist per-query results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.defense.postcheck import CrossEncoderVerifier
from src.evaluation.judge import AttackJudge
from src.pipeline.query_engine import QueryEngine


def _read(path: Path, limit: int | None = None):
    with path.open("r", encoding="utf-8") as handle:
        for position, line in enumerate(handle):
            if limit is not None and position >= limit:
                break
            yield json.loads(line)


def _attack_queries(path: Path, limit: int | None):
    for record in _read(path, limit):
        yield {
            "query_id": record["attack_id"],
            "kind": "attack",
            "attack_id": record["attack_id"],
            "goal": record["goal"],
            "query": record["target_query"],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("index_dir", type=Path)
    parser.add_argument("queries", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--system", choices=["baseline", "resilient"], required=True)
    parser.add_argument("--attacks", type=Path)
    parser.add_argument("--limit", type=int, help="clean-query limit")
    parser.add_argument("--attack-limit", type=int, help="attack-query limit")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--postcheck-threshold", type=float, default=-5.062863230705261)
    args = parser.parse_args()

    query_rows = list(_read(args.queries, args.limit))
    if args.attacks:
        query_rows.extend(_attack_queries(args.attacks, args.attack_limit))
    verifier = CrossEncoderVerifier(device="cuda") if args.system == "resilient" else None
    engine = QueryEngine(
        args.index_dir,
        verifier=verifier,
        postcheck_threshold=args.postcheck_threshold,
    )
    judge = AttackJudge()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in query_rows:
            result = engine.query(
                row["query"],
                top_k=args.top_k,
                resilient=args.system == "resilient",
            )
            output = {
                **row,
                "system": args.system,
                "answer": result.answer,
                "refused": result.refused,
                "refusal_reason": result.refusal_reason,
                "retrieved_ids": [item.get("chunk_id") for item in result.retrieved],
                "timings_ms": result.timings_ms,
            }
            if row.get("kind") == "attack":
                success, judge_method = judge.judge(row["goal"], result.answer)
                output["attack_succeeded"] = success
                output["judge_method"] = judge_method
            handle.write(json.dumps(output, ensure_ascii=False) + "\n")
            handle.flush()
            print(row["query_id"], "refused=" + str(result.refused), file=sys.stderr)
    print(json.dumps({"output": str(args.output), "rows": len(query_rows), "system": args.system}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
