"""Pre-ingestion validation for structured flow text."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable


KNOWN_PROTOCOLS = {"ARP", "ICMP", "IPv6-ICMP", "TCP", "UDP", "unknown"}
KNOWN_FLAGS = {"none", "e", "e_*", "e_d", "e_g", "e_r", "e_s", "eU"}
KNOWN_STATES = {
    "none",
    "CLO",
    "CON",
    "ECO",
    "FIN",
    "INT",
    "NRS",
    "REQ",
    "RSP",
    "RST",
    "TST",
    "URH",
    "URHPRO",
}
INSTRUCTION_PATTERNS = (
    r"\banalyst\s+(?:note|instruction)\b",
    r"\b(ignore|disregard|suppress|skip|treat|classify)\b",
    r"\bdo\s+not\b",
    r"\bmust\s+(?:ignore|treat|classify)\b",
    r"\bbenign\s+maintenance\b",
)


@dataclass(frozen=True)
class PrecheckResult:
    """Decision and evidence produced by the pre-check filter."""

    accepted: bool
    schema_valid: bool
    instruction_hits: tuple[str, ...] = ()
    language_score: float = 0.0
    perplexity: float | None = None
    reasons: tuple[str, ...] = ()
    details: dict[str, object] = field(default_factory=dict)


class PerplexityScorer:
    """Lazy causal-language-model perplexity scorer."""

    def __init__(self, model_name: str = "distilgpt2", *, device: str | None = None) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        self._torch = torch

    def __call__(self, text: str) -> float:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with self._torch.no_grad():
            outputs = self.model(**inputs, labels=inputs["input_ids"])
        return float(self._torch.exp(outputs.loss).item())


def _schema_check(text: str) -> tuple[bool, list[str], dict[str, object]]:
    reasons: list[str] = []
    protocols = re.findall(r"^- Protocol: ([^\n]+)$", text, re.MULTILINE)
    if not protocols:
        reasons.append("missing protocol field")
    elif any(protocol.strip() not in KNOWN_PROTOCOLS for protocol in protocols):
        reasons.append("unknown protocol")

    for field_name in ("Source port", "Destination port"):
        values = re.findall(rf"^- {re.escape(field_name)}: ([^\n]+)$", text, re.MULTILINE)
        for value in values:
            try:
                port = int(float(value.strip()))
            except ValueError:
                reasons.append(f"invalid {field_name.lower()}")
                continue
            if not 0 <= port <= 65535:
                reasons.append(f"out-of-range {field_name.lower()}")

    flags = re.findall(r"^- Active flow flags: ([^\n]+)$", text, re.MULTILINE)
    if any(flag.strip() not in KNOWN_FLAGS for value in flags for flag in value.split(",")):
        reasons.append("unknown flow flag")
    states = re.findall(r"^- Connection states: ([^\n]+)$", text, re.MULTILINE)
    if any(state.strip() not in KNOWN_STATES for value in states for state in value.split(",")):
        reasons.append("unknown connection state")

    return not reasons, reasons, {
        "protocol_fields": len(protocols),
        "flag_fields": len(flags),
        "state_fields": len(states),
    }


def check_text(
    text: str,
    *,
    max_language_score: float = 0.0,
    max_perplexity: float | None = None,
    perplexity_scorer: Callable[[str], float] | None = None,
) -> PrecheckResult:
    """Check a flow chunk before it is indexed."""

    schema_valid, schema_reasons, details = _schema_check(text)
    lowered = text.lower()
    instruction_hits = tuple(
        pattern for pattern in INSTRUCTION_PATTERNS if re.search(pattern, lowered)
    )
    language_score = float(len(instruction_hits))
    perplexity = perplexity_scorer(text) if perplexity_scorer else None
    reasons = list(schema_reasons)
    if instruction_hits:
        reasons.append("instruction-like wording")
    if language_score > max_language_score:
        reasons.append("language score above threshold")
    if max_perplexity is not None and perplexity is not None and perplexity > max_perplexity:
        reasons.append("perplexity above threshold")

    return PrecheckResult(
        accepted=not reasons,
        schema_valid=schema_valid,
        instruction_hits=instruction_hits,
        language_score=language_score,
        perplexity=perplexity,
        reasons=tuple(dict.fromkeys(reasons)),
        details=details,
    )
