import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from app.core.config import settings


sync_db_url = settings.database_url.replace("+aiosqlite", "")
sync_engine = create_engine(sync_db_url, echo=False)
engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"timeout": 30},
    pool_size=10,
    max_overflow=20,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Global lock to serialize DB writes across concurrent agents (SQLite limitation)
db_write_lock = asyncio.Lock()


class Base(DeclarativeBase):
    pass


def init_db():
    from app.core.models import UserProfile, Job, Prospect, OutreachDraft, ScrapeSession, ResearchLead
    Base.metadata.create_all(sync_engine)
    _migrate_research_leads()


def _migrate_research_leads():
    """Add new columns to research_leads if they don't exist (SQLite-safe)."""
    from sqlalchemy import text
    new_columns = {
        "current_fields":     "JSON",
        "past_fields":        "JSON",
        "all_emails":         "JSON",
        "contact_phone":      "TEXT DEFAULT ''",
        "office_address":     "TEXT DEFAULT ''",
        "personal_website":   "TEXT DEFAULT ''",
        "twitter_url":        "TEXT DEFAULT ''",
        "github_url":         "TEXT DEFAULT ''",
        "google_scholar_url": "TEXT DEFAULT ''",
        "orcid_url":          "TEXT DEFAULT ''",
        "researchgate_url":   "TEXT DEFAULT ''",
    }
    with sync_engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(research_leads)"))}
        for col, ddl in new_columns.items():
            if col not in existing:
                try:
                    conn.execute(text(f"ALTER TABLE research_leads ADD COLUMN {col} {ddl}"))
                    conn.commit()
                except Exception:
                    pass


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def close_db():
    await engine.dispose()
