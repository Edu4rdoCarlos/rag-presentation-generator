"""
LLM Provider Factory

Auto-detects the provider from available API keys, or uses LLM_PROVIDER env var.
Priority order (when LLM_PROVIDER is not set): openai → anthropic → nvidia → google

Usage:
    from app.core.llm_provider import get_llm, get_embeddings

    llm = get_llm()                  # default temperature=0
    llm = get_llm(temperature=0.7)
    embeddings = get_embeddings()
"""

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from app.core.config import settings


def _detect_provider() -> str:
    if settings.llm_provider:
        return settings.llm_provider.lower()

    if settings.openai_api_key:
        return "openai"
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.nvidia_api_key:
        return "nvidia"
    if settings.google_api_key:
        return "google"

    raise ValueError(
        "No LLM API key found. Set one of the following in your .env file:\n"
        "  OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, or NVIDIA_API_KEY\n"
        "Optionally, set LLM_PROVIDER to explicitly choose: openai | anthropic | google | nvidia"
    )


def get_llm(temperature: float = 0) -> BaseChatModel:
    """Returns the configured chat model based on available API keys."""
    provider = _detect_provider()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        model = settings.llm_model or settings.openai_model
        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
            temperature=temperature,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        model = settings.llm_model or settings.anthropic_model
        return ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
        )

    if provider == "nvidia":
        from langchain_nvidia_ai_endpoints import ChatNVIDIA

        model = settings.llm_model or settings.nvidia_model
        return ChatNVIDIA(
            model=model,
            api_key=settings.nvidia_api_key,
            temperature=temperature,
        )

    # default: google
    from langchain_google_genai import ChatGoogleGenerativeAI

    model = settings.llm_model or settings.google_model
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
    )


def get_embeddings() -> Embeddings:
    """
    Returns the embeddings model for the active provider.
    Note: Anthropic has no native embeddings — falls back to Google or OpenAI.
    """
    provider = _detect_provider()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(api_key=settings.openai_api_key)

    if provider == "nvidia":
        from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

        return NVIDIAEmbeddings(
            model="nvidia/nv-embedqa-e5-v5",
            api_key=settings.nvidia_api_key,
        )

    if provider == "anthropic":
        # Anthropic does not offer an embeddings API — use Google or OpenAI as fallback
        if settings.google_api_key:
            provider = "google"
        elif settings.openai_api_key:
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(api_key=settings.openai_api_key)
        else:
            raise ValueError(
                "Anthropic does not provide an embeddings API. "
                "Set GOOGLE_API_KEY or OPENAI_API_KEY to use as fallback for embeddings."
            )

    # google (default and anthropic fallback)
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=settings.google_api_key,
    )
