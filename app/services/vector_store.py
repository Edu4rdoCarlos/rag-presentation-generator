"""
Vector store singleton built from few-shot training examples.

Loads app/data/train/few_shot_examples.json, converts each example into a
searchable text document, indexes with FAISS + OpenAI embeddings, and exposes
get_similar_examples() for use in Agent 1.
"""

import json
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

_EXAMPLES_PATH = Path(__file__).parent.parent / "data" / "train" / "few_shot_examples.json"


def _load_examples() -> list[dict]:
    with open(_EXAMPLES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _example_to_document(example: dict) -> Document:
    """Serialises one few-shot example into a plain-text Document for embedding."""
    rules = "\n".join(f"- {r}" for r in example.get("business_rules", []))
    risks = "\n".join(f"- {r}" for r in example.get("identified_risks", []))
    test_types = ", ".join(example.get("recommended_test_types", []))
    scenarios = "\n".join(f"- {s}" for s in example.get("test_scenarios", []))

    text = (
        f"Feature: {example['feature_name']}\n"
        f"Descrição: {example['description']}\n"
        f"Regras de negócio:\n{rules}\n"
        f"Riscos identificados:\n{risks}\n"
        f"Criticidade: {example['criticality']}\n"
        f"Tipos de teste: {test_types}\n"
        f"Cenários de teste:\n{scenarios}\n"
        f"Justificativa: {example.get('justification', '')}"
    )

    return Document(page_content=text, metadata={"feature_name": example["feature_name"]})


def _build_vector_store() -> FAISS:
    examples = _load_examples()
    documents = [_example_to_document(ex) for ex in examples]
    embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key)
    return FAISS.from_documents(documents, embeddings)


# Singleton — built once on first import, reused across all requests.
_vector_store: FAISS | None = None


def get_vector_store() -> FAISS:
    global _vector_store
    if _vector_store is None:
        _vector_store = _build_vector_store()
    return _vector_store


def get_similar_examples(description: str, k: int = 2) -> list[str]:
    """
    Returns the k most similar few-shot examples as formatted strings,
    ready to be injected into a prompt.
    """
    store = get_vector_store()
    docs = store.similarity_search(description, k=k)
    return [doc.page_content for doc in docs]
