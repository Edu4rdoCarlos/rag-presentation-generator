from pydantic import BaseModel, Field
from typing import List, Optional


class TestDocState(BaseModel):
    """
    Shared state that flows immutably between graph nodes.
    Each agent receives the full state and returns a partial update dict.
    """

    # ── Input payload (populated at graph entry) ─────────────────────────────
    feature_name: str
    description: str
    business_rules: List[str]
    dependencies: List[str]

    # ── Agent 1 outputs: Risk Analyst (Planner + RAG) ─────────────────────────
    retrieved_examples: Optional[List[str]] = Field(default_factory=list)
    identified_risks: Optional[List[str]] = Field(default_factory=list)
    criticality: Optional[str] = None  # "Baixa" | "Média" | "Alta" | "Crítica"

    # ── Agent 2 outputs: Test Strategist (Tool Use) ───────────────────────────
    recommended_test_types: Optional[List[str]] = Field(default_factory=list)
    prioritized_scenarios: Optional[List[str]] = Field(default_factory=list)
    justification: Optional[str] = None

    # ── Agent 3 outputs: Documenter & Critic (Reflection) ────────────────────
    final_documentation: Optional[str] = None
    reflection_logs: Optional[List[str]] = Field(default_factory=list)

    # ── Internal orchestration metadata ──────────────────────────────────────
    reflection_iteration: int = 0
