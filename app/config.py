from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ai-business-process-automation"
    app_env: str = "development"
    database_url: str = "sqlite:///./abpa.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    llm_provider: str = "mock"
    llm_api_base: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    erp_base_url: str = "http://localhost:9001"
    crm_base_url: str = "http://localhost:9002"
    enable_pii_redaction: bool = True
    audit_log_path: str = "./logs/audit.jsonl"


@lru_cache
def get_settings() -> Settings:
    return Settings()
