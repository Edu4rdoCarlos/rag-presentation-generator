"""
Context Gatherer — Pre-analysis Question Generator

Responsibilities:
  - Receive a raw feature description.
  - Use an LLM to identify information gaps that would affect test coverage.
  - Return 2–4 targeted questions for the developer to answer.

Not a LangGraph node — invoked directly by the /feature/questions route.
"""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.llm_provider import get_llm


class _Question(BaseModel):
    id: str = Field(
        description="Identificador curto em snake_case, ex: 'rate_limit', 'failure_modes'."
    )
    question: str = Field(
        description="Pergunta específica e direta para o desenvolvedor."
    )


class _ContextQuestions(BaseModel):
    questions: list[_Question] = Field(
        description="Lista de 2 a 4 perguntas. Nunca mais do que 4."
    )


_SYSTEM_PROMPT = """\
Você é um engenheiro de QA sênior se preparando para analisar uma funcionalidade de software.

Sua tarefa é ler a descrição fornecida e identificar as lacunas de informação mais críticas \
que afetariam o planejamento de testes — coisas que, se assumidas incorretamente, levariam \
a uma estratégia de testes errada ou incompleta.

Gere entre 2 e 4 perguntas específicas que ajudem a entender:
- Regras de negócio e restrições não mencionadas explicitamente
- Dependências externas ou integrações que podem falhar
- Comportamentos esperados em cenários de erro
- Indicadores de criticidade e impacto para o usuário

Regras:
- Pergunte APENAS o que NÃO está claro na descrição
- Seja específico — mencione detalhes da feature nas perguntas
- Priorize o que mais mudaria a estratégia de testes
- Evite perguntas genéricas como "há mais requisitos?"
- Responda no mesmo idioma da descrição recebida
- Máximo de 4 perguntas
"""

_HUMAN_PROMPT = "Descrição da funcionalidade:\n\n{raw_description}"


async def get_context_questions(raw_description: str) -> list[dict]:
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", _HUMAN_PROMPT),
    ])

    chain = prompt | get_llm().with_structured_output(_ContextQuestions)

    result: _ContextQuestions = await chain.ainvoke({"raw_description": raw_description})

    return [{"id": q.id, "question": q.question} for q in result.questions]
