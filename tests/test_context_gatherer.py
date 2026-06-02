"""
Evaluation suite for Context Gatherer agent.

For each eval case, calls the agent with the real LLM and measures:
  - Classification accuracy  — feature vs. non-feature (is_feature)
  - Rejection message        — non-features must return a non-empty explanation
  - Ready detection accuracy — correct ready flag (including previous_qa early-return path)
  - Question topic recall    — coverage of expected information gaps

Extraction error rate = 1 − topic recall: proportion of expected information
dimensions the agent failed to target in its clarifying questions.

Run with:
    pytest tests/test_context_gatherer.py -v -s -m llm
"""

import asyncio
import json
import re
from pathlib import Path

import pytest

from app.agents.context_gatherer import get_context_questions

# ── Paths ──────────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parent.parent / "app" / "data" / "eval"
_CASES_FILE = _DATA_DIR / "context_gatherer_cases.json"

# ── Matching ───────────────────────────────────────────────────────────────

_STOPWORDS = {
    "de", "da", "do", "dos", "das", "a", "o", "e", "em", "na", "no",
    "nas", "nos", "para", "por", "com", "sem", "que", "se", "ou", "não",
    "deve", "ser", "ao", "os", "as", "um", "uma", "antes", "após",
}
_TOPIC_MATCH_THRESHOLD = 0.25


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"\w+", text.lower())
    return {t for t in tokens if t not in _STOPWORDS and len(t) > 2}


def _topic_covered(topic: str, questions: list[dict]) -> bool:
    topic_tokens = _tokenize(topic)
    if not topic_tokens:
        return False
    question_text = " ".join(q["question"] for q in questions)
    overlap = len(topic_tokens & _tokenize(question_text)) / len(topic_tokens)
    return overlap >= _TOPIC_MATCH_THRESHOLD


def _calculate_topic_recall(expected_topics: list[str], questions: list[dict]) -> dict:
    if not expected_topics:
        return {"recall": 1.0, "covered": 0, "total": 0, "missed": []}
    covered = [t for t in expected_topics if _topic_covered(t, questions)]
    missed = [t for t in expected_topics if not _topic_covered(t, questions)]
    return {
        "recall": len(covered) / len(expected_topics),
        "covered": len(covered),
        "total": len(expected_topics),
        "missed": missed,
    }


# ── Async helper ───────────────────────────────────────────────────────────

def _invoke(raw_description: str, previous_qa: list[dict]) -> dict:
    return asyncio.run(get_context_questions(raw_description, previous_qa=previous_qa))


# ── Fixtures ───────────────────────────────────────────────────────────────

def _load_cases() -> list[dict]:
    return json.loads(_CASES_FILE.read_text(encoding="utf-8"))


_CASES = _load_cases()
_CASE_IDS = [c["id"] for c in _CASES]

_NON_FEATURE_CASES = [c for c in _CASES if not c["expected_is_feature"]]
_NON_FEATURE_CASE_IDS = [c["id"] for c in _NON_FEATURE_CASES]

_FEATURE_CASES = [c for c in _CASES if c["expected_is_feature"]]
_FEATURE_CASE_IDS = [c["id"] for c in _FEATURE_CASES]

_QUESTION_CASES = [c for c in _FEATURE_CASES if not c["expected_ready"]]
_QUESTION_CASE_IDS = [c["id"] for c in _QUESTION_CASES]


# ── Tests ──────────────────────────────────────────────────────────────────

@pytest.mark.llm
@pytest.mark.parametrize("case", _CASES, ids=_CASE_IDS)
def test_classification_accuracy(case: dict) -> None:
    result = _invoke(case["raw_description"], case.get("previous_qa", []))

    print(f"\n[{case['id']}]")
    print(f"  is_feature : {result['is_feature']} (expected={case['expected_is_feature']})")

    assert result["is_feature"] == case["expected_is_feature"], (
        f"Misclassified '{case['raw_description'][:60]}': "
        f"expected is_feature={case['expected_is_feature']}, got {result['is_feature']}"
    )


@pytest.mark.llm
@pytest.mark.parametrize("case", _NON_FEATURE_CASES, ids=_NON_FEATURE_CASE_IDS)
def test_rejection_message_present(case: dict) -> None:
    result = _invoke(case["raw_description"], case.get("previous_qa", []))

    print(f"\n[{case['id']}]")
    print(f"  rejection : {result['rejection_message']!r}")

    assert result["rejection_message"].strip(), (
        f"Non-feature input returned empty rejection_message for: "
        f"'{case['raw_description'][:60]}'"
    )


@pytest.mark.llm
@pytest.mark.parametrize("case", _FEATURE_CASES, ids=_FEATURE_CASE_IDS)
def test_ready_detection(case: dict) -> None:
    result = _invoke(case["raw_description"], case.get("previous_qa", []))

    print(f"\n[{case['id']}]")
    print(f"  ready : {result['ready']} (expected={case['expected_ready']})")
    print(f"  questions : {[q['id'] for q in result['questions']]}")

    assert result["ready"] == case["expected_ready"], (
        f"Wrong ready flag for '{case['raw_description'][:60]}': "
        f"expected ready={case['expected_ready']}, got {result['ready']}"
    )

    if case["expected_ready"]:
        assert result["questions"] == [], (
            f"ready=True but questions is not empty for '{case['raw_description'][:60]}': "
            f"{result['questions']}"
        )


@pytest.mark.llm
@pytest.mark.parametrize("case", _QUESTION_CASES, ids=_QUESTION_CASE_IDS)
def test_question_topic_recall(case: dict) -> None:
    result = _invoke(case["raw_description"], case.get("previous_qa", []))

    questions = result["questions"]

    assert len(questions) > 0, (
        f"Expected clarifying questions for '{case['raw_description'][:60]}' "
        f"but agent returned ready=True with no questions"
    )

    metrics = _calculate_topic_recall(case["expected_topics"], questions)
    error_rate = 1.0 - metrics["recall"]

    print(f"\n[{case['id']}]")
    print(f"  Questions            : {[q['id'] for q in questions]}")
    print(f"  Topic recall         : {metrics['recall']:.2f}  ({metrics['covered']}/{metrics['total']} covered)")
    print(f"  Extraction error rate: {error_rate:.2f}")
    if metrics["missed"]:
        print(f"  Missed topics        : {metrics['missed']}")

    assert metrics["recall"] >= 0.3, (
        f"Topic recall too low for '{case['raw_description'][:60]}': {metrics['recall']:.2f} "
        f"(error rate={error_rate:.2f}). Missed: {metrics['missed']}"
    )


@pytest.mark.llm
def test_aggregate_metrics() -> None:
    classification_hits: list[bool] = []
    ready_hits: list[bool] = []
    topic_recalls: list[float] = []

    for case in _CASES:
        result = _invoke(case["raw_description"], case.get("previous_qa", []))

        classification_hits.append(result["is_feature"] == case["expected_is_feature"])

        if case["expected_is_feature"]:
            ready_hits.append(result["ready"] == case["expected_ready"])

        if case["expected_is_feature"] and not case["expected_ready"] and case.get("expected_topics"):
            m = _calculate_topic_recall(case["expected_topics"], result["questions"])
            topic_recalls.append(m["recall"])

    classification_accuracy = sum(classification_hits) / len(classification_hits)
    ready_accuracy = sum(ready_hits) / len(ready_hits) if ready_hits else 1.0
    avg_topic_recall = sum(topic_recalls) / len(topic_recalls) if topic_recalls else 1.0
    avg_error_rate = 1.0 - avg_topic_recall

    print(f"\n=== Context Gatherer Aggregate Metrics ({len(_CASES)} cases) ===")
    print(f"  Classification accuracy  : {classification_accuracy:.2f}  "
          f"({sum(classification_hits)}/{len(classification_hits)} correct)")
    print(f"  Ready detection accuracy : {ready_accuracy:.2f}  "
          f"({sum(ready_hits)}/{len(ready_hits)} correct)")
    print(f"  Avg topic recall         : {avg_topic_recall:.2f}  ({len(topic_recalls)} question cases)")
    print(f"  Avg extraction error rate: {avg_error_rate:.2f}")

    assert classification_accuracy >= 0.8, (
        f"Classification accuracy too low: {classification_accuracy:.2f}"
    )
    assert ready_accuracy >= 0.8, (
        f"Ready detection accuracy too low: {ready_accuracy:.2f}"
    )
    assert avg_topic_recall >= 0.3, (
        f"Average topic recall too low: {avg_topic_recall:.2f} "
        f"(avg extraction error rate: {avg_error_rate:.2f})"
    )
