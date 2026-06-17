import pytest

from app.agents import documenter_critic as critic
from app.core.state import TestDocState as State


def _normalize(text: str) -> str:
    replacements = str.maketrans(
        {
            "á": "a",
            "ã": "a",
            "â": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "õ": "o",
            "ô": "o",
            "ú": "u",
            "ç": "c",
            "Á": "A",
            "Ã": "A",
            "É": "E",
            "Ê": "E",
            "Í": "I",
            "Ó": "O",
            "Õ": "O",
            "Ú": "U",
            "Ç": "C",
        }
    )
    return text.translate(replacements)


def _state(**overrides) -> State:
    data = {
        "feature_name": "Login",
        "description": "Autentica usuario com email e senha.",
        "business_rules": ["Senha deve ser armazenada com hash e salt."],
        "dependencies": ["Servico de identidade"],
        "identified_risks": ["Forca bruta contra endpoint de login."],
        "criticality": "Alta",
        "recommended_test_types": ["Seguranca", "Integracao", "Negativo"],
        "prioritized_scenarios": [
            "Login valido retorna sessao.",
            "Senha invalida retorna erro sem revelar detalhes.",
            "Tentativas repetidas respeitam rate limit por IP.",
        ],
        "justification": "Fluxo sensivel por envolver credenciais.",
    }
    data.update(overrides)
    return State(**data)


class _FakeLLM:
    def __init__(self, output):
        self.output = output

    def with_structured_output(self, schema):
        return lambda _: schema(**self.output)


def test_documenter_node_builds_document_and_appends_approval(monkeypatch):
    def fake_reflection(state, draft):
        assert "Login" in draft
        assert "Forca bruta" in draft
        return "APROVADO: documento coerente"

    monkeypatch.setattr(critic, "_run_reflection", fake_reflection)

    state = _state(reflection_logs=["APROVADO: ciclo anterior"], reflection_iteration=1)
    result = critic.agent_3_documenter_reflection_node(state)

    assert result["reflection_iteration"] == 2
    assert result["reflection_logs"] == [
        "APROVADO: ciclo anterior",
        "APROVADO: documento coerente",
    ]
    assert "# Plano de Testes" in result["final_documentation"]
    assert "## Riscos Identificados" in result["final_documentation"]
    assert "## Cenarios Prioritarios" in _normalize(result["final_documentation"])


def test_run_reflection_approves_when_findings_are_not_critical(monkeypatch):
    monkeypatch.setattr(
        critic,
        "get_llm",
        lambda: _FakeLLM(
            {
                "decision": "APROVADO",
                "findings": ["Apenas ajuste textual; estrategia cobre risco e cenarios."],
                "revision_guidance": "",
            }
        ),
    )

    signal = critic._run_reflection(_state(), "documento")

    assert signal.startswith("APROVADO")
    assert "REVER_ESTRATEGIA" not in signal
    assert "Apenas ajuste textual" in signal


def test_run_reflection_requests_revision_for_critical_strategy_gap(monkeypatch):
    monkeypatch.setattr(
        critic,
        "get_llm",
        lambda: _FakeLLM(
            {
                "decision": "REVER_ESTRATEGIA",
                "findings": ["Risco central de forca bruta sem cenario correspondente."],
                "revision_guidance": "Adicionar cenario de rate limit e bloqueio progressivo.",
            }
        ),
    )

    state = _state(
        prioritized_scenarios=["Login valido retorna sessao."],
        recommended_test_types=["Funcional"],
    )
    signal = critic._run_reflection(state, "documento")

    assert signal.startswith("REVER_ESTRATEGIA")
    assert "forca bruta" in signal
    assert "rate limit" in signal


def test_reflection_prompt_guards_against_known_false_positives_and_false_negatives():
    prompt = _normalize(critic._REFLECTION_SYSTEM)

    assert "Retorne REVER_ESTRATEGIA apenas" in prompt
    assert "Evite falso positivo" in prompt
    assert "nao exija refresh token, logout, sessao ou MFA" in prompt
    assert "Para problemas apenas textuais ou de formatacao, aprove." in prompt

    critical_rules = [
        "risco central sem cenario correspondente",
        "tipo de teste claramente irrelevante",
        "ausencia de casos negativos ou de borda",
        "mais de 15 cenarios",
        "mistura de dominios",
        "hash com salt",
        "rate limit por IP",
        "refresh token",
        "logout normal",
    ]

    for rule in critical_rules:
        assert rule in prompt


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        ([], "Nenhum item informado."),
        (None, "Nenhum item informado."),
        (["um", "dois"], "1. um\n2. dois"),
    ],
)
def test_format_numbered_handles_empty_and_ordered_items(items, expected):
    assert critic._format_numbered(items) == expected
