"""
Agent 3 — Documenter & Critic (Reflection)

Responsibilities:
  - Compile all cumulative state data into the structured final document.
  - Run a self-review pass (Reflection Pattern) to check QA constraints:
      · No obvious risk omitted.
      · No irrelevant test type suggested.
      · Criticality is coherent with the risks.
      · Scenarios cover positive, negative, and edge cases.
      · Every test type has a justification.
  - If the self-review finds a critical flaw, append "REVER_ESTRATEGIA" to
    reflection_logs so the router sends flow back to Agent 2.
  - Otherwise append "APROVADO" and let the flow reach END.

Writes to state:
  - final_documentation
  - reflection_logs
  - reflection_iteration  (incremented each cycle)
"""

from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.llm_provider import get_llm
from app.core.state import TestDocState

_REVISION_SIGNAL = "REVER_ESTRATEGIA"
_APPROVAL_SIGNAL = "APROVADO"


class _ReflectionOutput(BaseModel):
    decision: Literal["APROVADO", "REVER_ESTRATEGIA"] = Field(
        description=(
            "APROVADO quando o documento estiver completo e coerente; "
            "REVER_ESTRATEGIA quando houver falha crítica que exija nova estratégia."
        )
    )
    findings: list[str] = Field(
        default_factory=list,
        description="Lista objetiva de problemas encontrados ou pontos validados.",
    )
    revision_guidance: str = Field(
        default="",
        description=(
            "Orientação concreta para o estrategista quando decision for "
            "REVER_ESTRATEGIA. Deve ficar vazio ou breve quando aprovado."
        ),
    )


def _format_numbered(items: list[str] | None) -> str:
    if not items:
        return "Nenhum item informado."
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def _format_bullets(items: list[str] | None) -> str:
    if not items:
        return "- Nenhum item informado."
    return "\n".join(f"- {item}" for item in items)


def _format_documentation(state: TestDocState) -> str:
    """
    Assembles all state fields into the standardised Markdown/text report
    defined by the project documentation PDFs.
    """
    feature_name = state.feature_name or "Funcionalidade sem nome"
    description = state.description or "Resumo nao informado."
    criticality = state.criticality or "Nao classificada"
    justification = state.justification or "Justificativa nao informada."

    return f"""# Plano de Testes - {feature_name}

## Funcionalidade
{feature_name}

## Resumo
{description}

## Criticidade
{criticality}

## Regras de Negocio
{_format_bullets(state.business_rules)}

## Dependencias
{_format_bullets(state.dependencies)}

## Riscos Identificados
{_format_numbered(state.identified_risks)}

## Tipos de Teste Recomendados
{_format_bullets(state.recommended_test_types)}

## Cenarios Prioritarios
{_format_numbered(state.prioritized_scenarios)}

## Justificativa
{justification}
"""


_REFLECTION_PROMPT = """\
Voce e o agente Documentador e Critico do TestDoc Agent.

Revise criticamente o documento de testes gerado a partir dos dados cumulativos
dos agentes anteriores. Use o padrao Reflection/Critic descrito na especificacao:

- verificar se algum risco obvio foi omitido;
- verificar se algum tipo de teste recomendado e irrelevante;
- verificar se a criticidade esta coerente com riscos e impacto;
- verificar se os cenarios incluem casos positivos, negativos e de borda;
- verificar se ha justificativa para cada tipo de teste recomendado;
- verificar se a documentacao esta completa e limpa.

Retorne REVER_ESTRATEGIA apenas para falhas criticas de estrategia, por exemplo:
risco central sem cenario correspondente, tipo de teste claramente irrelevante,
criticidade incompatível com impacto financeiro/seguranca/dados sensiveis, ou
ausencia de casos negativos/de borda. Para problemas apenas textuais ou de
formatacao, aprove.

Dados estruturados:
Feature: {feature_name}
Descricao: {description}
Regras de negocio:
{business_rules}
Dependencias: {dependencies}
Criticidade: {criticality}
Riscos:
{risks}
Tipos de teste:
{test_types}
Cenarios:
{scenarios}
Justificativa:
{justification}

Documento gerado:
{draft}
"""


def _run_reflection(state: TestDocState, draft: str) -> str:
    """
    Invokes a critic LLM prompt against 'draft'.
    Returns either _REVISION_SIGNAL or _APPROVAL_SIGNAL.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", _REFLECTION_PROMPT),
    ])
    llm = get_llm()
    chain = prompt | llm.with_structured_output(_ReflectionOutput)

    result: _ReflectionOutput = chain.invoke({
        "feature_name": state.feature_name,
        "description": state.description,
        "business_rules": _format_bullets(state.business_rules),
        "dependencies": _format_bullets(state.dependencies),
        "criticality": state.criticality or "Nao classificada",
        "risks": _format_numbered(state.identified_risks),
        "test_types": _format_bullets(state.recommended_test_types),
        "scenarios": _format_numbered(state.prioritized_scenarios),
        "justification": state.justification or "",
        "draft": draft,
    })

    findings = "; ".join(result.findings).strip()
    guidance = result.revision_guidance.strip()

    if result.decision == _REVISION_SIGNAL:
        details = " | ".join(part for part in [findings, guidance] if part)
        return f"{_REVISION_SIGNAL}: {details}" if details else _REVISION_SIGNAL

    return f"{_APPROVAL_SIGNAL}: {findings}" if findings else _APPROVAL_SIGNAL


def agent_3_documenter_reflection_node(state: TestDocState) -> dict:
    """
    LangGraph node — receives full state, returns partial update dict.

    1. Call _format_documentation() to produce the draft.
    2. Call _run_reflection() to evaluate the draft.
    3. Append the signal to reflection_logs.
    4. Increment reflection_iteration.
    5. Return updated fields.
    """
    draft = _format_documentation(state)
    signal = _run_reflection(state, draft)

    updated_logs = list(state.reflection_logs or []) + [signal]

    return {
        "final_documentation": draft,
        "reflection_logs": updated_logs,
        "reflection_iteration": state.reflection_iteration + 1,
    }
