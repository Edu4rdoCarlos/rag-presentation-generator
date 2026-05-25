from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.context_gatherer import get_context_questions
from app.core.state import TestDocState
from app.services.graph_service import testdoc_graph

router = APIRouter(prefix="/feature", tags=["feature"])


# ── Request / Response schemas ─────────────────────────────────────────────

class PreviousQA(BaseModel):
    question: str
    answer: str


class ContextQuestionsRequest(BaseModel):
    raw_text: str = Field(..., examples=["Tela de login com autenticação em dois fatores."])
    previous_qa: list[PreviousQA] = Field(default_factory=list)


class Question(BaseModel):
    id: str
    question: str


class ContextQuestionsResponse(BaseModel):
    ready: bool
    questions: list[Question]


class FeatureAnalyzeRequest(BaseModel):
    feature_name: str = Field(..., examples=["Checkout com cupom"])
    description: str = Field(..., examples=["Aplica cupons de desconto durante o checkout."])
    business_rules: list[str] = Field(
        ...,
        examples=[["Cupom não pode ser usado duas vezes pelo mesmo usuário."]],
    )
    dependencies: list[str] = Field(
        default_factory=list,
        examples=[["PaymentService", "CouponService"]],
    )


class FeatureAnalyzeTextRequest(BaseModel):
    raw_text: str = Field(
        ...,
        examples=["Fiz uma tela de cadastro onde o usuário informa nome, e-mail e senha. O e-mail precisa ser único e a senha ter 8 caracteres no mínimo."],
    )


class FeatureAnalyzeResponse(BaseModel):
    feature_name: str
    criticality: str | None
    identified_risks: list[str]
    recommended_test_types: list[str]
    prioritized_scenarios: list[str]
    justification: str | None
    final_documentation: str | None
    reflection_logs: list[str]
    reflection_iteration: int


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post(
    "/questions",
    response_model=ContextQuestionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate clarifying questions for a feature description",
)
async def feature_questions(payload: ContextQuestionsRequest) -> ContextQuestionsResponse:
    try:
        result = await get_context_questions(
            payload.raw_text,
            previous_qa=[qa.model_dump() for qa in payload.previous_qa],
        )
        return ContextQuestionsResponse(
            ready=result["ready"],
            questions=[Question(**q) for q in result["questions"]],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question generation failed: {exc}",
        ) from exc


async def _run_graph(initial_state: TestDocState) -> FeatureAnalyzeResponse:
    try:
        s = await testdoc_graph.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph execution failed: {exc}",
        ) from exc

    return FeatureAnalyzeResponse(
        feature_name=s.get("feature_name", ""),
        criticality=s.get("criticality"),
        identified_risks=s.get("identified_risks", []),
        recommended_test_types=s.get("recommended_test_types", []),
        prioritized_scenarios=s.get("prioritized_scenarios", []),
        justification=s.get("justification"),
        final_documentation=s.get("final_documentation"),
        reflection_logs=s.get("reflection_logs", []),
        reflection_iteration=s.get("reflection_iteration", 0),
    )


@router.post(
    "/analyze",
    response_model=FeatureAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a structured feature and generate test documentation",
)
async def analyze_feature(payload: FeatureAnalyzeRequest) -> FeatureAnalyzeResponse:
    return await _run_graph(TestDocState(
        feature_name=payload.feature_name,
        description=payload.description,
        business_rules=payload.business_rules,
        dependencies=payload.dependencies,
    ))


@router.post(
    "/analyze/text",
    response_model=FeatureAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a plain-text feature description and generate test documentation",
)
async def analyze_feature_text(payload: FeatureAnalyzeTextRequest) -> FeatureAnalyzeResponse:
    return await _run_graph(TestDocState(raw_description=payload.raw_text))
