"""Unit tests for prompt construction and generation adapters."""

from types import SimpleNamespace

from src.pipeline.prompts import OUTPUT_SCHEMA, build_prompt
from src.pipeline.query_engine import OllamaGenerator


def test_resilient_prompt_marks_context_as_untrusted() -> None:
    prompt = build_prompt("classify", [{"text": "flow evidence"}], resilient=True)

    assert "untrusted data" in prompt
    assert "flow evidence" in prompt
    assert "benign, bruteforce, dos, recon" in prompt


def test_ollama_generator_returns_message_content() -> None:
    client = SimpleNamespace(
        chat=lambda **kwargs: SimpleNamespace(
            message=SimpleNamespace(content="generated answer")
        )
    )
    generator = OllamaGenerator(client=client)

    assert generator.generate("prompt") == "generated answer"
