"""
Agent 2 — Test Strategist (Tool Use)

Responsibilities:
  - Consume identified_risks and criticality from Agent 1.
  - Use llm.bind_tools() to call deterministic Python functions that encode
    the Decision Matrix (feature characteristics → test types).
  - Produce the prioritized list of test scenarios with justification.

Writes to state:
  - recommended_test_types
  - prioritized_scenarios
  - justification
"""

from app.core.state import TestDocState


# ── Decision Matrix tools (stubs) ────────────────────────────────────────────
# Each function below will be bound to the LLM via llm.bind_tools().
# Implement the mapping logic inside each function.

def map_risks_to_test_types(risks: list[str], criticality: str) -> list[str]:
    """
    TODO: implement
    Maps identified risks + criticality to test type labels using the
    Decision Matrix defined in the project documentation (Section 14).
    Returns a deduplicated list such as ["unitário", "integração", "E2E"].
    """
    return []


def generate_prioritized_scenarios(
    feature_name: str,
    risks: list[str],
    test_types: list[str],
) -> list[str]:
    """
    TODO: implement
    Generates ordered test scenario descriptions covering happy-path,
    negative, and edge cases for each identified risk.
    """
    return []


def build_justification(
    feature_name: str,
    risks: list[str],
    test_types: list[str],
) -> str:
    """
    TODO: implement
    Produces a human-readable technical justification explaining why each
    recommended test type is required for this feature.
    """
    return ""


# ── LangGraph node ─────────────────────────────────────────────────────────

def agent_2_test_strategist_node(state: TestDocState) -> dict:
    """
    LangGraph node — receives full state, returns partial update dict.

    TODO: implement
      1. Instantiate LLM with tools bound:
           llm_with_tools = llm.bind_tools([
               map_risks_to_test_types,
               generate_prioritized_scenarios,
               build_justification,
           ])
      2. Invoke the LLM; handle tool_calls from its response.
      3. Execute the called tools to populate the fields below.
    """
    recommended_test_types: list[str] = []
    prioritized_scenarios: list[str] = []
    justification: str = ""

    return {
        "recommended_test_types": recommended_test_types,
        "prioritized_scenarios": prioritized_scenarios,
        "justification": justification,
    }
