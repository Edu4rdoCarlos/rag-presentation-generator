"""
Agent 1 — Risk Analyst (Planner + RAG)

Responsibilities:
  - Query the vector store to retrieve annotated few-shot examples of
    similar features (RAG).
  - Build a dynamic Few-shot Prompting context from retrieved examples.
  - Identify business/technical risks for the incoming feature.
  - Classify feature criticality: Baixa | Média | Alta | Crítica.

Writes to state:
  - retrieved_examples
  - identified_risks
  - criticality
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.state import TestDocState
from app.services.vector_store import get_similar_examples


class _RiskAnalysisOutput(BaseModel):
    identified_risks: list[str] = Field(
        description="Lista de riscos funcionais, técnicos e de negócio identificados para a feature."
    )
    criticality: str = Field(
        description="Criticidade da feature: Baixa, Média, Alta ou Crítica."
    )


_SYSTEM_PROMPT = """\
Você é um especialista em qualidade de software. Sua tarefa é analisar a descrição \
de uma feature e identificar todos os riscos relevantes, além de classificar sua criticidade.

Use os exemplos de referência abaixo para calibrar o formato, o nível de detalhe e os \
critérios de criticidade esperados:

{examples}

Diretrizes:
- Liste apenas riscos concretos e diretamente relacionados à feature.
- Classifique a criticidade como Baixa, Média, Alta ou Crítica com base no impacto \
  financeiro, de segurança ou de experiência do usuário.
- Prefira riscos específicos ao domínio da feature a riscos genéricos.\
"""

_HUMAN_PROMPT = """\
Analise a feature abaixo e retorne os riscos identificados e a criticidade.

Feature: {feature_name}
Descrição: {description}
Regras de negócio:
{business_rules}
Dependências: {dependencies}\
"""


def agent_1_risk_analyst_node(state: TestDocState) -> dict:
    examples = get_similar_examples(state.description, k=2)
    examples_text = "\n\n---\n\n".join(examples)

    rules_text = "\n".join(f"- {r}" for r in state.business_rules)
    deps_text = ", ".join(state.dependencies)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", _HUMAN_PROMPT),
    ])

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

    chain = prompt | llm.with_structured_output(_RiskAnalysisOutput)

    result: _RiskAnalysisOutput = chain.invoke({
        "examples": examples_text,
        "feature_name": state.feature_name,
        "description": state.description,
        "business_rules": rules_text,
        "dependencies": deps_text,
    })

    return {
        "retrieved_examples": examples,
        "identified_risks": result.identified_risks,
        "criticality": result.criticality,
    }
