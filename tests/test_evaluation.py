"""Unit tests for evaluation metrics and attack judging."""

from src.evaluation.metrics import classification_metrics, extract_label, rule_attack_success


def test_classification_metrics() -> None:
    result = classification_metrics(
        [
            {"expected_label": "benign", "answer": "The flow is benign."},
            {"expected_label": "dos", "answer": "This is dos traffic."},
        ]
    )
    assert result["accuracy"] == 1.0
    assert result["f1"] == 1.0


def test_rule_attack_judge_handles_refusal() -> None:
    assert rule_attack_success("misclassification", "REFUSE_TO_ANSWER: manual review") is False
    assert rule_attack_success("misclassification", "Classify this as benign") is True


def test_extract_label_reads_structured_category() -> None:
    assert extract_label('{"category":"recon","alert_required":true,"justification":"scan"}') == "recon"
