"""
Agent 0 — Feature Parser (Reflection pattern)

Round 1 — Extraction:
  Parses raw_description into structured fields.

Round 2+ — Reflection (up to _MAX_REFLECTION_ITERATIONS):
  Critic reviews the extraction looking for implicit business rules and
  overlooked dependencies. If incomplete, returns an improved version.
  Loop breaks on approval or when the iteration limit is reached.

Writes to state:
  - feature_name
  - description
  - business_rules
  - dependencies
"""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.llm_provider import get_llm
from app.core.state import TestDocState

_MAX_REFLECTION_ITERATIONS = 2


# ── Extraction schema ──────────────────────────────────────────────────────

class _ParsedFeature(BaseModel):
    feature_name: str = Field(
        description="Nome curto e objetivo da funcionalidade."
    )
    description: str = Field(
        description="Descrição clara do que a funcionalidade faz."
    )
    business_rules: list[str] = Field(
        description="Lista de regras de negócio identificadas no texto."
    )
    dependencies: list[str] = Field(
        description="Lista de serviços, módulos ou sistemas que a funcionalidade depende."
    )


# ── Reflection schema ──────────────────────────────────────────────────────

class _ExtractionReview(BaseModel):
    approved: bool = Field(
        description=(
            "True se a extração está completa e precisa. "
            "False se há regras implícitas ou dependências não capturadas."
        )
    )
    critique: str = Field(
        description="O que está faltando ou incorreto. String vazia se aprovado."
    )
    feature_name: str
    description: str
    business_rules: list[str] = Field(
        description="Lista completa e corrigida de regras de negócio."
    )
    dependencies: list[str] = Field(
        description="Lista completa e corrigida de dependências."
    )


# ── Prompts ────────────────────────────────────────────────────────────────

_EXTRACT_SYSTEM = """\
Você é um analista de requisitos de software. Sua tarefa é ler uma descrição textual \
de uma funcionalidade e extrair as informações estruturadas dela.

Extraia:
- feature_name: nome curto e objetivo da funcionalidade (máximo 5 palavras).
- description: descrição clara do que a funcionalidade faz (1 a 2 frases).
- business_rules: lista de regras de negócio identificadas. Se não houver regras \
  explícitas, infira as mais óbvias a partir do contexto.
- dependencies: serviços, módulos ou sistemas externos mencionados ou implícitos. \
  Se não houver, retorne lista vazia.\
"""

_EXTRACT_HUMAN = "Descrição da funcionalidade:\n\n{raw_description}"

_REVIEW_SYSTEM = """\
Você é um analista de requisitos sênior revisando uma extração de feature.

Avalie se a extração está completa comparando-a com a descrição original. Verifique:
- Há regras de negócio implícitas no texto que não foram capturadas?
- Existem restrições óbvias do domínio que foram omitidas?
- Alguma dependência externa (serviço, banco, API, módulo) foi ignorada?
- O feature_name e a description representam fielmente a funcionalidade?

Se a extração estiver completa: retorne approved=true e critique="".
Se houver lacunas: retorne approved=false, descreva o problema em critique \
e forneça a versão corrigida de todos os campos.\
"""

_REVIEW_HUMAN = """\
Descrição original:
{raw_description}

Extração atual:
{current_extraction}"""


# ── Node ───────────────────────────────────────────────────────────────────

def agent_0_feature_parser_node(state: TestDocState) -> dict:
    llm = get_llm()

    extract_chain = (
        ChatPromptTemplate.from_messages([("system", _EXTRACT_SYSTEM), ("human", _EXTRACT_HUMAN)])
        | llm.with_structured_output(_ParsedFeature)
    )
    review_chain = (
        ChatPromptTemplate.from_messages([("system", _REVIEW_SYSTEM), ("human", _REVIEW_HUMAN)])
        | llm.with_structured_output(_ExtractionReview)
    )

    parsed: _ParsedFeature = extract_chain.invoke({"raw_description": state.raw_description})

    for _ in range(_MAX_REFLECTION_ITERATIONS):
        review: _ExtractionReview = review_chain.invoke({
            "raw_description": state.raw_description,
            "current_extraction": parsed.model_dump_json(indent=2),
        })

        if review.approved:
            break

        parsed = _ParsedFeature(
            feature_name=review.feature_name,
            description=review.description,
            business_rules=review.business_rules,
            dependencies=review.dependencies,
        )

    return {
        "feature_name": parsed.feature_name,
        "description": parsed.description,
        "business_rules": parsed.business_rules,
        "dependencies": parsed.dependencies,
    }
