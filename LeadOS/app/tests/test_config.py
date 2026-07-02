from app.core.config import settings


def test_settings_defaults():
    assert settings.llm_provider == "openai"
    assert settings.max_search_results == 25
    assert settings.scrape_delay == 0
    assert settings.match_threshold == 50


def test_settings_db_url():
    url = settings.database_url.replace("\\", "/")
    assert url.endswith("app/data/ggh.db")
