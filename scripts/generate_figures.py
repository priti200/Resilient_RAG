"""Generate dependency-free SVG figures from verified experiment outputs."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _classification(rows: list[dict]) -> tuple[float, float]:
    from src.evaluation.metrics import classification_metrics

    metrics = classification_metrics(rows)
    return float(metrics["accuracy"]), float(metrics["f1"])


def _svg_header(title: str, width: int = 1000, height: int = 600) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/>'
        f'<text x="500" y="35" text-anchor="middle" font-family="Arial" font-size="22" font-weight="bold">'
        f'{html.escape(title)}</text>'
    )


def _bar_chart(path: Path, title: str, labels: list[str], series: dict[str, list[float]], y_max: float = 1.0) -> None:
    width, height = 1000, 600
    left, right, top, bottom = 90, 30, 70, 100
    plot_width = width - left - right
    plot_height = height - top - bottom
    colors = ["#4777a8", "#b35c5c", "#5a8f68"]
    parts = [_svg_header(title, width, height)]
    for tick in range(6):
        value = y_max * tick / 5
        y = top + plot_height * (1 - value / y_max)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#dddddd"/>')
        parts.append(f'<text x="{left-12}" y="{y+5:.1f}" text-anchor="end" font-family="Arial" font-size="12">{value:.2f}</text>')
    group_width = plot_width / max(1, len(labels))
    bar_width = group_width / (len(series) + 1)
    for series_index, (name, values) in enumerate(series.items()):
        for index, value in enumerate(values):
            bar_height = plot_height * min(max(value, 0) / y_max, 1)
            x = left + index * group_width + bar_width * (series_index + 0.5)
            y = top + plot_height - bar_height
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width*.85:.1f}" height="{bar_height:.1f}" fill="{colors[series_index % len(colors)]}"/>')
            parts.append(f'<text x="{x+bar_width*.42:.1f}" y="{y-5:.1f}" text-anchor="middle" font-family="Arial" font-size="11">{value:.2f}</text>')
    for index, label in enumerate(labels):
        x = left + index * group_width + group_width / 2
        parts.append(f'<text x="{x:.1f}" y="{height-55}" text-anchor="middle" font-family="Arial" font-size="13">{html.escape(label).replace(chr(10), "&#10;")}</text>')
    legend_x = width - 210
    for index, name in enumerate(series):
        y = 65 + index * 20
        parts.append(f'<rect x="{legend_x}" y="{y-12}" width="12" height="12" fill="{colors[index % len(colors)]}"/>')
        parts.append(f'<text x="{legend_x+18}" y="{y-2}" font-family="Arial" font-size="12">{html.escape(name)}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _line_chart(path: Path, title: str, labels: list[str], series: dict[str, list[float]]) -> None:
    width, height = 1000, 600
    left, right, top, bottom = 90, 40, 70, 100
    plot_width = width - left - right
    plot_height = height - top - bottom
    colors = ["#777777", "#4777a8", "#c08a45", "#5a8f68"]
    parts = [_svg_header(title, width, height)]
    for tick in range(6):
        value = tick / 5
        y = top + plot_height * (1 - value)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#dddddd"/>')
        parts.append(f'<text x="{left-12}" y="{y+5:.1f}" text-anchor="end" font-family="Arial" font-size="12">{value:.2f}</text>')
    for series_index, (name, values) in enumerate(series.items()):
        points = []
        for index, value in enumerate(values):
            x = left + (plot_width * index / max(1, len(labels) - 1))
            y = top + plot_height * (1 - min(max(value, 0), 1))
            points.append(f"{x:.1f},{y:.1f}")
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{colors[series_index % len(colors)]}"/>')
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{colors[series_index % len(colors)]}" stroke-width="3"/>')
    for index, label in enumerate(labels):
        x = left + (plot_width * index / max(1, len(labels) - 1))
        parts.append(f'<text x="{x:.1f}" y="{height-55}" text-anchor="middle" font-family="Arial" font-size="13">{html.escape(label)}</text>')
    for index, name in enumerate(series):
        x = width - 190
        y = 65 + index * 20
        parts.append(f'<text x="{x}" y="{y}" font-family="Arial" font-size="12" fill="{colors[index % len(colors)]}">{html.escape(name)}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=ROOT_DIR / "experiments")
    parser.add_argument("--output-dir", type=Path, default=ROOT_DIR / "docs" / "figures")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    files = [
        ("Proportional baseline", args.input_dir / "test_clean_baseline.jsonl"),
        ("Proportional resilient", args.input_dir / "test_clean_resilient.jsonl"),
        ("Balanced baseline", args.input_dir / "test_clean_balanced_baseline.jsonl"),
        ("Balanced resilient", args.input_dir / "test_clean_balanced_resilient.jsonl"),
    ]
    labels = [name.replace(" ", "\n") for name, _ in files]
    rows = [_read_rows(path) for _, path in files]
    accuracy = [_classification(value)[0] for value in rows]
    f1 = [_classification(value)[1] for value in rows]
    latency = [sum(sum(row.get("timings_ms", {}).values()) for row in value) / len(value) / 1000 for value in rows]
    refusal = [sum(bool(row.get("refused")) for row in value) / len(value) for value in rows]
    _bar_chart(args.output_dir / "clean_accuracy_f1.svg", "Clean held-out classification performance", labels, {"Accuracy": accuracy, "Macro F1": f1})
    _bar_chart(args.output_dir / "clean_latency.svg", "Clean-query latency (seconds)", labels, {"Mean latency": latency}, y_max=max(1, max(latency) * 1.2))
    _bar_chart(args.output_dir / "clean_false_refusal.svg", "Clean-query false refusals", labels, {"False refusal": refusal}, y_max=max(0.05, max(refusal) * 1.2))

    pattern = re.compile(r"test_attack_(prop|bal)_(0\.1|0\.5|1\.0)_(baseline|resilient)\.jsonl")
    rates = ["0.1", "0.5", "1.0"]
    asr = {}
    refusals = {}
    for path in args.input_dir.glob("test_attack_*.jsonl"):
        match = pattern.fullmatch(path.name)
        if not match:
            continue
        arm, rate, system = match.groups()
        values = _read_rows(path)
        key = f"{arm} {system}"
        asr.setdefault(key, {})[rate] = sum(bool(row.get("attack_succeeded")) for row in values) / len(values)
        refusals.setdefault(key, {})[rate] = sum(bool(row.get("refused")) for row in values) / len(values)
    _line_chart(args.output_dir / "attack_asr.svg", "Attack Success Rate", rates, {key: [values.get(rate, 0) for rate in rates] for key, values in sorted(asr.items())})
    _line_chart(args.output_dir / "attack_refusal.svg", "Attack-query refusal rate", rates, {key: [values.get(rate, 0) for rate in rates] for key, values in sorted(refusals.items())})
    print(json.dumps({"output_dir": str(args.output_dir), "figures": sorted(path.name for path in args.output_dir.glob("*.svg"))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
