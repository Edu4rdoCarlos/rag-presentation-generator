from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "development"
    app_debug: bool = True

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Reflection loop guard: max times Agent 3 can send back to Agent 2
    max_reflection_iterations: int = 3


settings = Settings()
