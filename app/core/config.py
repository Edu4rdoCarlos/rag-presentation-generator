from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "development"
    app_debug: bool = True

    # ── Provider selection ─────────────────────────────────────────────────
    # Explicit provider override. When empty, auto-detected from available keys.
    # Valid values: "openai" | "anthropic" | "google" | "nvidia"
    llm_provider: str = ""
    # Override the model name for the active provider. When empty, uses provider default.
    llm_model: str = ""

    # ── Google / Gemini ────────────────────────────────────────────────────
    google_api_key: str = ""
    google_model: str = "gemini-2.5-flash"

    # ── OpenAI ────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ── Anthropic ─────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # ── NVIDIA NIM ────────────────────────────────────────────────────────
    nvidia_api_key: str = ""
    nvidia_model: str = "meta/llama-3.1-70b-instruct"

    # Reflection loop guard: max times Agent 3 can send back to Agent 2
    max_reflection_iterations: int = 3

    # Context gatherer: max total answered questions before forcing ready=true
    max_context_answers: int = 2


settings = Settings()
