from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


class Settings(BaseSettings):
    # Application
    app_env: str = "development"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Database
    database_url: str = "sqlite:///./agentic_fintech.db"

    # LLM Providers
    openai_api_key: str = ""
    groq_api_key: str = ""

    # LLM Settings
    primary_llm_model: str = "gpt-4o-mini"
    fallback_llm_model: str = "llama-3.1-8b-instant"
    llm_max_tokens: int = 1500
    enable_llm_agents: bool = False

    # LangSmith tracing (optional)
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "agentic-fintech-platform"

    # App settings
    seed_on_startup: bool = True
    # Chroma ingest on boot can OOM small Railway containers — off by default
    ingest_policies_on_startup: bool = False
    audit_export_dir: str = "./audit_exports"
    cors_origins: str = ",".join(DEFAULT_CORS_ORIGINS)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
