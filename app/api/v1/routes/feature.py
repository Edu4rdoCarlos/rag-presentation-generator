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


@router.post(
    "/analyze",
    response_model=FeatureAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a feature and generate test documentation",
)
async def analyze_feature(payload: FeatureAnalyzeRequest) -> FeatureAnalyzeResponse:
    """
    Receives a feature description and runs it through the 3-agent LangGraph
    workflow to produce structured test documentation.
    """
    initial_state = TestDocState(
        feature_name=payload.feature_name,
        description=payload.description,
        business_rules=payload.business_rules,
        dependencies=payload.dependencies,
    )

    try:
        final_state: TestDocState = await testdoc_graph.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph execution failed: {exc}",
        ) from exc

    return FeatureAnalyzeResponse(
        feature_name=final_state["feature_name"],
        criticality=final_state.get("criticality"),
        identified_risks=final_state.get("identified_risks", []),
        recommended_test_types=final_state.get("recommended_test_types", []),
        prioritized_scenarios=final_state.get("prioritized_scenarios", []),
        justification=final_state.get("justification"),
        final_documentation=final_state.get("final_documentation"),
        reflection_logs=final_state.get("reflection_logs", []),
        reflection_iteration=final_state.get("reflection_iteration", 0),
    )


@router.post(
    "/analyze/text",
    response_model=FeatureAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a feature from plain text and generate test documentation",
)
async def analyze_feature_text(payload: FeatureAnalyzeTextRequest) -> FeatureAnalyzeResponse:
    """
    Receives a plain-text description of a feature, parses it into structured
    fields via Agent 0, then runs the full 3-agent pipeline.
    """
    initial_state = TestDocState(raw_description=payload.raw_text)

    try:
        final_state: TestDocState = await testdoc_graph.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph execution failed: {exc}",
        ) from exc

    return FeatureAnalyzeResponse(
        feature_name=final_state["feature_name"],
        criticality=final_state.get("criticality"),
        identified_risks=final_state.get("identified_risks", []),
        recommended_test_types=final_state.get("recommended_test_types", []),
        prioritized_scenarios=final_state.get("prioritized_scenarios", []),
        justification=final_state.get("justification"),
        final_documentation=final_state.get("final_documentation"),
        reflection_logs=final_state.get("reflection_logs", []),
        reflection_iteration=final_state.get("reflection_iteration", 0),
    )
