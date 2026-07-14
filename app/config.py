from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql://po_user:po_pass@localhost:5432/po_compliance"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "po_policies"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"


settings = Settings()