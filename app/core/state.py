from pydantic import BaseModel, Field


class TestDocState(BaseModel):
    """
    Shared state that flows immutably between graph nodes.
    Each agent receives the full state and returns a partial update dict.
    """

    # ── Raw text input (populated when user sends plain text instead of JSON) ──
    raw_description: str | None = None

    # ── Input payload (populated at graph entry or by parser agent) ───────────
    feature_name: str = ""
    description: str = ""
    business_rules: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)

    # ── Agent 1 outputs: Risk Analyst (Planner + RAG) ─────────────────────────
    retrieved_examples: list[str] = Field(default_factory=list)
    identified_risks: list[str] = Field(default_factory=list)
    criticality: str | None = None  # "Baixa" | "Média" | "Alta" | "Crítica"

    # ── Agent 2 outputs: Test Strategist (Tool Use) ───────────────────────────
    recommended_test_types: list[str] = Field(default_factory=list)
    prioritized_scenarios: list[str] = Field(default_factory=list)
    justification: str | None = None

    # ── Agent 3 outputs: Documenter & Critic (Reflection) ────────────────────
    final_documentation: str | None = None
    reflection_logs: list[str] = Field(default_factory=list)

    # ── Internal orchestration metadata ──────────────────────────────────────
    reflection_iteration: int = 0
