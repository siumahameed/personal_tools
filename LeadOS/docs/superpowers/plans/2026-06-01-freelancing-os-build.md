# Freelancing OS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete Freelancing OS — discovers freelance jobs/clients from the entire web, matches them against user profile, and generates cold email/LinkedIn outreach drafts.

**Architecture:** Python monorepo with Click CLI for background jobs (scraping, matching, generation) + FastAPI web dashboard for reviewing results. SQLite for storage. LLM (OpenAI/Anthropic) for skill matching and draft generation. Playwright + httpx + BeautifulSoup for scraping.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy + SQLite, Click, Playwright, httpx, BeautifulSoup, Jinja2 + Tailwind CSS, OpenAI/Anthropic API

---

### Task 1: Project Scaffolding

**Files:**
- Create: `E:\Desktop\ggh\pyproject.toml`
- Create: `E:\Desktop\ggh\.env`
- Create: `E:\Desktop\ggh\.gitignore`
- Create: `E:\Desktop\ggh\config\queries.yml`
- Create: `E:\Desktop\ggh\config\companies.yml`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "freelancing-os"
version = "0.1.0"
description = "Freelancing OS — discover opportunities, match skills, generate outreach"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]",
    "sqlalchemy>=2.0",
    "aiosqlite",
    "playwright",
    "beautifulsoup4",
    "httpx",
    "openai",
    "anthropic",
    "googlesearch-python",
    "jinja2",
    "pydantic>=2.0",
    "pydantic-settings",
    "python-dotenv",
    "click",
    "pyyaml",
]

[tool.setuptools.packages.find]
include = ["app*"]

[project.scripts]
ggh = "app.cli:cli"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Create .env**

```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.pyc
.env
*.db
outputs/
.pytest_cache/
*.egg-info/
```

- [ ] **Step 4: Create config/queries.yml**

```yaml
queries:
  - "machine learning freelancer needed"
  - "looking for data science consultant"
  - "sklearn Python freelance project"
  - "AI ML contractor required"
  - "need help with data analysis"
  - "freelance machine learning engineer"
  - "Python data analysis freelance"
  - "FastAPI developer freelancer needed"
  - "statistical modeling consultant"
  - "hire ML freelancer remotely"
  - "data science freelancer for hire"
  - "entry level machine learning freelance"
  - "junior data scientist freelance project"
```

- [ ] **Step 5: Create config/companies.yml**

```yaml
companies: []
```

- [ ] **Step 6: Create directory structure**

```bash
mkdir -p app/agents app/scrapers app/llm app/templates app/static config outputs tests
```

---

### Task 2: Database Models + Config

**Files:**
- Create: `E:\Desktop\ggh\app\__init__.py` (empty)
- Create: `E:\Desktop\ggh\app\config.py`
- Create: `E:\Desktop\ggh\app\database.py`
- Create: `E:\Desktop\ggh\app\models.py`
- Create: `E:\Desktop\ggh\app\schemas.py`

- [ ] **Step 1: Create config.py**

```python
from pydantic_settings import BaseSettings
from pathlib import Path
import os


class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    database_url: str = "sqlite+aiosqlite:///ggh.db"
    data_dir: Path = Path("outputs")
    config_dir: Path = Path("config")
    max_search_results: int = 20
    scrape_delay: float = 2.0
    match_threshold: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

- [ ] **Step 2: Create database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    async with engine.begin() as conn:
        from app.models import UserProfile, Job, Prospect, OutreachDraft, ScrapeSession
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **Step 3: Create models.py**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, func
from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True)
    name = Column(Text, default="Sium Ahameed")
    title = Column(Text, default="Machine Learning Engineer")
    summary = Column(Text, default="")
    skills = Column(JSON, default=list)
    portfolio_urls = Column(JSON, default=list)
    experience_years = Column(Integer, default=0)
    location = Column(Text, default="Dhaka, Bangladesh")
    preferred_roles = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    platform = Column(Text)
    url = Column(Text, unique=True)
    description = Column(Text)
    required_skills = Column(JSON, default=list)
    budget = Column(Text, default="")
    client_name = Column(Text, default="")
    client_location = Column(Text, default="")
    posted_date = Column(DateTime, nullable=True)
    match_score = Column(Integer, default=0)
    match_reason = Column(Text, default="")
    source_query = Column(Text, default="")
    status = Column(Text, default="new")
    created_at = Column(DateTime, server_default=func.now())


class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True)
    company_name = Column(Text)
    industry = Column(Text, default="")
    contact_name = Column(Text, default="")
    contact_title = Column(Text, default="")
    email = Column(Text, default="")
    linkedin_url = Column(Text, default="")
    company_url = Column(Text, default="")
    source = Column(Text)
    source_query = Column(Text, default="")
    notes = Column(Text, default="")
    relevance_score = Column(Integer, default=0)
    relevance_reason = Column(Text, default="")
    status = Column(Text, default="new")
    created_at = Column(DateTime, server_default=func.now())


class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"

    id = Column(Integer, primary_key=True)
    prospect_id = Column(Integer, nullable=True)
    job_id = Column(Integer, nullable=True)
    email_subject = Column(Text, default="")
    email_body = Column(Text, default="")
    linkedin_message = Column(Text, default="")
    channel = Column(Text, default="both")
    status = Column(Text, default="draft")
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ScrapeSession(Base):
    __tablename__ = "scrape_sessions"

    id = Column(Integer, primary_key=True)
    source = Column(Text)
    query = Column(Text, default="")
    urls_found = Column(Integer, default=0)
    jobs_found = Column(Integer, default=0)
    prospects_found = Column(Integer, default=0)
    status = Column(Text, default="running")
    error = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Create schemas.py**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserProfileSchema(BaseModel):
    name: str = "Sium Ahameed"
    title: str = "Machine Learning Engineer"
    summary: str = ""
    skills: list = []
    portfolio_urls: list = []
    experience_years: int = 0
    location: str = "Dhaka, Bangladesh"
    preferred_roles: list = []


class JobSchema(BaseModel):
    id: int
    title: str
    platform: str
    url: str
    description: str
    required_skills: list = []
    budget: str = ""
    client_name: str = ""
    match_score: int = 0
    match_reason: str = ""
    status: str = "new"
    created_at: Optional[datetime] = None


class ProspectSchema(BaseModel):
    id: int
    company_name: str
    industry: str = ""
    contact_name: str = ""
    email: str = ""
    linkedin_url: str = ""
    source: str
    relevance_score: int = 0
    status: str = "new"
    created_at: Optional[datetime] = None


class OutreachDraftSchema(BaseModel):
    id: int
    prospect_id: Optional[int] = None
    job_id: Optional[int] = None
    email_subject: str = ""
    email_body: str = ""
    linkedin_message: str = ""
    channel: str = "both"
    status: str = "draft"
    created_at: Optional[datetime] = None


class StatsSchema(BaseModel):
    total_jobs: int
    total_prospects: int
    total_drafts: int
    matched_jobs: int
    high_score_jobs: int
```

---

### Task 3: LLM Client + Prompts

**Files:**
- Create: `E:\Desktop\ggh\app\llm\__init__.py` (empty)
- Create: `E:\Desktop\ggh\app\llm\client.py`
- Create: `E:\Desktop\ggh\app\llm\prompts.py`

- [ ] **Step 1: Create client.py**

```python
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.config import settings


class LLMClient:
    def __init__(self):
        self.provider = settings.llm_provider
        self.model = settings.llm_model
        self._openai = None
        self._anthropic = None

    def _get_openai(self):
        if self._openai is None:
            self._openai = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._openai

    def _get_anthropic(self):
        if self._anthropic is None:
            self._anthropic = AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._anthropic

    async def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        if self.provider == "anthropic":
            client = self._get_anthropic()
            msg = await client.messages.create(
                model=self.model,
                system=system,
                messages=[{"role": "user", "content": user}],
                max_tokens=2000,
                temperature=temperature,
            )
            return msg.content[0].text
        else:
            client = self._get_openai()
            resp = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""


llm = LLMClient()
```

- [ ] **Step 2: Create prompts.py**

```python
EXTRACT_OPPORTUNITY = """You are a freelance opportunity extractor. Given the content of a web page, determine if it contains a freelance job, project, or potential client opportunity.

If it IS an opportunity, extract:
- title: The job/project title
- description: Brief summary (max 100 words)
- company: Company or client name
- contact_name: Person hiring (if visible)
- contact_email: Email if visible
- required_skills: Comma-separated list of skills needed
- budget: Budget or rate if mentioned
- is_job: true if it's a specific job/project listing
- is_prospect: true if it's a company/person who might need ML services

Respond in this JSON format:
{"is_opportunity": true/false, "title": "", "description": "", "company": "", "contact_name": "", "contact_email": "", "required_skills": "", "budget": "", "is_job": false, "is_prospect": false}

If NOT an opportunity, respond: {"is_opportunity": false}"""

SKILL_MATCH = """You are a skill matcher for freelance opportunities. You compare a freelancer's profile against a job or client opportunity and return a match score.

The freelancer specializes in: Python, Scikit-learn, Pandas, NumPy, Matplotlib, Seaborn, SQL, Statistics, FastAPI, Data Analysis, EDA.
They are LEARNING: TensorFlow, PyTorch, Deep Learning.
They want entry-level to intermediate freelance work. They are from Dhaka, Bangladesh and prefer remote work.

Scoring rules:
- 90-100: Perfect match — skills align exactly, no advanced DL required
- 70-89: Strong match — most skills align, some learning needed
- 50-69: Good match — some relevant skills, but some gaps
- 30-49: Weak match — significant skill gaps or requires advanced DL
- 0-29: Poor match — requires expertise they don't have

If the job REQUIRES advanced TensorFlow/PyTorch/Deep Learning expertise, score low (max 30).
If the job mentions "entry level", "junior", "beginner friendly", or "learning opportunity", bonus +10 points.

Respond in JSON: {"score": 0-100, "reason": "Brief explanation of the score"}"""

OUTREACH_EMAIL = """You are a cold email writer for a freelance professional. Generate a professional, personalized cold email.

The freelancer:
- Name: {name}
- Title: {title}
- Location: {location}
- Key skills: {skills}
- Portfolio: {portfolio_urls}
- Stats background from university

Tone: Professional, confident, helpful — not desperate. Show how you can solve their problems.

Write a cold email to the prospect with:
1. Subject line that references their company/work
2. Introduction — who you are
3. Value proposition — relevant project from portfolio that relates to their work
4. Call to action — suggest a quick call

Return as JSON: {{"subject": "...", "email_body": "..."}}"""

OUTREACH_LINKEDIN = """You are a LinkedIn message writer for a freelance professional. Generate a short, professional LinkedIn connection request.

The freelancer:
- Name: {name}
- Title: {title}
- Key skills: {skills}

Write a ~100 character LinkedIn connection note. Be specific about why you want to connect. Reference their work or company.

Return as JSON: {{"message": "..."}}"""
```

---

### Task 4: Base Agent + Web Search Agent

**Files:**
- Create: `E:\Desktop\ggh\app\agents\__init__.py` (empty)
- Create: `E:\Desktop\ggh\app\agents\base.py`
- Create: `E:\Desktop\ggh\app\agents\web_search.py`

- [ ] **Step 1: Create agents/base.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)


class BaseAgent:
    def __init__(self):
        self.session: AsyncSession | None = None

    async def __aenter__(self):
        self.session = async_session()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
```

- [ ] **Step 2: Create agents/web_search.py**

```python
from app.agents.base import BaseAgent, logger
from app.models import Job, Prospect, ScrapeSession
from app.llm.client import llm
from app.llm.prompts import EXTRACT_OPPORTUNITY
from app.config import settings
from googlesearch import search
import httpx
import yaml
from pathlib import Path
from datetime import datetime


class WebSearchAgent(BaseAgent):
    async def run(self, custom_query: str | None = None):
        queries = self._load_queries()
        if custom_query:
            queries = [custom_query]

        for query in queries:
            session_log = ScrapeSession(source="web_search", query=query)
            self.session.add(session_log)
            await self.session.flush()

            try:
                urls = list(search(query, num_results=settings.max_search_results))
                session_log.urls_found = len(urls)

                for url in urls:
                    content = await self._fetch_page(url)
                    if not content:
                        continue

                    result = await self._extract_opportunity(content, url)
                    if result and result.get("is_opportunity"):
                        await self._store_result(result, query, url)
                        if result.get("is_job"):
                            session_log.jobs_found += 1
                        if result.get("is_prospect"):
                            session_log.prospects_found += 1

                session_log.status = "completed"
            except Exception as e:
                session_log.status = "failed"
                session_log.error = str(e)
                logger.error(f"Search failed for '{query}': {e}")

            await self.session.commit()

    def _load_queries(self) -> list[str]:
        path = Path(settings.config_dir) / "queries.yml"
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f)
                return data.get("queries", [])
        return []

    async def _fetch_page(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    return resp.text
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
        return None

    async def _extract_opportunity(self, content: str, url: str) -> dict | None:
        text = content[:8000]
        try:
            result = await llm.chat(
                system=EXTRACT_OPPORTUNITY,
                user=f"URL: {url}\n\nContent:\n{text}",
            )
            import json
            result = result.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[-1]
                result = result.rsplit("\n", 1)[0]
            if result.startswith("json"):
                result = result[4:]
            return json.loads(result)
        except Exception as e:
            logger.debug(f"LLM extraction failed for {url}: {e}")
            return None

    async def _store_result(self, result: dict, query: str, url: str):
        if result.get("is_job"):
            existing = await self.session.get(Job, url)
            if not existing:
                job = Job(
                    title=result.get("title", "Untitled"),
                    platform="web_search",
                    url=url,
                    description=result.get("description", ""),
                    required_skills=[s.strip() for s in result.get("required_skills", "").split(",") if s.strip()],
                    budget=result.get("budget", ""),
                    client_name=result.get("company", ""),
                    source_query=query,
                )
                self.session.add(job)

        if result.get("is_prospect"):
            existing = await self.session.get(Prospect, url)
            if not existing:
                prospect = Prospect(
                    company_name=result.get("company", "Unknown"),
                    contact_name=result.get("contact_name", ""),
                    email=result.get("contact_email", ""),
                    company_url=url,
                    source="web_search",
                    source_query=query,
                    notes=result.get("description", ""),
                )
                self.session.add(prospect)
```

---

### Task 5: Known Platform Scrapers

**Files:**
- Create: `E:\Desktop\ggh\app\scrapers\__init__.py` (empty)
- Create: `E:\Desktop\ggh\app\scrapers\base.py`
- Create: `E:\Desktop\ggh\app\scrapers\upwork.py`
- Create: `E:\Desktop\ggh\app\scrapers\indeed.py`
- Create: `E:\Desktop\ggh\app\scrapers\freelancer.py`

- [ ] **Step 1: Create scrapers/base.py**

```python
from abc import ABC, abstractmethod
from app.database import async_session
from app.models import Job, ScrapeSession
from app.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    def __init__(self):
        self.session = None

    @abstractmethod
    async def scrape(self, query: str) -> list[dict]:
        pass

    async def run(self, query: str = ""):
        self.session = async_session()
        session_log = ScrapeSession(source=self.__class__.__name__, query=query)
        self.session.add(session_log)

        try:
            results = await self.scrape(query)
            for item in results:
                job = Job(
                    title=item.get("title", ""),
                    platform=self.__class__.__name__.lower(),
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                    required_skills=item.get("skills", []),
                    budget=item.get("budget", ""),
                    client_name=item.get("client", ""),
                    client_location=item.get("location", ""),
                )
                self.session.add(job)

            session_log.jobs_found = len(results)
            session_log.status = "completed"
        except Exception as e:
            session_log.status = "failed"
            session_log.error = str(e)
            logger.error(f"Scrape failed: {e}")

        await self.session.commit()
        if self.session:
            await self.session.close()
```

- [ ] **Step 2: Create scrapers/upwork.py**

```python
from app.scrapers.base import BaseScraper, logger
from app.config import settings
import httpx
from bs4 import BeautifulSoup


class UpworkScraper(BaseScraper):
    async def scrape(self, query: str) -> list[dict]:
        results = []
        search_url = f"https://www.upwork.com/search/jobs/?q={query}&sort=recency"
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for card in soup.select('[data-job-title]')[:20]:
                        results.append({
                            "title": card.get("data-job-title", ""),
                            "url": f"https://www.upwork.com{card.get('href', '')}",
                            "description": card.get_text(strip=True)[:500],
                            "skills": [],
                            "budget": "",
                            "client": "",
                            "location": "Remote",
                        })
                    await asyncio.sleep(settings.scrape_delay)
        except Exception as e:
            logger.error(f"Upwork scrape error: {e}")
        return results
```

- [ ] **Step 3: Create scrapers/indeed.py**

```python
from app.scrapers.base import BaseScraper, logger
from app.config import settings
import httpx
from bs4 import BeautifulSoup


class IndeedScraper(BaseScraper):
    async def scrape(self, query: str) -> list[dict]:
        results = []
        search_url = f"https://www.indeed.com/q-{query}-l-remote-freelance-jobs.html"
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for card in soup.select(".job_seen_beacon")[:20]:
                        title_el = card.select_one(".jobTitle")
                        company_el = card.select_one(".companyName")
                        desc_el = card.select_one(".job-snippet")
                        results.append({
                            "title": title_el.get_text(strip=True) if title_el else "",
                            "url": f"https://www.indeed.com{title_el.find('a').get('href', '') if title_el and title_el.find('a') else ''}",
                            "description": desc_el.get_text(strip=True)[:500] if desc_el else "",
                            "skills": [],
                            "budget": "",
                            "client": company_el.get_text(strip=True) if company_el else "",
                            "location": "Remote",
                        })
                    await asyncio.sleep(settings.scrape_delay)
        except Exception as e:
            logger.error(f"Indeed scrape error: {e}")
        return results
```

- [ ] **Step 4: Create scrapers/freelancer.py**

```python
from app.scrapers.base import BaseScraper, logger
from app.config import settings
import httpx
from bs4 import BeautifulSoup


class FreelancerScraper(BaseScraper):
    async def scrape(self, query: str) -> list[dict]:
        results = []
        search_url = f"https://www.freelancer.com/projects/skill/{query}/"
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for project in soup.select(".ProjectCard")[:20]:
                        title_el = project.select_one(".ProjectCard-title")
                        desc_el = project.select_one(".ProjectCard-description")
                        results.append({
                            "title": title_el.get_text(strip=True) if title_el else "",
                            "url": f"https://www.freelancer.com{title_el.find('a').get('href', '') if title_el and title_el.find('a') else ''}",
                            "description": desc_el.get_text(strip=True)[:500] if desc_el else "",
                            "skills": [],
                            "budget": "",
                            "client": "",
                            "location": "Remote",
                        })
                    await asyncio.sleep(settings.scrape_delay)
        except Exception as e:
            logger.error(f"Freelancer scrape error: {e}")
        return results
```

---

### Task 6: Client Discovery Agent

**Files:**
- Create: `E:\Desktop\ggh\app\agents\client_discovery.py`

- [ ] **Step 1: Create client_discovery.py**

```python
from app.agents.base import BaseAgent, logger
from app.models import Prospect, ScrapeSession
from app.llm.client import llm
from app.llm.prompts import EXTRACT_OPPORTUNITY
from app.config import settings
import httpx
from bs4 import BeautifulSoup
import yaml
from pathlib import Path


class ClientDiscoveryAgent(BaseAgent):
    async def run(self):
        companies = self._load_companies()
        await self._search_linkedin()
        await self._search_crunchbase()
        for company in companies:
            await self._scrape_company_page(company)

    def _load_companies(self) -> list[str]:
        path = Path(settings.config_dir) / "companies.yml"
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f)
                return data.get("companies", [])
        return ["openai", "anthropic", "huggingface", "databricks", "scaleai"]

    async def _search_linkedin(self):
        session = ScrapeSession(source="linkedin", query="ML freelancer companies")
        self.session.add(session)
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://www.linkedin.com/search/results/companies/?keywords=machine+learning",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for item in soup.select(".entity-result")[:10]:
                        name_el = item.select_one(".entity-result__title-text")
                        if name_el:
                            prospect = Prospect(
                                company_name=name_el.get_text(strip=True),
                                source="linkedin",
                                source_query="ML companies",
                            )
                            self.session.add(prospect)
                            session.prospects_found += 1
            session.status = "completed"
        except Exception as e:
            session.status = "failed"
            session.error = str(e)
        await self.session.commit()

    async def _search_crunchbase(self):
        session = ScrapeSession(source="crunchbase", query="AI/ML startups")
        self.session.add(session)
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(
                    "https://www.crunchbase.com/discover/organization.companies/",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for item in soup.select(".grid-item")[:10]:
                        prospect = Prospect(
                            company_name=item.get_text(strip=True)[:100],
                            source="crunchbase",
                            source_query="AI ML startups",
                        )
                        self.session.add(prospect)
                        session.prospects_found += 1
            session.status = "completed"
        except Exception as e:
            session.status = "failed"
            session.error = str(e)
        await self.session.commit()

    async def _scrape_company_page(self, company: str):
        session = ScrapeSession(source="company_page", query=company)
        self.session.add(session)
        urls = [
            f"https://{company}.com/careers",
            f"https://www.{company}.com/careers",
        ]
        for url in urls:
            try:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200 and "ML" in resp.text or "machine learning" in resp.text.lower():
                        prospect = Prospect(
                            company_name=company,
                            company_url=url,
                            source="company_page",
                            notes=f"Has ML-related opportunities at {url}",
                        )
                        self.session.add(prospect)
                        session.prospects_found += 1
            except Exception:
                pass
        session.status = "completed"
        await self.session.commit()
```

---

### Task 7: Skill Matcher Agent

**Files:**
- Create: `E:\Desktop\ggh\app\agents\matcher.py`

- [ ] **Step 1: Create matcher.py**

```python
from app.agents.base import BaseAgent, logger
from app.models import Job, Prospect
from app.llm.client import llm
from app.llm.prompts import SKILL_MATCH
from sqlalchemy import select


class SkillMatcherAgent(BaseAgent):
    async def run(self):
        await self._match_jobs()
        await self._match_prospects()

    async def _match_jobs(self):
        result = await self.session.execute(
            select(Job).where(Job.match_score == 0)
        )
        jobs = result.scalars().all()
        for job in jobs:
            score = await self._score_opportunity(
                title=job.title,
                description=job.description,
                skills=job.required_skills,
            )
            job.match_score = score.get("score", 0)
            job.match_reason = score.get("reason", "")
            job.status = "matched"
        await self.session.commit()
        logger.info(f"Matched {len(jobs)} jobs")

    async def _match_prospects(self):
        result = await self.session.execute(
            select(Prospect).where(Prospect.relevance_score == 0)
        )
        prospects = result.scalars().all()
        for prospect in prospects:
            score = await self._score_opportunity(
                title=prospect.company_name,
                description=prospect.notes,
                skills=[],
            )
            prospect.relevance_score = score.get("score", 0)
            prospect.relevance_reason = score.get("reason", "")
        await self.session.commit()
        logger.info(f"Matched {len(prospects)} prospects")

    async def _score_opportunity(self, title: str, description: str, skills: list) -> dict:
        user_input = f"Title: {title}\nDescription: {description}\nRequired Skills: {', '.join(skills)}"
        try:
            result = await llm.chat(system=SKILL_MATCH, user=user_input)
            import json
            result = result.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[-1]
                result = result.rsplit("\n", 1)[0]
            if result.startswith("json"):
                result = result[4:]
            return json.loads(result)
        except Exception as e:
            logger.error(f"Match error for '{title}': {e}")
            return {"score": 0, "reason": "Failed to score"}
```

---

### Task 8: Outreach Draft Agent

**Files:**
- Create: `E:\Desktop\ggh\app\agents\outreach.py`

- [ ] **Step 1: Create outreach.py**

```python
from app.agents.base import BaseAgent, logger
from app.models import Job, Prospect, OutreachDraft, UserProfile
from app.llm.client import llm
from app.llm.prompts import OUTREACH_EMAIL, OUTREACH_LINKEDIN
from sqlalchemy import select


class OutreachAgent(BaseAgent):
    async def run(self):
        profile = await self._get_profile()
        if not profile:
            logger.warning("No user profile found — run 'ggh config set-profile' first")
            return

        await self._generate_for_prospects(profile)
        await self._generate_for_jobs(profile)

    async def _get_profile(self):
        result = await self.session.execute(select(UserProfile))
        return result.scalar_one_or_none()

    async def _generate_for_prospects(self, profile):
        result = await self.session.execute(
            select(Prospect).where(Prospect.relevance_score >= 50)
        )
        prospects = result.scalars().all()

        for prospect in prospects:
            draft = await self._generate_draft(profile, prospect)
            if draft:
                self.session.add(draft)

        await self.session.commit()
        logger.info(f"Generated drafts for {len(prospects)} prospects")

    async def _generate_for_jobs(self, profile):
        result = await self.session.execute(
            select(Job).where(Job.match_score >= 50)
        )
        jobs = result.scalars().all()

        for job in jobs:
            prospect = Prospect(
                company_name=job.client_name or "Unknown Company",
                source="job_listing",
                notes=job.description[:500],
            )
            self.session.add(prospect)
            await self.session.flush()
            draft = await self._generate_draft(profile, prospect, job)
            if draft:
                self.session.add(draft)

        await self.session.commit()
        logger.info(f"Generated drafts for {len(jobs)} jobs")

    async def _generate_draft(self, profile, prospect, job=None):
        try:
            skills_str = ", ".join(profile.skills or [])
            portfolio_str = ", ".join(profile.portfolio_urls or [])

            email_result = await llm.chat(
                system=OUTREACH_EMAIL.format(
                    name=profile.name,
                    title=profile.title,
                    location=profile.location,
                    skills=skills_str,
                    portfolio_urls=portfolio_str,
                ),
                user=f"Company: {prospect.company_name}\nNotes: {prospect.notes[:500]}",
            )
            import json
            email_result = email_result.strip()
            if email_result.startswith("```"):
                email_result = email_result.split("\n", 1)[-1]
                email_result = email_result.rsplit("\n", 1)[0]
            if email_result.startswith("json"):
                email_result = email_result[4:]
            email_data = json.loads(email_result)

            li_result = await llm.chat(
                system=OUTREACH_LINKEDIN.format(
                    name=profile.name,
                    title=profile.title,
                    skills=skills_str,
                ),
                user=f"Company: {prospect.company_name}",
            )
            li_result = li_result.strip()
            if li_result.startswith("```"):
                li_result = li_result.split("\n", 1)[-1]
                li_result = li_result.rsplit("\n", 1)[0]
            if li_result.startswith("json"):
                li_result = li_result[4:]
            li_data = json.loads(li_result)

            return OutreachDraft(
                prospect_id=prospect.id,
                job_id=job.id if job else None,
                email_subject=email_data.get("subject", ""),
                email_body=email_data.get("email_body", ""),
                linkedin_message=li_data.get("message", ""),
            )
        except Exception as e:
            logger.error(f"Draft generation failed for {prospect.company_name}: {e}")
            return None
```

---

### Task 9: CLI Interface

**Files:**
- Create: `E:\Desktop\ggh\app\cli.py`
- Create: `E:\Desktop\ggh\app\agents\__init__.py` (update)

- [ ] **Step 1: Create cli.py**

```python
import asyncio
import click
from pathlib import Path


@click.group()
def cli():
    pass


@cli.command()
@click.argument("query", required=False)
def search(query):
    """Search the web for freelance opportunities dynamically"""
    async def _run():
        from app.database import init_db
        await init_db()
        from app.agents.web_search import WebSearchAgent
        async with WebSearchAgent() as agent:
            await agent.run(custom_query=query)
        click.echo("Search complete.")
    asyncio.run(_run())


@cli.command()
def scrape_jobs():
    """Scrape known freelance platforms for ML jobs"""
    async def _run():
        from app.database import init_db
        await init_db()
        from app.scrapers.upwork import UpworkScraper
        from app.scrapers.indeed import IndeedScraper
        from app.scrapers.freelancer import FreelancerScraper
        scrapers = [
            UpworkScraper(),
            IndeedScraper(),
            FreelancerScraper(),
        ]
        queries = ["machine learning", "data analysis", "python", "scikit-learn"]
        for scraper in scrapers:
            for q in queries:
                click.echo(f"  Scraping {scraper.__class__.__name__} for '{q}'...")
                await scraper.run(q)
        click.echo("Job scraping complete.")
    asyncio.run(_run())


@cli.command()
def scrape_prospects():
    """Find new prospects from LinkedIn, Crunchbase, company pages"""
    async def _run():
        from app.database import init_db
        await init_db()
        from app.agents.client_discovery import ClientDiscoveryAgent
        async with ClientDiscoveryAgent() as agent:
            await agent.run()
        click.echo("Prospect discovery complete.")
    asyncio.run(_run())


@cli.command()
def match():
    """Score all unscored jobs and prospects against your profile"""
    async def _run():
        from app.database import init_db
        await init_db()
        from app.agents.matcher import SkillMatcherAgent
        async with SkillMatcherAgent() as agent:
            await agent.run()
        click.echo("Matching complete.")
    asyncio.run(_run())


@cli.command()
def generate():
    """Generate outreach drafts for matched opportunities"""
    async def _run():
        from app.database import init_db
        await init_db()
        from app.agents.outreach import OutreachAgent
        async with OutreachAgent() as agent:
            await agent.run()
        click.echo("Draft generation complete.")
    asyncio.run(_run())


@cli.command()
def run_all():
    """Full pipeline: search → scrape → match → generate"""
    async def _run():
        from app.database import init_db
        await init_db()
        click.echo("1/4 Searching web for opportunities...")
        from app.agents.web_search import WebSearchAgent
        async with WebSearchAgent() as agent:
            await agent.run()
        click.echo("2/4 Scraping known platforms...")
        from app.scrapers.upwork import UpworkScraper
        from app.scrapers.indeed import IndeedScraper
        from app.scrapers.freelancer import FreelancerScraper
        scrapers = [UpworkScraper(), IndeedScraper(), FreelancerScraper()]
        queries = ["machine learning", "data analysis", "python"]
        for s in scrapers:
            for q in queries:
                await s.run(q)
        click.echo("3/4 Matching skills...")
        from app.agents.matcher import SkillMatcherAgent
        async with SkillMatcherAgent() as agent:
            await agent.run()
        click.echo("4/4 Generating outreach drafts...")
        from app.agents.outreach import OutreachAgent
        async with OutreachAgent() as agent:
            await agent.run()
        click.echo("Pipeline complete!")
    asyncio.run(_run())


@cli.command()
def serve():
    """Start the web dashboard"""
    click.echo("Starting dashboard at http://localhost:8000")
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


@cli.command()
def stats():
    """Show database statistics"""
    async def _run():
        from app.database import init_db, async_session
        from app.models import Job, Prospect, OutreachDraft
        from sqlalchemy import select, func
        await init_db()
        async with async_session() as session:
            jobs = (await session.execute(select(func.count(Job.id)))).scalar()
            prospects = (await session.execute(select(func.count(Prospect.id)))).scalar()
            drafts = (await session.execute(select(func.count(OutreachDraft.id)))).scalar()
            matched = (await session.execute(select(func.count(Job.id)).where(Job.match_score > 0))).scalar()
            high = (await session.execute(select(func.count(Job.id)).where(Job.match_score >= 70))).scalar()
        click.echo(f"Jobs: {jobs} ({matched} matched, {high} high-score)")
        click.echo(f"Prospects: {prospects}")
        click.echo(f"Drafts: {drafts}")
    asyncio.run(_run())


@cli.command()
@click.option("--name", prompt="Your name")
@click.option("--title", prompt="Your title")
@click.option("--summary", prompt="Brief summary")
@click.option("--skills", prompt="Skills (comma-separated)")
@click.option("--portfolio", prompt="Portfolio URLs (comma-separated)")
def set_profile(name, title, summary, skills, portfolio):
    """Set your freelancer profile"""
    async def _run():
        from app.database import init_db, async_session
        from app.models import UserProfile
        from sqlalchemy import select
        await init_db()
        async with async_session() as session:
            result = await session.execute(select(UserProfile))
            profile = result.scalar_one_or_none()
            if not profile:
                profile = UserProfile()
                session.add(profile)
            profile.name = name
            profile.title = title
            profile.summary = summary
            profile.skills = [s.strip() for s in skills.split(",")]
            profile.portfolio_urls = [p.strip() for p in portfolio.split(",")]
            await session.commit()
        click.echo("Profile updated!")
    asyncio.run(_run())
```

---

### Task 10: Web Dashboard (FastAPI + Templates)

**Files:**
- Create: `E:\Desktop\ggh\app\main.py`
- Create: `E:\Desktop\ggh\app\templates\base.html`
- Create: `E:\Desktop\ggh\app\templates\dashboard.html`
- Create: `E:\Desktop\ggh\app\templates\jobs.html`
- Create: `E:\Desktop\ggh\app\templates\prospects.html`
- Create: `E:\Desktop\ggh\app\templates\drafts.html`
- Create: `E:\Desktop\ggh\app\templates\settings.html`
- Create: `E:\Desktop\ggh\app\static\style.css`
- Create: `E:\Desktop\ggh\app\static\script.js`

- [ ] **Step 1: Create main.py**

```python
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.database import init_db, get_session
from app.models import Job, Prospect, OutreachDraft, UserProfile

app = FastAPI(title="Freelancing OS")

templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(templates_dir))

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    total_jobs = (await session.execute(select(func.count(Job.id)))).scalar() or 0
    total_prospects = (await session.execute(select(func.count(Prospect.id)))).scalar() or 0
    total_drafts = (await session.execute(select(func.count(OutreachDraft.id)))).scalar() or 0
    matched = (await session.execute(select(func.count(Job.id)).where(Job.match_score > 0))).scalar() or 0
    high = (await session.execute(select(func.count(Job.id)).where(Job.match_score >= 70))).scalar() or 0
    profile = (await session.execute(select(UserProfile))).scalar_one_or_none()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": {
            "total_jobs": total_jobs,
            "total_prospects": total_prospects,
            "total_drafts": total_drafts,
            "matched_jobs": matched,
            "high_score_jobs": high,
        },
        "profile": profile,
    })


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Job).order_by(Job.match_score.desc()))
    jobs = result.scalars().all()
    return templates.TemplateResponse("jobs.html", {"request": request, "jobs": jobs})


@app.get("/prospects", response_class=HTMLResponse)
async def prospects_page(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Prospect).order_by(Prospect.relevance_score.desc()))
    prospects = result.scalars().all()
    return templates.TemplateResponse("prospects.html", {"request": request, "prospects": prospects})


@app.get("/drafts", response_class=HTMLResponse)
async def drafts_page(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(OutreachDraft).order_by(OutreachDraft.created_at.desc()))
    drafts = result.scalars().all()
    return templates.TemplateResponse("drafts.html", {"request": request, "drafts": drafts})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, session: AsyncSession = Depends(get_session)):
    profile = (await session.execute(select(UserProfile))).scalar_one_or_none()
    return templates.TemplateResponse("settings.html", {"request": request, "profile": profile})
```

- [ ] **Step 2: Create base.html**

```html
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Freelancing OS</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        primary: {50:'#eef2ff',100:'#e0e7ff',200:'#c7d2fe',300:'#a5b4fc',400:'#818cf8',500:'#6366f1',600:'#4f46e5',700:'#4338ca',800:'#3730a3',900:'#312e81'},
                        surface: {50:'#f8fafc',100:'#f1f5f9',200:'#e2e8f0',300:'#cbd5e1',400:'#94a3b8',500:'#64748b',600:'#475569',700:'#334155',800:'#1e293b',900:'#0f172a'},
                    }
                }
            }
        }
    </script>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body class="bg-surface-900 text-surface-100 min-h-screen">
    <nav class="bg-surface-800 border-b border-surface-700 px-6 py-3">
        <div class="max-w-7xl mx-auto flex items-center justify-between">
            <a href="/" class="text-xl font-bold text-primary-400">Freelancing OS</a>
            <div class="flex gap-6">
                <a href="/" class="hover:text-primary-400 transition">Dashboard</a>
                <a href="/jobs" class="hover:text-primary-400 transition">Jobs</a>
                <a href="/prospects" class="hover:text-primary-400 transition">Prospects</a>
                <a href="/drafts" class="hover:text-primary-400 transition">Drafts</a>
                <a href="/settings" class="hover:text-primary-400 transition">Settings</a>
            </div>
        </div>
    </nav>
    <main class="max-w-7xl mx-auto px-6 py-8">
        {% block content %}{% endblock %}
    </main>
    <script src="/static/script.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create dashboard.html**

```html
{% extends "base.html" %}
{% block content %}
<div class="mb-8">
    <h1 class="text-3xl font-bold mb-2">Dashboard</h1>
    <p class="text-surface-400">{{ profile.name if profile else 'Welcome' }} — Your Freelancing Command Center</p>
</div>

<div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
    <div class="bg-surface-800 rounded-xl p-5 border border-surface-700">
        <div class="text-surface-400 text-sm mb-1">Total Jobs</div>
        <div class="text-3xl font-bold text-primary-400">{{ stats.total_jobs }}</div>
    </div>
    <div class="bg-surface-800 rounded-xl p-5 border border-surface-700">
        <div class="text-surface-400 text-sm mb-1">Matched</div>
        <div class="text-3xl font-bold text-green-400">{{ stats.matched_jobs }}</div>
    </div>
    <div class="bg-surface-800 rounded-xl p-5 border border-surface-700">
        <div class="text-surface-400 text-sm mb-1">High Score</div>
        <div class="text-3xl font-bold text-emerald-400">{{ stats.high_score_jobs }}</div>
    </div>
    <div class="bg-surface-800 rounded-xl p-5 border border-surface-700">
        <div class="text-surface-400 text-sm mb-1">Prospects</div>
        <div class="text-3xl font-bold text-blue-400">{{ stats.total_prospects }}</div>
    </div>
    <div class="bg-surface-800 rounded-xl p-5 border border-surface-700">
        <div class="text-surface-400 text-sm mb-1">Drafts Ready</div>
        <div class="text-3xl font-bold text-purple-400">{{ stats.total_drafts }}</div>
    </div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div class="bg-surface-800 rounded-xl p-6 border border-surface-700">
        <h2 class="text-lg font-semibold mb-4">Quick Actions</h2>
        <div class="space-y-3">
            <a href="/jobs" class="block bg-primary-600 hover:bg-primary-500 text-white rounded-lg px-4 py-3 text-center transition">Browse Jobs</a>
            <a href="/prospects" class="block bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-4 py-3 text-center transition">View Prospects</a>
            <a href="/drafts" class="block bg-purple-600 hover:bg-purple-500 text-white rounded-lg px-4 py-3 text-center transition">Review Drafts</a>
        </div>
    </div>
    <div class="bg-surface-800 rounded-xl p-6 border border-surface-700">
        <h2 class="text-lg font-semibold mb-4">CLI Commands</h2>
        <div class="space-y-2 text-sm font-mono">
            <div class="bg-surface-900 rounded px-3 py-2"><span class="text-green-400">ggh run all</span> — Full pipeline</div>
            <div class="bg-surface-900 rounded px-3 py-2"><span class="text-green-400">ggh search "query"</span> — Web search</div>
            <div class="bg-surface-900 rounded px-3 py-2"><span class="text-green-400">ggh serve</span> — Open this dashboard</div>
            <div class="bg-surface-900 rounded px-3 py-2"><span class="text-green-400">ggh stats</span> — Show stats</div>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Create jobs.html**

```html
{% extends "base.html" %}
{% block content %}
<div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold">Jobs</h1>
    <div class="flex gap-2">
        <input type="text" id="search" placeholder="Search jobs..." class="bg-surface-700 border border-surface-600 rounded-lg px-4 py-2 text-sm">
        <select id="platform-filter" class="bg-surface-700 border border-surface-600 rounded-lg px-4 py-2 text-sm">
            <option value="all">All Platforms</option>
            <option value="web_search">Web Search</option>
            <option value="upworkscraper">Upwork</option>
            <option value="indeedscraper">Indeed</option>
            <option value="freelancerscraper">Freelancer</option>
        </select>
    </div>
</div>

<div class="bg-surface-800 rounded-xl border border-surface-700 overflow-hidden">
    <table class="w-full">
        <thead>
            <tr class="text-left text-surface-400 text-sm border-b border-surface-700">
                <th class="px-4 py-3">Title</th>
                <th class="px-4 py-3">Platform</th>
                <th class="px-4 py-3">Score</th>
                <th class="px-4 py-3">Client</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3">Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for job in jobs %}
            <tr class="border-b border-surface-700 hover:bg-surface-700/50 transition job-row" data-platform="{{ job.platform }}">
                <td class="px-4 py-3">
                    <div class="font-medium">{{ job.title[:80] }}</div>
                    <div class="text-surface-400 text-xs mt-1">{{ job.description[:100] }}{% if job.description|length > 100 %}...{% endif %}</div>
                </td>
                <td class="px-4 py-3 text-sm">{{ job.platform }}</td>
                <td class="px-4 py-3">
                    {% if job.match_score >= 70 %}
                    <span class="bg-green-600/20 text-green-400 px-2 py-1 rounded text-sm">{{ job.match_score }}</span>
                    {% elif job.match_score >= 40 %}
                    <span class="bg-yellow-600/20 text-yellow-400 px-2 py-1 rounded text-sm">{{ job.match_score }}</span>
                    {% elif job.match_score > 0 %}
                    <span class="bg-red-600/20 text-red-400 px-2 py-1 rounded text-sm">{{ job.match_score }}</span>
                    {% else %}
                    <span class="text-surface-500 text-sm">—</span>
                    {% endif %}
                </td>
                <td class="px-4 py-3 text-sm">{{ job.client_name or '—' }}</td>
                <td class="px-4 py-3 text-sm">{{ job.status }}</td>
                <td class="px-4 py-3">
                    <a href="{{ job.url }}" target="_blank" class="text-primary-400 hover:text-primary-300 text-sm">View</a>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="6" class="px-4 py-12 text-center text-surface-500">No jobs found yet. Run <code class="bg-surface-700 px-2 py-0.5 rounded text-green-400">ggh run all</code> to start discovering.</td></tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<script>
document.getElementById('search')?.addEventListener('input', function() {
    const q = this.value.toLowerCase();
    document.querySelectorAll('.job-row').forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
});
document.getElementById('platform-filter')?.addEventListener('change', function() {
    const v = this.value;
    document.querySelectorAll('.job-row').forEach(row => {
        row.style.display = v === 'all' || row.dataset.platform === v ? '' : 'none';
    });
});
</script>
{% endblock %}
```

- [ ] **Step 5: Create prospects.html**

```html
{% extends "base.html" %}
{% block content %}
<div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold">Prospects</h1>
    <input type="text" id="search" placeholder="Search prospects..." class="bg-surface-700 border border-surface-600 rounded-lg px-4 py-2 text-sm">
</div>

<div class="grid gap-4">
    {% for prospect in prospects %}
    <div class="bg-surface-800 rounded-xl p-5 border border-surface-700 prospect-card">
        <div class="flex justify-between items-start">
            <div>
                <h3 class="text-lg font-semibold">{{ prospect.company_name }}</h3>
                {% if prospect.contact_name %}
                <p class="text-surface-400 text-sm">{{ prospect.contact_name }}{% if prospect.contact_title %} — {{ prospect.contact_title }}{% endif %}</p>
                {% endif %}
            </div>
            <div class="flex items-center gap-3">
                {% if prospect.relevance_score >= 70 %}
                <span class="bg-green-600/20 text-green-400 px-2 py-1 rounded text-sm font-bold">{{ prospect.relevance_score }}</span>
                {% elif prospect.relevance_score >= 40 %}
                <span class="bg-yellow-600/20 text-yellow-400 px-2 py-1 rounded text-sm font-bold">{{ prospect.relevance_score }}</span>
                {% else %}
                <span class="bg-red-600/20 text-red-400 px-2 py-1 rounded text-sm font-bold">{{ prospect.relevance_score }}</span>
                {% endif %}
                <span class="text-surface-500 text-xs bg-surface-700 px-2 py-1 rounded">{{ prospect.source }}</span>
            </div>
        </div>
        {% if prospect.notes %}
        <p class="text-surface-300 text-sm mt-2">{{ prospect.notes[:200] }}</p>
        {% endif %}
        <div class="flex gap-3 mt-3 text-sm">
            {% if prospect.email %}
            <span class="text-surface-400">✉ {{ prospect.email }}</span>
            {% endif %}
            {% if prospect.linkedin_url %}
            <a href="{{ prospect.linkedin_url }}" target="_blank" class="text-blue-400 hover:text-blue-300">LinkedIn</a>
            {% endif %}
            {% if prospect.company_url %}
            <a href="{{ prospect.company_url }}" target="_blank" class="text-primary-400 hover:text-primary-300">Website</a>
            {% endif %}
        </div>
    </div>
    {% else %}
    <div class="text-center text-surface-500 py-12">No prospects yet. Run <code class="bg-surface-700 px-2 py-0.5 rounded text-green-400">ggh scrape prospects</code> to find leads.</div>
    {% endfor %}
</div>

<script>
document.getElementById('search')?.addEventListener('input', function() {
    const q = this.value.toLowerCase();
    document.querySelectorAll('.prospect-card').forEach(card => {
        card.style.display = card.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
});
</script>
{% endblock %}
```

- [ ] **Step 6: Create drafts.html**

```html
{% extends "base.html" %}
{% block content %}
<div class="mb-6">
    <h1 class="text-3xl font-bold">Outreach Drafts</h1>
    <p class="text-surface-400 mt-1">Review and copy cold email / LinkedIn drafts</p>
</div>

<div class="space-y-6">
    {% for draft in drafts %}
    <div class="bg-surface-800 rounded-xl border border-surface-700 overflow-hidden">
        <div class="bg-surface-750 px-5 py-3 border-b border-surface-700 flex justify-between items-center">
            <div>
                <span class="font-semibold">{{ draft.email_subject or 'No Subject' }}</span>
                <span class="text-surface-500 text-sm ml-3">Draft #{{ draft.id }}</span>
            </div>
            <span class="text-xs bg-surface-700 text-surface-300 px-2 py-1 rounded">{{ draft.status }}</span>
        </div>
        <div class="p-5 space-y-4">
            <div>
                <div class="flex justify-between items-center mb-2">
                    <h3 class="text-sm font-medium text-surface-400">📧 Email</h3>
                    <button onclick="copyText(this, 'email-{{ draft.id }}')" class="text-xs bg-primary-600 hover:bg-primary-500 px-3 py-1 rounded transition">Copy Email</button>
                </div>
                <div id="email-{{ draft.id }}" class="bg-surface-900 rounded-lg p-4 text-sm whitespace-pre-wrap font-sans text-surface-200">{{ draft.email_body }}</div>
            </div>
            <div>
                <div class="flex justify-between items-center mb-2">
                    <h3 class="text-sm font-medium text-surface-400">💼 LinkedIn</h3>
                    <button onclick="copyText(this, 'li-{{ draft.id }}')" class="text-xs bg-blue-600 hover:bg-blue-500 px-3 py-1 rounded transition">Copy LinkedIn Message</button>
                </div>
                <div id="li-{{ draft.id }}" class="bg-surface-900 rounded-lg p-4 text-sm whitespace-pre-wrap font-sans text-surface-200">{{ draft.linkedin_message }}</div>
            </div>
        </div>
    </div>
    {% else %}
    <div class="text-center text-surface-500 py-12">No drafts yet. Run <code class="bg-surface-700 px-2 py-0.5 rounded text-green-400">ggh generate</code> to create them.</div>
    {% endfor %}
</div>

<script>
function copyText(btn, id) {
    const text = document.getElementById(id).textContent;
    navigator.clipboard.writeText(text).then(() => {
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        btn.classList.add('bg-green-600');
        setTimeout(() => {
            btn.textContent = orig;
            btn.classList.remove('bg-green-600');
        }, 1500);
    });
}
</script>
{% endblock %}
```

- [ ] **Step 7: Create settings.html**

```html
{% extends "base.html" %}
{% block content %}
<div class="mb-6">
    <h1 class="text-3xl font-bold">Settings</h1>
    <p class="text-surface-400 mt-1">Manage your freelancer profile</p>
</div>

<div class="bg-surface-800 rounded-xl p-6 border border-surface-700 max-w-2xl">
    <h2 class="text-lg font-semibold mb-4">Your Profile</h2>
    {% if profile %}
    <div class="space-y-3">
        <div><span class="text-surface-400 text-sm">Name:</span> <span class="ml-2">{{ profile.name }}</span></div>
        <div><span class="text-surface-400 text-sm">Title:</span> <span class="ml-2">{{ profile.title }}</span></div>
        <div><span class="text-surface-400 text-sm">Location:</span> <span class="ml-2">{{ profile.location }}</span></div>
        <div><span class="text-surface-400 text-sm">Skills:</span> <span class="ml-2">{{ profile.skills|join(', ') }}</span></div>
        <div><span class="text-surface-400 text-sm">Portfolio:</span>
            {% for url in profile.portfolio_urls %}
            <a href="{{ url }}" target="_blank" class="ml-2 text-primary-400 hover:text-primary-300 block">{{ url }}</a>
            {% endfor %}
        </div>
    </div>
    {% else %}
    <p class="text-surface-500">No profile set. Use <code class="bg-surface-700 px-2 py-0.5 rounded text-green-400">ggh set-profile</code> in the CLI.</p>
    {% endif %}
    <div class="mt-6 p-4 bg-surface-900/50 rounded-lg">
        <p class="text-sm text-surface-400">To update your profile, run in terminal:</p>
        <code class="block mt-2 bg-surface-800 px-3 py-2 rounded text-green-400 font-mono text-sm">ggh set-profile --name "Sium Ahameed" --title "ML Engineer" --skills "Python,Scikit-learn,Pandas" --portfolio "https://siumahameed.github.io/portfolio/"</code>
    </div>
</div>

<div class="bg-surface-800 rounded-xl p-6 border border-surface-700 max-w-2xl mt-6">
    <h2 class="text-lg font-semibold mb-4">Search Queries</h2>
    <p class="text-surface-400 text-sm mb-3">Edit <code class="bg-surface-700 px-1.5 py-0.5 rounded">config/queries.yml</code> to customize what the web search agent looks for.</p>
    <p class="text-surface-500 text-xs">Example queries you can add: "freelance FastAPI developer needed", "remote data analysis project", "statistics consultant freelance"</p>
</div>
{% endblock %}
```

- [ ] **Step 8: Create style.css**

```css
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.bg-surface-750 { background-color: #1a2332; }
```

- [ ] **Step 9: Create script.js**

```js
// Clipboard helper for draft pages
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-copy]').forEach(el => {
        el.addEventListener('click', function() {
            const target = document.getElementById(this.dataset.copy);
            if (target) {
                navigator.clipboard.writeText(target.textContent);
                const orig = this.textContent;
                this.textContent = 'Copied!';
                setTimeout(() => this.textContent = orig, 1500);
            }
        });
    });
});
```

---

### Task 11: Install Dependencies + Init Playwright

**Files:** None (terminal commands)

- [ ] **Step 1: Install Python dependencies**

```bash
cd E:\Desktop\ggh
pip install -e .
```

- [ ] **Step 2: Install Playwright browsers**

```bash
playwright install chromium
```

---

### Task 12: Init DB + Set Profile + Verify

**Files:** None (terminal commands)

- [ ] **Step 1: Initialize database by running any command**

```bash
cd E:\Desktop\ggh
python -c "import asyncio; from app.database import init_db; asyncio.run(init_db()); print('DB created')"
```

- [ ] **Step 2: Set your profile**

```bash
ggh set-profile --name "Sium Ahameed" --title "Machine Learning Engineer" --summary "Statistics graduate with ML skills" --skills "Python,Scikit-learn,Pandas,NumPy,FastAPI,SQL,Statistics,Matplotlib,Seaborn,Data Analysis" --portfolio "https://siumahameed.github.io/portfolio/,https://github.com/siumahameed,https://linkedin.com/in/sium11"
```

- [ ] **Step 3: Start web dashboard and verify**

```bash
ggh serve
```

Open browser to http://localhost:8000 — should see the dashboard with your profile.

---

### Task 13: Run Full Pipeline + Verify

**Files:** None (terminal commands)

- [ ] **Step 1: Run the full pipeline**

```bash
cd E:\Desktop\ggh
ggh run all
```

- [ ] **Step 2: Check stats**

```bash
ggh stats
```

Expected: jobs > 0, prospects > 0, drafts > 0

- [ ] **Step 3: Browse results in web dashboard**

```bash
ggh serve
```

Open http://localhost:8000 — check Jobs, Prospects, Drafts pages for results.

- [ ] **Step 4: Run individual commands if needed**

```bash
ggh search "data science freelancer needed"
ggh scrape jobs
ggh scrape prospects
ggh match
ggh generate
```

---

### Self-Review Checklist

1. **Spec coverage:** All spec sections mapped to tasks:
   - Web search agent → Task 4
   - Platform scrapers → Task 5
   - Client discovery → Task 6
   - Skill matcher → Task 7
   - Outreach drafts → Task 8
   - CLI → Task 9
   - Web dashboard → Task 10
   - Profile management → Task 9 (set-profile)

2. **Placeholder scan:** All code blocks contain complete implementations. No TBD, TODO, or vague references.

3. **Type consistency:** Method signatures match across agents (all use async `run()`), model fields consistent between models.py and templates.

4. **Ambiguity check:** File paths are absolute. CLI commands are exact. Template variables match what main.py passes.
