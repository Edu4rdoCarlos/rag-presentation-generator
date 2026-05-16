"""
LangGraph orchestration — builds, compiles and exposes the TestDoc workflow.

Graph topology:
  analista_riscos → estrategista_testes → documentador_critico
                           ↑                       │
                           └── REVER_ESTRATEGIA ───┘
                                   (or END)
"""

from langgraph.graph import END, StateGraph

from app.agents.documenter_critic import agent_3_documenter_reflection_node
from app.agents.risk_analyst import agent_1_risk_analyst_node
from app.agents.test_strategist import agent_2_test_strategist_node
from app.core.config import settings
from app.core.state import TestDocState

# ── Node names (string constants avoid typos across the codebase) ─────────

NODE_RISK_ANALYST = "analista_riscos"
NODE_TEST_STRATEGIST = "estrategista_testes"
NODE_DOCUMENTER_CRITIC = "documentador_critico"

_REVISION_SIGNAL = "REVER_ESTRATEGIA"


# ── Conditional edge router ────────────────────────────────────────────────

def _evaluate_reflection_path(state: TestDocState) -> str:
    """
    Router called after Agent 3 runs.

    - Returns NODE_TEST_STRATEGIST  → triggers another strategy cycle.
    - Returns END                   → workflow finishes.

    Guards against infinite loops using reflection_iteration.
    """
    if not state.reflection_logs:
        return END

    last_log = state.reflection_logs[-1]
    iteration_limit_reached = (
        state.reflection_iteration >= settings.max_reflection_iterations
    )

    if _REVISION_SIGNAL in last_log and not iteration_limit_reached:
        return NODE_TEST_STRATEGIST

    return END


# ── Graph factory ──────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Constructs and returns the compiled LangGraph application."""

    workflow = StateGraph(TestDocState)

    # Register nodes
    workflow.add_node(NODE_RISK_ANALYST, agent_1_risk_analyst_node)
    workflow.add_node(NODE_TEST_STRATEGIST, agent_2_test_strategist_node)
    workflow.add_node(NODE_DOCUMENTER_CRITIC, agent_3_documenter_reflection_node)

    # Entry point
    workflow.set_entry_point(NODE_RISK_ANALYST)

    # Sequential mandatory edges
    workflow.add_edge(NODE_RISK_ANALYST, NODE_TEST_STRATEGIST)
    workflow.add_edge(NODE_TEST_STRATEGIST, NODE_DOCUMENTER_CRITIC)

    # Conditional reflection loop from Agent 3
    workflow.add_conditional_edges(
        NODE_DOCUMENTER_CRITIC,
        _evaluate_reflection_path,
        {
            NODE_TEST_STRATEGIST: NODE_TEST_STRATEGIST,
            END: END,
        },
    )

    return workflow.compile()


# ── Module-level compiled graph (singleton) ────────────────────────────────
# Import this instance wherever you need to invoke the workflow.
testdoc_graph = build_graph()
