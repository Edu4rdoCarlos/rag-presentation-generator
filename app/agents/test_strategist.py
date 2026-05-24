"""
Agent 2 — Test Strategist (Tool Use)

Responsibilities:
  - Consume identified_risks and criticality produced by Agent 1.
  - Phase 1 (Tool Use): LLM calls map_risks_to_test_types(), which applies the
    Decision Matrix deterministically to produce recommended_test_types.
  - Phase 2 (Structured Output): LLM generates prioritized_scenarios and
    justification using the accumulated context from both phases.

Writes to state:
  - recommended_test_types
  - prioritized_scenarios
  - justification
"""

import logging

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.core.llm_provider import get_llm
from app.core.state import TestDocState

logger = logging.getLogger(__name__)


# ── Decision Matrix ────────────────────────────────────────────────────────
# Source: Section 14 of the project documentation.
# Keys are lowercase substrings matched against the combined risk text.
# Values are the test types that apply whenever the keyword is present.

_DECISION_MATRIX: dict[str, list[str]] = {
    "autenticação":     ["segurança", "integração", "E2E"],
    "autorização":      ["segurança", "casos negativos"],
    "permissão":        ["segurança", "casos negativos"],
    "banco de dados":   ["integração", "migração/banco"],
    "migração":         ["integração", "migração/banco"],
    "schema":           ["integração", "migração/banco"],
    "api":              ["integração", "contrato/API"],
    "endpoint":         ["integração", "contrato/API"],
    "serviço externo":  ["integração", "contrato/API"],
    "integração":       ["integração", "contrato/API"],
    "pagamento":        ["unitário", "integração", "E2E", "segurança"],
    "financeiro":       ["unitário", "integração", "casos de borda"],
    "cálculo":          ["unitário", "integração", "casos de borda"],
    "desconto":         ["unitário", "integração"],
    "cupom":            ["unitário", "integração", "segurança"],
    "upload":           ["integração", "segurança", "validação arquivo"],
    "arquivo":          ["integração", "segurança", "validação arquivo"],
    "relatório":        ["performance", "integração"],
    "exclusão":         ["segurança", "integração", "regressão"],
    "remoção":          ["segurança", "integração", "regressão"],
    "fluxo":            ["E2E"],
    "interface":        ["UI/componente"],
    "formulário":       ["UI/componente"],
    "regra de negócio": ["unitário"],
}

# Minimum test types guaranteed by criticality level, regardless of keyword matches.
_CRITICALITY_FLOOR: dict[str, list[str]] = {
    "Baixa":   ["unitário"],
    "Média":   ["unitário", "integração"],
    "Alta":    ["unitário", "integração"],
    "Crítica": ["unitário", "integração", "E2E"],
}


# ── Tool: Decision Matrix (bound to LLM via bind_tools) ───────────────────

@tool
def map_risks_to_test_types(risks: list[str], criticality: str) -> list[str]:
    """
    Applies the Decision Matrix to map identified feature risks and criticality
    level to the recommended test types. Always call this tool first, passing
    the complete list of risks and the criticality classification.

    Args:
        risks: List of identified risks from the risk analyst agent.
        criticality: Feature criticality ("Baixa", "Média", "Alta" or "Crítica").

    Returns:
        Deduplicated, sorted list of recommended test type labels.
    """
    test_types: set[str] = set()

    combined_risks = " ".join(risks).lower()
    for keyword, types in _DECISION_MATRIX.items():
        if keyword in combined_risks:
            test_types.update(types)

    # Guarantee minimum coverage based on criticality
    floor = _CRITICALITY_FLOOR.get(criticality, ["unitário"])
    test_types.update(floor)

    return sorted(test_types)


# ── Structured output schema (Phase 2) ────────────────────────────────────

class _StrategyOutput(BaseModel):
    prioritized_scenarios: list[str] = Field(
        description=(
            "Lista ordenada de cenários de teste a implementar. Cada item deve ser uma "
            "descrição concisa no formato: verbo no infinitivo + contexto específico. "
            "Inclua obrigatoriamente casos positivos (caminho feliz), negativos "
            "(entrada inválida / estado proibido) e de borda. "
            "Ordene do cenário mais crítico para o menos crítico."
        )
    )
    justification: str = Field(
        description=(
            "Justificativa técnica explicando por que cada tipo de teste recomendado "
            "é necessário para esta feature. Correlacione diretamente cada tipo com "
            "os riscos identificados e as regras de negócio."
        )
    )


# ── Prompts ────────────────────────────────────────────────────────────────

_TOOL_CALL_PROMPT = """\
Você é um estrategista de testes de software. Analise os dados da feature abaixo e \
chame a ferramenta `map_risks_to_test_types` passando a lista de riscos e a criticidade \
para determinar os tipos de teste recomendados pela Matriz de Decisão.

Feature: {feature_name}
Descrição: {description}
Criticidade: {criticality}

Riscos identificados:
{risks_text}

Regras de negócio:
{rules_text}

Dependências: {dependencies_text}\
"""

_SCENARIOS_PROMPT = """\
Você é um estrategista de testes de software. Com base em todos os dados abaixo, \
gere os cenários de teste priorizados e a justificativa técnica.

Feature: {feature_name}
Descrição: {description}
Criticidade: {criticality}

Riscos identificados:
{risks_text}

Regras de negócio:
{rules_text}

Tipos de teste recomendados (resultado da Matriz de Decisão):
{test_types_text}

Feedback da revisão anterior, se houver:
{reflection_feedback}

Instruções para geração dos cenários:
- Gere cenários concretos e acionáveis (verbo no infinitivo + contexto específico).
- Cubra cada risco identificado com pelo menos um cenário.
- Inclua obrigatoriamente casos negativos e de borda além do caminho feliz.
- Ordene por criticidade: cenários que validam os maiores riscos primeiro.
- Quando houver feedback da revisão anterior, corrija explicitamente os problemas apontados.
- A justificativa deve explicar por que cada TIPO de teste é necessário para ESTA feature \
  específica, não de forma genérica.\
"""


# ── LangGraph node ─────────────────────────────────────────────────────────

def agent_2_test_strategist_node(state: TestDocState) -> dict:
    """
    LangGraph node — receives full state, returns partial update dict.

    Execution flow:

      Phase 1 — Tool Use
        LLM receives risks + criticality and calls map_risks_to_test_types().
        The @tool function applies the Decision Matrix keyword-matching algorithm
        deterministically, returning the recommended test type labels.

      Phase 2 — Structured Output
        LLM receives the complete context (risks + test types from Phase 1) and
        generates prioritized_scenarios and justification via with_structured_output().
    """
    llm = get_llm()

    criticality  = state.criticality or "Média"
    risks_text   = "\n".join(f"- {r}" for r in (state.identified_risks or []))
    rules_text   = "\n".join(f"- {r}" for r in state.business_rules)
    deps_text    = ", ".join(state.dependencies) if state.dependencies else "Nenhuma"

    # ── Phase 1: Tool Use — Decision Matrix ───────────────────────────────
    llm_with_tools = llm.bind_tools([map_risks_to_test_types], tool_choice="required")

    ai_message = llm_with_tools.invoke([
        HumanMessage(content=_TOOL_CALL_PROMPT.format(
            feature_name=state.feature_name,
            description=state.description,
            criticality=criticality,
            risks_text=risks_text,
            rules_text=rules_text,
            dependencies_text=deps_text,
        ))
    ])

    # Execute the tool call returned by the LLM
    recommended_test_types: list[str] = []

    for tool_call in ai_message.tool_calls:
        if tool_call["name"] == "map_risks_to_test_types":
            recommended_test_types = map_risks_to_test_types.invoke(tool_call["args"])

    # Safety fallback: LLM skipped the tool call — run Decision Matrix directly
    if not recommended_test_types:
        logger.warning(
            "LLM did not produce a tool call despite tool_choice='required'. "
            "Executing map_risks_to_test_types directly as fallback."
        )
        recommended_test_types = map_risks_to_test_types.invoke({
            "risks": state.identified_risks or [],
            "criticality": criticality,
        })

    # ── Phase 2: Structured output — scenarios + justification ────────────
    test_types_text = "\n".join(f"- {t}" for t in recommended_test_types)
    reflection_feedback = (
        state.reflection_logs[-1]
        if state.reflection_logs and "REVER_ESTRATEGIA" in state.reflection_logs[-1]
        else "Nenhum feedback anterior."
    )

    chain = llm.with_structured_output(_StrategyOutput)

    strategy: _StrategyOutput = chain.invoke(
        _SCENARIOS_PROMPT.format(
            feature_name=state.feature_name,
            description=state.description,
            criticality=criticality,
            risks_text=risks_text,
            rules_text=rules_text,
            test_types_text=test_types_text,
            reflection_feedback=reflection_feedback,
        )
    )

    return {
        "recommended_test_types": recommended_test_types,
        "prioritized_scenarios": strategy.prioritized_scenarios,
        "justification": strategy.justification,
    }
