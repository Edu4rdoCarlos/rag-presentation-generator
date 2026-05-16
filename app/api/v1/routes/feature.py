from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.state import TestDocState
from app.services.graph_service import testdoc_graph

router = APIRouter(prefix="/feature", tags=["feature"])


# ── Request / Response schemas ─────────────────────────────────────────────

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


# ── Endpoint ───────────────────────────────────────────────────────────────

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
        feature_name=final_state.feature_name,
        criticality=final_state.criticality,
        identified_risks=final_state.identified_risks or [],
        recommended_test_types=final_state.recommended_test_types or [],
        prioritized_scenarios=final_state.prioritized_scenarios or [],
        justification=final_state.justification,
        final_documentation=final_state.final_documentation,
        reflection_logs=final_state.reflection_logs or [],
        reflection_iteration=final_state.reflection_iteration,
    )
