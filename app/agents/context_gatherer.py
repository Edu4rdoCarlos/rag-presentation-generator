"""
Context Gatherer — Iterative Question Generator (Human-in-the-Loop)

Each round receives the original description plus all previous Q&A pairs.
Returns either more questions (ready=False) or signals the context is
sufficient to proceed to analysis (ready=True).

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


class _GatherResult(BaseModel):
    ready: bool = Field(
        description=(
            "True se o contexto já é suficiente para planejar testes sem suposições críticas. "
            "False se ainda há lacunas importantes não cobertas pelas respostas anteriores."
        )
    )
    questions: list[_Question] = Field(
        default_factory=list,
        description="Lista de 2 a 4 perguntas quando ready=False. Vazia quando ready=True.",
    )


_SYSTEM_PROMPT = """\
Você é um engenheiro de QA sênior se preparando para analisar uma funcionalidade de software.

Avalie se o contexto disponível é suficiente para planejar uma estratégia de testes completa \
sem fazer suposições críticas.

Se o contexto for suficiente: retorne ready=true e questions=[].
Se ainda houver lacunas importantes: retorne ready=false e entre 2 e 4 perguntas novas.

Lacunas críticas são aquelas que, se assumidas incorretamente, levariam a uma estratégia errada:
- Regras de negócio e restrições não mencionadas
- Comportamentos esperados em cenários de erro
- Dependências externas que podem falhar
- Indicadores de criticidade e impacto para o usuário

Regras:
- Pergunte APENAS o que ainda NÃO foi respondido nas rodadas anteriores
- Não repita nem parafraseie perguntas já feitas
- Se as respostas cobriram os pontos críticos, declare ready=true
- Seja específico — mencione detalhes da feature nas perguntas
- Responda no mesmo idioma da descrição recebida
- Máximo de 4 perguntas por rodada
"""

_HUMAN_PROMPT = """\
Descrição da funcionalidade:

{raw_description}{context_block}"""


async def get_context_questions(
    raw_description: str,
    previous_qa: list[dict] | None = None,
) -> dict:
    previous_qa = previous_qa or []

    context_block = ""
    answered = [qa for qa in previous_qa if qa.get("answer", "").strip()]
    if answered:
        lines = "\n".join(f"P: {qa['question']}\nR: {qa['answer']}" for qa in answered)
        context_block = f"\n\nRespostas já fornecidas pelo desenvolvedor:\n{lines}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", _HUMAN_PROMPT),
    ])

    chain = prompt | get_llm().with_structured_output(_GatherResult)

    result: _GatherResult = await chain.ainvoke({
        "raw_description": raw_description,
        "context_block": context_block,
    })

    return {
        "ready": result.ready,
        "questions": [{"id": q.id, "question": q.question} for q in result.questions],
    }
