"""
Context Gatherer — Iterative Question Generator (Human-in-the-Loop)

Each round receives the original description plus all previous Q&A pairs.
Returns either more questions (ready=False) or signals the context is
sufficient to proceed to analysis (ready=True).

Not a LangGraph node — invoked directly by the /feature/questions route.
"""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.config import settings
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

Avalie se o contexto disponível é suficiente para planejar uma estratégia de testes sem \
suposições bloqueantes.

Se o contexto for suficiente: retorne ready=true e questions=[].
Se houver lacunas que tornam o planejamento inviável: retorne ready=false e no máximo 2 perguntas.

Regras:
- Prefira ready=true quando em dúvida — o agente de análise consegue inferir detalhes menores.
- Só pergunte sobre lacunas BLOQUEANTES: sem a resposta, é impossível escrever qualquer teste.
- Se já houve pelo menos uma rodada de respostas e os pontos críticos foram abordados: ready=true.
- Nunca repita perguntas já respondidas.
- Responda no mesmo idioma da descrição recebida.
- Máximo de 2 perguntas por rodada.
"""

_HUMAN_PROMPT = """\
Descrição da funcionalidade:

{raw_description}{context_block}"""


async def get_context_questions(
    raw_description: str,
    previous_qa: list[dict] | None = None,
) -> dict:
    previous_qa = previous_qa or []

    MAX_ANSWERS = settings.max_context_answers

    context_block = ""
    answered = [qa for qa in previous_qa if qa.get("answer", "").strip()]
    if len(answered) >= MAX_ANSWERS:
        return {"ready": True, "questions": []}

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
