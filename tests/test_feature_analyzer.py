"""
Evaluation suite for Feature Analyzer agent.

For each eval case, calls the agent with the real LLM and measures:
  - Risk Recall          — expected risks covered by generated risks
  - Risk Precision       — generated risks grounded in the gabarito
  - Risk F1              — harmonic mean of Recall and Precision
  - Criticality accuracy — Baixa/Média/Alta/Crítica exact match
  - Domain confusion     — FP risks matching known wrong-domain patterns

LLM-as-judge (one batched call per case) handles semantic matching.
Domain confusion is classified separately from generic hallucinations.

Run with:
    pytest tests/test_feature_analyzer.py -v -s -m llm
"""

import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agents.feature_analyzer import agent_0_feature_analyzer_node
from app.core.llm_provider import get_llm
from app.core.state import TestDocState

# ── Paths ──────────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parent.parent / "app" / "data" / "eval"
_FEATURES_FILE = _DATA_DIR / "features.json"
_EXPECTED_FILE = _DATA_DIR / "expected_outputs.json"
_NOT_EXPECTED_FILE = _DATA_DIR / "not_expected_outputs.json"

# ── Thresholds ─────────────────────────────────────────────────────────────

_MIN_RECALL_PER_CASE = 0.6
_MIN_AGGREGATE_RECALL = 0.7
_MIN_AGGREGATE_F1 = 0.6
_MIN_CRITICALITY_ACCURACY = 0.75

# ── Judge schemas ──────────────────────────────────────────────────────────


class _CoverageResult(BaseModel):
    covered_expected_indices: list[int] = Field(
        description=(
            "0-based indices of expected risks semantically covered "
            "by at least one generated risk."
        )
    )
    matched_generated_indices: list[int] = Field(
        description=(
            "0-based indices of generated risks that correspond to "
            "at least one expected risk."
        )
    )


class _ConfusionResult(BaseModel):
    confused_indices: list[int] = Field(
        description=(
            "0-based indices of the candidate FP risks that match "
            "a known domain confusion pattern."
        )
    )


# ── Judge prompts ──────────────────────────────────────────────────────────

_COVERAGE_SYSTEM = """\
You evaluate whether generated test risks semantically cover expected test risks.

Two risks are semantically equivalent when they describe the same failure scenario, \
security concern, or business rule violation — even if worded differently.

Examples of EQUIVALENT pairs:
  - "Aceitar e-mail já cadastrado" ≡ "Permitir registro com e-mail duplicado no sistema"
  - "Senha sem validação de tamanho mínimo" ≡ "Aceitar senha abaixo do mínimo de 8 caracteres"

Examples of NON-EQUIVALENT pairs:
  - "Aceitar e-mail já cadastrado" ≢ "Falha no gateway de pagamento"
  - "Race condition ao agendar horários" ≢ "Timeout na API externa"

Return:
  covered_expected_indices — 0-based indices of expected risks covered by at least one generated risk.
  matched_generated_indices — 0-based indices of generated risks that correspond to at least one expected risk.\
"""

_COVERAGE_HUMAN = """\
Feature: {feature_name}

Expected risks (0-based):
{expected_risks}

Generated risks (0-based):
{generated_risks}\
"""

_CONFUSION_SYSTEM = """\
You detect domain confusion in test risks.

A domain confusion occurs when a risk clearly belongs to a different feature's \
domain — not the one being analyzed.

Return confused_indices: 0-based indices of the candidate risks that match \
any known domain confusion pattern.\
"""

_CONFUSION_HUMAN = """\
Feature being analyzed: {feature_name} — {description}

Candidate FP risks (0-based):
{fp_risks}

Known domain confusion patterns (risks from other features that must NOT appear here):
{not_expected_risks}\
"""

# ── Judge helpers ──────────────────────────────────────────────────────────


def _fmt(items: list[str]) -> str:
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items))


def _run_coverage_judge(
    feature_name: str,
    expected: list[str],
    generated: list[str],
) -> _CoverageResult:
    if not generated:
        return _CoverageResult(
            covered_expected_indices=[],
            matched_generated_indices=[],
        )

    chain = (
        ChatPromptTemplate.from_messages([
            ("system", _COVERAGE_SYSTEM),
            ("human", _COVERAGE_HUMAN),
        ])
        | get_llm().with_structured_output(_CoverageResult)
    )
    result: _CoverageResult = chain.invoke({
        "feature_name": feature_name,
        "expected_risks": _fmt(expected),
        "generated_risks": _fmt(generated),
    })
    result.covered_expected_indices = [
        i for i in result.covered_expected_indices if i < len(expected)
    ]
    result.matched_generated_indices = [
        i for i in result.matched_generated_indices if i < len(generated)
    ]
    return result


def _run_confusion_judge(
    feature_name: str,
    description: str,
    fp_risks: list[str],
    not_expected: list[str],
) -> list[int]:
    if not fp_risks or not not_expected:
        return []

    chain = (
        ChatPromptTemplate.from_messages([
            ("system", _CONFUSION_SYSTEM),
            ("human", _CONFUSION_HUMAN),
        ])
        | get_llm().with_structured_output(_ConfusionResult)
    )
    result: _ConfusionResult = chain.invoke({
        "feature_name": feature_name,
        "description": description,
        "fp_risks": _fmt(fp_risks),
        "not_expected_risks": _fmt(not_expected),
    })
    return [i for i in result.confused_indices if i < len(fp_risks)]


# ── Metrics ────────────────────────────────────────────────────────────────


def _compute_metrics(
    tp_recall: int,
    total_expected: int,
    tp_precision: int,
    total_generated: int,
) -> dict[str, float]:
    recall = tp_recall / total_expected if total_expected else 1.0
    precision = tp_precision / total_generated if total_generated else 1.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return {"recall": recall, "precision": precision, "f1": f1}


# ── Case evaluation (module-level cache) ───────────────────────────────────

_EVAL_CACHE: dict[str, dict[str, Any]] = {}


def _evaluate_case(
    feature: dict,
    expected: dict,
    not_expected_risks: list[str],
) -> dict[str, Any]:
    case_id = feature["id"]
    if case_id in _EVAL_CACHE:
        return _EVAL_CACHE[case_id]

    state = TestDocState(
        feature_name=feature["feature_name"],
        description=feature["description"],
        business_rules=feature["business_rules"],
        dependencies=feature["dependencies"],
    )
    output = agent_0_feature_analyzer_node(state)

    generated_risks: list[str] = output["identified_risks"]
    generated_criticality: str = output["criticality"]
    expected_risks: list[str] = expected["identified_risks"]

    coverage = _run_coverage_judge(
        feature["feature_name"], expected_risks, generated_risks
    )

    fp_indices = [
        i for i in range(len(generated_risks))
        if i not in coverage.matched_generated_indices
    ]
    fp_risks = [generated_risks[i] for i in fp_indices]
    confused_fp_indices = _run_confusion_judge(
        feature["feature_name"],
        feature["description"],
        fp_risks,
        not_expected_risks,
    )

    metrics = _compute_metrics(
        tp_recall=len(coverage.covered_expected_indices),
        total_expected=len(expected_risks),
        tp_precision=len(coverage.matched_generated_indices),
        total_generated=len(generated_risks),
    )

    result: dict[str, Any] = {
        "generated_risks": generated_risks,
        "generated_criticality": generated_criticality,
        "expected_criticality": expected["criticality"],
        "covered_expected": coverage.covered_expected_indices,
        "matched_generated": coverage.matched_generated_indices,
        "fp_risks": fp_risks,
        "domain_confused": [fp_risks[i] for i in confused_fp_indices],
        "hallucinations": [
            fp_risks[i]
            for i in range(len(fp_risks))
            if i not in confused_fp_indices
        ],
        "criticality_correct": generated_criticality == expected["criticality"],
        **metrics,
    }

    _EVAL_CACHE[case_id] = result
    return result


# ── Data loading ───────────────────────────────────────────────────────────


def _load_data() -> tuple[list[dict], dict[str, dict], dict[str, list[str]]]:
    features = json.loads(_FEATURES_FILE.read_text(encoding="utf-8"))
    expected_list = json.loads(_EXPECTED_FILE.read_text(encoding="utf-8"))
    not_expected_list = json.loads(_NOT_EXPECTED_FILE.read_text(encoding="utf-8"))

    expected_by_id = {e["feature_id"]: e for e in expected_list}
    not_expected_by_id = {n["feature_id"]: n["not_expected_risks"] for n in not_expected_list}

    return features, expected_by_id, not_expected_by_id


_FEATURES, _EXPECTED, _NOT_EXPECTED = _load_data()
_CASE_IDS = [f["id"] for f in _FEATURES]
_CASES = [
    (f, _EXPECTED[f["id"]], _NOT_EXPECTED.get(f["id"], []))
    for f in _FEATURES
]


# ── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.llm
@pytest.mark.parametrize("feature,expected,not_expected", _CASES, ids=_CASE_IDS)
def test_risk_recall(feature: dict, expected: dict, not_expected: list[str]) -> None:
    result = _evaluate_case(feature, expected, not_expected)

    print(f"\n[{feature['id']}] {feature['feature_name']}")
    print(f"  Recall    : {result['recall']:.2f}")
    print(f"  Precision : {result['precision']:.2f}")
    print(f"  F1        : {result['f1']:.2f}")
    print(f"  Covered   : {len(result['covered_expected'])}/{len(expected['identified_risks'])} expected risks")
    if result["fp_risks"]:
        print(f"  FP risks  : {result['fp_risks']}")

    assert result["recall"] >= _MIN_RECALL_PER_CASE, (
        f"Recall too low for '{feature['feature_name']}': {result['recall']:.2f} "
        f"(covered {len(result['covered_expected'])}/{len(expected['identified_risks'])} risks)"
    )


@pytest.mark.llm
@pytest.mark.parametrize("feature,expected,not_expected", _CASES, ids=_CASE_IDS)
def test_criticality_accuracy(feature: dict, expected: dict, not_expected: list[str]) -> None:
    result = _evaluate_case(feature, expected, not_expected)

    print(f"\n[{feature['id']}] {feature['feature_name']}")
    print(
        f"  Criticality: {result['generated_criticality']} "
        f"(expected={result['expected_criticality']})"
    )

    assert result["criticality_correct"], (
        f"Wrong criticality for '{feature['feature_name']}': "
        f"expected={result['expected_criticality']}, got={result['generated_criticality']}"
    )


@pytest.mark.llm
@pytest.mark.parametrize("feature,expected,not_expected", _CASES, ids=_CASE_IDS)
def test_no_domain_confusion(feature: dict, expected: dict, not_expected: list[str]) -> None:
    result = _evaluate_case(feature, expected, not_expected)

    print(f"\n[{feature['id']}] {feature['feature_name']}")
    if result["domain_confused"]:
        print(f"  Domain confusion : {result['domain_confused']}")
    if result["hallucinations"]:
        print(f"  Hallucinations   : {result['hallucinations']}")

    assert not result["domain_confused"], (
        f"Domain confusion detected in '{feature['feature_name']}': "
        f"{result['domain_confused']}"
    )


@pytest.mark.llm
def test_aggregate_metrics() -> None:
    recalls: list[float] = []
    precisions: list[float] = []
    f1s: list[float] = []
    criticality_hits: list[bool] = []
    total_domain_confused = 0
    total_hallucinations = 0

    for feature, expected, not_expected in _CASES:
        result = _evaluate_case(feature, expected, not_expected)
        recalls.append(result["recall"])
        precisions.append(result["precision"])
        f1s.append(result["f1"])
        criticality_hits.append(result["criticality_correct"])
        total_domain_confused += len(result["domain_confused"])
        total_hallucinations += len(result["hallucinations"])

    avg_recall = sum(recalls) / len(recalls)
    avg_precision = sum(precisions) / len(precisions)
    avg_f1 = sum(f1s) / len(f1s)
    criticality_accuracy = sum(criticality_hits) / len(criticality_hits)

    print(f"\n=== Feature Analyzer Aggregate Metrics ({len(_CASES)} cases) ===")
    print(f"  Avg Recall             : {avg_recall:.2f}")
    print(f"  Avg Precision          : {avg_precision:.2f}")
    print(f"  Avg F1                 : {avg_f1:.2f}")
    print(
        f"  Criticality accuracy   : {criticality_accuracy:.2f}  "
        f"({sum(criticality_hits)}/{len(criticality_hits)} correct)"
    )
    print(f"  Domain confusion total : {total_domain_confused} risk(s) across all cases")
    print(f"  Hallucinations total   : {total_hallucinations} risk(s) across all cases")

    assert avg_recall >= _MIN_AGGREGATE_RECALL, (
        f"Average recall too low: {avg_recall:.2f}"
    )
    assert avg_f1 >= _MIN_AGGREGATE_F1, (
        f"Average F1 too low: {avg_f1:.2f}"
    )
    assert criticality_accuracy >= _MIN_CRITICALITY_ACCURACY, (
        f"Criticality accuracy too low: {criticality_accuracy:.2f}"
    )
