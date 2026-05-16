"""
Agent 1 — Risk Analyst (Planner + RAG)

Responsibilities:
  - Query the vector store to retrieve annotated few-shot examples of
    similar features (RAG).
  - Build a dynamic Few-shot Prompting context from retrieved examples.
  - Identify business/technical risks for the incoming feature.
  - Classify feature criticality: Baixa | Média | Alta | Crítica.

Writes to state:
  - retrieved_examples
  - identified_risks
  - criticality
"""

from app.core.state import TestDocState


def agent_1_risk_analyst_node(state: TestDocState) -> dict:
    """
    LangGraph node — receives full state, returns partial update dict.

    TODO: implement
      1. Build retriever from vector store (VectorStoreRetriever).
      2. Retrieve similar feature examples using state.description.
      3. Assemble ChatPromptTemplate with few-shot examples + feature input.
      4. Invoke LLM chain to produce identified_risks and criticality.
      5. Return the fields below populated.
    """
    retrieved_examples: list[str] = []
    identified_risks: list[str] = []
    criticality: str | None = None

    return {
        "retrieved_examples": retrieved_examples,
        "identified_risks": identified_risks,
        "criticality": criticality,
    }
