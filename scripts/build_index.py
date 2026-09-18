"""Build a FAISS index from flow records or precomputed chunks."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.chunking.fixed_size import chunk_records as fixed_chunks
from src.chunking.semantic import chunk_records as semantic_chunks
from src.index.embedder import TextEmbedder
from src.index.vector_store import FaissVectorStore


def _records(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"Line {line_number} is not a JSON object")
            yield record


def _chunks(path: Path, method: str, max_chars: int, input_is_chunks: bool):
    records = _records(path)
    if input_is_chunks:
        from src.chunking.model import Chunk

        for record in records:
            yield Chunk(
                chunk_id=str(record["chunk_id"]),
                text=str(record["text"]),
                method=str(record.get("method", method)),
                source_flow_ids=tuple(str(value) for value in record["source_flow_ids"]),
                source_labels=tuple(str(value) for value in record.get("source_labels", [])),
                metadata=record.get("metadata", {}),
            )
    elif method == "semantic":
        yield from semantic_chunks(records, split_name="kb")
    elif method == "fixed":
        yield from fixed_chunks(records, split_name="kb", max_chars=max_chars)
    else:
        raise ValueError("method must be semantic or fixed when input_is_chunks is false")


def build_index(
    input_path: Path,
    output_dir: Path,
    *,
    method: str,
    model_name: str,
    batch_size: int,
    max_chars: int,
    input_is_chunks: bool,
) -> dict[str, Any]:
    embedder = TextEmbedder(model_name)
    store = FaissVectorStore(embedder.dimension)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / f"{method}_metadata.jsonl"
    texts: list[str] = []
    pending: list[Any] = []
    chunks_written = 0

    def flush(handle) -> None:
        nonlocal chunks_written
        if not pending:
            return
        vectors = embedder.encode(texts, batch_size=batch_size)
        store.add(vectors)
        for chunk in pending:
            handle.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
            chunks_written += 1
        pending.clear()
        texts.clear()

    with metadata_path.open("w", encoding="utf-8") as metadata_handle:
        for chunk in _chunks(input_path, method, max_chars, input_is_chunks):
            pending.append(chunk)
            texts.append(chunk.text)
            if len(pending) >= batch_size:
                flush(metadata_handle)
        flush(metadata_handle)

    if chunks_written == 0:
        raise ValueError("No chunks were produced")
    index_path = output_dir / f"{method}.faiss"
    store.save(index_path)
    summary = {
        "input": str(input_path),
        "index": str(index_path),
        "metadata": str(metadata_path),
        "method": method,
        "model": model_name,
        "chunks": chunks_written,
        "dimension": store.dimension,
        "device": embedder.device,
    }
    (output_dir / f"{method}_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--method", choices=["semantic", "fixed", "agentic"], default="semantic")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-chars", type=int, default=2048)
    parser.add_argument("--input-is-chunks", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    summary = build_index(
        args.input,
        args.output_dir,
        method=args.method,
        model_name=args.model,
        batch_size=args.batch_size,
        max_chars=args.max_chars,
        input_is_chunks=args.input_is_chunks,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
