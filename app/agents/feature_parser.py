"""
Agent 0 — Feature Parser

Responsibilities:
  - Receive a free-text description of a feature (raw_description).
  - Use an LLM to extract structured fields:
      feature_name, description, business_rules, dependencies.
  - Populate the state so Agent 1 can proceed normally.

Writes to state:
  - feature_name
  - description
  - business_rules
  - dependencies
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.state import TestDocState


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


_SYSTEM_PROMPT = """\
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

_HUMAN_PROMPT = "Descrição da funcionalidade:\n\n{raw_description}"


def agent_0_feature_parser_node(state: TestDocState) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", _HUMAN_PROMPT),
    ])

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

    chain = prompt | llm.with_structured_output(_ParsedFeature)

    result: _ParsedFeature = chain.invoke({
        "raw_description": state.raw_description,
    })

    return {
        "feature_name": result.feature_name,
        "description": result.description,
        "business_rules": result.business_rules,
        "dependencies": result.dependencies,
    }
