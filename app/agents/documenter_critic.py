"""
Agent 3 — Documenter & Critic (Reflection)

Responsibilities:
  - Compile all cumulative state data into the structured final document.
  - Run a self-review pass (Reflection Pattern) to check QA constraints:
      · No obvious risk omitted.
      · No irrelevant test type suggested.
      · Criticality is coherent with the risks.
      · Scenarios cover positive, negative, and edge cases.
      · Every test type has a justification.
  - If the self-review finds a critical flaw, append "REVER_ESTRATEGIA" to
    reflection_logs so the router sends flow back to Agent 2.
  - Otherwise append "APROVADO" and let the flow reach END.

Writes to state:
  - final_documentation
  - reflection_logs
  - reflection_iteration  (incremented each cycle)
"""

from app.core.state import TestDocState

_REVISION_SIGNAL = "REVER_ESTRATEGIA"
_APPROVAL_SIGNAL = "APROVADO"


def _format_documentation(state: TestDocState) -> str:
    """
    TODO: implement
    Assembles all state fields into the standardised Markdown/text report
    defined in Section 9 of the project documentation.
    """
    return ""


def _run_reflection(state: TestDocState, draft: str) -> str:
    """
    TODO: implement
    Invokes a critic LLM prompt against 'draft'.
    Returns either _REVISION_SIGNAL or _APPROVAL_SIGNAL.
    Use a ChatPromptTemplate with conditional edges instructions.
    """
    return _APPROVAL_SIGNAL


def agent_3_documenter_reflection_node(state: TestDocState) -> dict:
    """
    LangGraph node — receives full state, returns partial update dict.

    TODO: implement
      1. Call _format_documentation() to produce the draft.
      2. Call _run_reflection() to evaluate the draft.
      3. Append the signal to reflection_logs.
      4. Increment reflection_iteration.
      5. Return updated fields.
    """
    draft = _format_documentation(state)
    signal = _run_reflection(state, draft)

    updated_logs = list(state.reflection_logs or []) + [signal]

    return {
        "final_documentation": draft,
        "reflection_logs": updated_logs,
        "reflection_iteration": state.reflection_iteration + 1,
    }
