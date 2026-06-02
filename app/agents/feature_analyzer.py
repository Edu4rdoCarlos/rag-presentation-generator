"""
Agent 0 — Feature Analyzer (merged Feature Parser + Risk Analyst)

When raw_description is set: extracts feature structure AND identifies risks
in a single LLM call, followed by a reflection pass (Reflection pattern).

When raw_description is absent: structured fields are already in state;
performs risk analysis only (Planner + RAG).

Both paths use RAG to retrieve annotated few-shot examples.

Writes to state:
  - feature_name, description, business_rules, dependencies  (raw_description path only)
  - retrieved_examples, identified_risks, criticality
"""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.llm_provider import get_llm
from app.core.state import TestDocState
from app.services.vector_store import get_similar_examples

_MAX_REFLECTION_ITERATIONS = 2


# ── Full analysis schema (raw_description path) ────────────────────────────

class _FullAnalysis(BaseModel):
    feature_name: str = Field(
        description="Nome curto e objetivo da funcionalidade (máximo 5 palavras)."
    )
    description: str = Field(
        description="Descrição clara do que a funcionalidade faz (1 a 2 frases)."
    )
    business_rules: list[str] = Field(
        description="Regras de negócio identificadas no texto. Se não houver explícitas, infira as óbvias."
    )
    dependencies: list[str] = Field(
        description="Serviços, módulos ou sistemas externos mencionados ou implícitos. Lista vazia se nenhum."
    )
    identified_risks: list[str] = Field(
        description="Lista de riscos funcionais, técnicos e de negócio identificados."
    )
    criticality: str = Field(
        description="Criticidade da feature: Baixa, Média, Alta ou Crítica."
    )


class _FullAnalysisReview(BaseModel):
    approved: bool = Field(
        description=(
            "True se a análise está completa e precisa. "
            "False se há regras implícitas, dependências ou riscos não capturados."
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
    identified_risks: list[str] = Field(
        description="Lista completa e corrigida de riscos."
    )
    criticality: str


# ── Risk-only schema (structured path) ────────────────────────────────────

class _RiskAnalysis(BaseModel):
    identified_risks: list[str] = Field(
        description="Lista de riscos funcionais, técnicos e de negócio identificados para a feature."
    )
    criticality: str = Field(
        description="Criticidade da feature: Baixa, Média, Alta ou Crítica."
    )


# ── Prompts ────────────────────────────────────────────────────────────────

_FULL_EXTRACT_SYSTEM = """\
Você é um analista de requisitos e especialista em qualidade de software. Em uma única \
etapa, extraia as informações estruturadas da descrição recebida E identifique os riscos \
associados.

Use os exemplos de referência abaixo para calibrar o nível de detalhe, o formato dos \
riscos e os critérios de criticidade esperados:

{examples}

Diretrizes de extração:
- feature_name: nome curto e objetivo (máximo 5 palavras).
- description: 1 a 2 frases descrevendo o que a funcionalidade faz.
- business_rules: se não houver regras explícitas, infira as mais óbvias pelo contexto.
- dependencies: serviços ou módulos externos mencionados ou implícitos. Lista vazia se nenhum.

Diretrizes de riscos:
- Liste apenas riscos concretos e diretamente relacionados à feature.
- Prefira riscos específicos ao domínio a riscos genéricos.
- Classifique a criticidade com base no impacto financeiro, de segurança ou de experiência \
  do usuário.\
"""

_FULL_EXTRACT_HUMAN = "Descrição da funcionalidade:\n\n{raw_description}"

_REVIEW_SYSTEM = """\
Você é um analista sênior revisando uma extração e análise de feature.

Avalie se a análise está completa comparando-a com a descrição original. Verifique:
- Há regras de negócio implícitas no texto que não foram capturadas?
- Alguma dependência externa foi ignorada?
- Há riscos óbvios não identificados?
- A criticidade está correta para o domínio da feature?

Se aprovado: retorne approved=true e critique="".
Se houver lacunas: retorne approved=false, descreva o problema em critique \
e forneça a versão corrigida de todos os campos.\
"""

_REVIEW_HUMAN = """\
Descrição original:
{raw_description}

Análise atual:
{current_analysis}"""

_RISK_ONLY_SYSTEM = """\
Você é um especialista em qualidade de software. Analise a feature descrita e identifique \
todos os riscos relevantes, além de classificar sua criticidade.

Use os exemplos de referência abaixo para calibrar o formato, o nível de detalhe e os \
critérios de criticidade esperados:

{examples}

Diretrizes:
- Liste apenas riscos concretos e diretamente relacionados à feature.
- Classifique a criticidade como Baixa, Média, Alta ou Crítica com base no impacto \
  financeiro, de segurança ou de experiência do usuário.
- Prefira riscos específicos ao domínio da feature a riscos genéricos.\
"""

_RISK_ONLY_HUMAN = """\
Analise a feature abaixo e retorne os riscos identificados e a criticidade.

Feature: {feature_name}
Descrição: {description}
Regras de negócio:
{business_rules}
Dependências: {dependencies}\
"""


# ── Node ───────────────────────────────────────────────────────────────────

def agent_0_feature_analyzer_node(state: TestDocState) -> dict:
    llm = get_llm()
    description_for_rag = state.raw_description or state.description
    examples = get_similar_examples(description_for_rag, k=2)
    examples_text = "\n\n---\n\n".join(examples)

    if state.raw_description:
        extract_chain = (
            ChatPromptTemplate.from_messages([
                ("system", _FULL_EXTRACT_SYSTEM),
                ("human", _FULL_EXTRACT_HUMAN),
            ])
            | llm.with_structured_output(_FullAnalysis)
        )
        review_chain = (
            ChatPromptTemplate.from_messages([
                ("system", _REVIEW_SYSTEM),
                ("human", _REVIEW_HUMAN),
            ])
            | llm.with_structured_output(_FullAnalysisReview)
        )

        analysis: _FullAnalysis = extract_chain.invoke({
            "examples": examples_text,
            "raw_description": state.raw_description,
        })

        for _ in range(_MAX_REFLECTION_ITERATIONS):
            review: _FullAnalysisReview = review_chain.invoke({
                "raw_description": state.raw_description,
                "current_analysis": analysis.model_dump_json(indent=2),
            })

            if review.approved:
                break

            analysis = _FullAnalysis(
                feature_name=review.feature_name,
                description=review.description,
                business_rules=review.business_rules,
                dependencies=review.dependencies,
                identified_risks=review.identified_risks,
                criticality=review.criticality,
            )

        return {
            "feature_name": analysis.feature_name,
            "description": analysis.description,
            "business_rules": analysis.business_rules,
            "dependencies": analysis.dependencies,
            "retrieved_examples": examples,
            "identified_risks": analysis.identified_risks,
            "criticality": analysis.criticality,
        }

    risk_chain = (
        ChatPromptTemplate.from_messages([
            ("system", _RISK_ONLY_SYSTEM),
            ("human", _RISK_ONLY_HUMAN),
        ])
        | llm.with_structured_output(_RiskAnalysis)
    )

    result: _RiskAnalysis = risk_chain.invoke({
        "examples": examples_text,
        "feature_name": state.feature_name,
        "description": state.description,
        "business_rules": "\n".join(f"- {r}" for r in state.business_rules),
        "dependencies": ", ".join(state.dependencies),
    })

    return {
        "retrieved_examples": examples,
        "identified_risks": result.identified_risks,
        "criticality": result.criticality,
    }
