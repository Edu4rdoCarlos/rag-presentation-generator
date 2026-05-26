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
    is_feature: bool = Field(
        description=(
            "True se a descrição parece ser uma funcionalidade de software que pode ser testada. "
            "False se o conteúdo não tem relação com desenvolvimento de software "
            "(ex: receitas, piadas, perguntas gerais, textos aleatórios)."
        )
    )
    rejection_message: str = Field(
        default="",
        description=(
            "Mensagem explicando por que o conteúdo não foi reconhecido como uma funcionalidade "
            "de software. Preenchida apenas quando is_feature=False. "
            "Responda no mesmo idioma da descrição recebida."
        ),
    )
    ready: bool = Field(
        description=(
            "True se o contexto já é suficiente para planejar testes sem suposições críticas. "
            "False se ainda há lacunas importantes. Irrelevante quando is_feature=False."
        )
    )
    questions: list[_Question] = Field(
        default_factory=list,
        description="Lista de até 2 perguntas quando ready=False. Vazia quando ready=True ou is_feature=False.",
    )


_SYSTEM_PROMPT = """\
Você é um engenheiro de QA sênior se preparando para analisar uma funcionalidade de software.

PRIMEIRO: verifique se a descrição recebida é de fato uma funcionalidade de software que \
pode ser testada (autenticação, CRUD, fluxo de pagamento, API, relatório, etc.).

Se NÃO for uma funcionalidade de software — incluindo saudações ("ola", "oi", "tudo bem"), \
cumprimentos, mensagens curtas de conversa, receitas, piadas, texto aleatório ou qualquer \
pergunta não relacionada a software — retorne is_feature=false, rejection_message vazio, \
ready=false e questions=[].

Se FOR uma funcionalidade de software:
- O padrão é ready=true. Declare ready=true a menos que haja uma lacuna ABSOLUTAMENTE bloqueante.
- Uma lacuna é bloqueante apenas se, sem a resposta, for literalmente impossível escrever \
  qualquer cenário de teste — nem um único. Exemplos: não sabe se é uma API REST ou uma tela \
  (muda completamente o que testar), não sabe se a feature existe para um único usuário ou \
  multi-tenant (muda o escopo de isolamento).
- Dúvidas sobre regras de negócio menores, limites de campos, mensagens de erro, timeouts, \
  paginação, etc. NÃO são bloqueantes — o agente de análise infere esses detalhes.
- Se houver lacuna realmente bloqueante: retorne ready=false e no máximo 1-2 perguntas.
- Se já houve pelo menos uma rodada de respostas anteriores: declare ready=true obrigatoriamente.
- Nunca repita perguntas já respondidas.
- Responda no mesmo idioma da descrição recebida.
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
        "is_feature": result.is_feature,
        "rejection_message": result.rejection_message,
        "ready": result.ready,
        "questions": [{"id": q.id, "question": q.question} for q in result.questions],
    }
