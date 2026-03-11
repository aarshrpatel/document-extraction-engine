from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Anthropic
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_max_tokens: int = 4096

    # Azure Document Intelligence (optional - falls back to Tesseract)
    azure_doc_intel_endpoint: str = ""
    azure_doc_intel_key: str = ""

    # Database
    database_url: str = "postgresql://extraction:extraction@localhost:5432/extraction_engine"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    log_level: str = "INFO"
    environment: str = "development"
    max_file_size_mb: int = 50
    max_extraction_retries: int = 2


def get_settings() -> Settings:
    return Settings()
