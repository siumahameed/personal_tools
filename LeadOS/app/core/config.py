from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="app/data/.env", env_file_encoding="utf-8")

    # LLM
    openai_api_key: str = ""
    openai_base_url: str = ""
    anthropic_api_key: str = ""
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"

    # Database
    database_url: str = "sqlite+aiosqlite:///app/data/ggh.db"

    # Paths
    data_dir: Path = Path("outputs")
    config_dir: Path = Path("app/discovery")

    # Search backends (cascading: serpapi -> google -> ddgs)
    serpapi_api_key: str = ""
    google_api_key: str = ""
    google_cse_id: str = ""
    max_search_results: int = 25

    # Pipeline
    scrape_delay: float = 0
    match_threshold: int = 50
    search_recency: str = ""  # d=day, w=week, m=month, 3m=3months, ""=any


settings = Settings()
