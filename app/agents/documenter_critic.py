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
    feature_name  = state.feature_name  or "Funcionalidade sem nome"
    description   = state.description   or "Resumo não informado."
    criticality   = state.criticality   or "Não classificada"
    justification = state.justification or "Justificativa não informada."

    return f"""# Plano de Testes — {feature_name}

## Funcionalidade
{feature_name}

## Resumo
{description}

## Criticidade
{criticality}

## Regras de Negócio
{_format_bullets(state.business_rules)}

## Dependências
{_format_bullets(state.dependencies)}

## Riscos Identificados
{_format_numbered(state.identified_risks)}

## Tipos de Teste Recomendados
{_format_bullets(state.recommended_test_types)}

## Cenários Prioritários
{_format_numbered(state.prioritized_scenarios)}

## Justificativa
{justification}
"""


_REFLECTION_SYSTEM = """\
Você é o agente Documentador e Crítico do TestDoc Agent.

Revise criticamente o documento de testes gerado. Retorne REVER_ESTRATEGIA apenas \
para falhas críticas de estratégia:
- risco central sem cenário correspondente
- tipo de teste claramente irrelevante para a feature
- criticidade incompatível com o impacto real (financeiro, segurança, dados sensíveis)
- ausência de casos negativos ou de borda

Para problemas apenas textuais ou de formatação, aprove.\
"""

_REFLECTION_HUMAN = """\
Feature: {feature_name}
Descrição: {description}
Regras de negócio:
{business_rules}
Dependências: {dependencies}
Criticidade: {criticality}
Riscos:
{risks}
Tipos de teste:
{test_types}
Cenários:
{scenarios}
Justificativa:
{justification}

Documento gerado:
{draft}\
"""


def _run_reflection(state: TestDocState, draft: str) -> str:
    chain = (
        ChatPromptTemplate.from_messages([
            ("system", _REFLECTION_SYSTEM),
            ("human", _REFLECTION_HUMAN),
        ])
        | get_llm().with_structured_output(_ReflectionOutput)
    )

    result: _ReflectionOutput = chain.invoke({
        "feature_name": state.feature_name,
        "description": state.description,
        "business_rules": _format_bullets(state.business_rules),
        "dependencies": _format_bullets(state.dependencies),
        "criticality": state.criticality or "Não classificada",
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
    draft = _format_documentation(state)
    signal = _run_reflection(state, draft)

    updated_logs = list(state.reflection_logs or []) + [signal]

    return {
        "final_documentation": draft,
        "reflection_logs": updated_logs,
        "reflection_iteration": state.reflection_iteration + 1,
    }
