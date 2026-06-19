# Freelancing OS — Design Spec

**Author:** Sium Ahameed
**Date:** 2026-06-01
**Stack:** Python 3.11+, FastAPI, SQLAlchemy + SQLite, Playwright, httpx, BeautifulSoup, Click, Jinja2 + Tailwind CSS, OpenAI/Anthropic API

---

## 1. System Architecture

```
┌───────────────────────────────────────────────────────────┐
│                    CLI (click)                            │
│  ggh search <query>   — Web search for any opportunity   │
│  ggh scrape jobs      — Scrape known freelance platforms │
│  ggh scrape prospects — Find new leads dynamically       │
│  ggh match            — Score vs user profile            │
│  ggh generate         — Create outreach drafts           │
│  ggh serve            — Launch web dashboard             │
│  ggh run all          — Full pipeline                    │
└──────────────────────┬────────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────┐
│                    Agent Pipeline                          │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 1. Web Search Agent (dynamic)                        │ │
│  │    Google/Bing search via configurable queries       │ │
│  │    Crawls every result URL → LLM extracts            │ │
│  │    job/client info from ANY page                     │ │
│  └──────────────────────┬───────────────────────────────┘ │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │ 2. Job Scraper Agent (known platforms)              │  │
│  │    Upwork, Fiverr, Freelancer.com, Indeed, Remote   │  │
│  └──────────────────────┬──────────────────────────────┘  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │ 3. Client Discovery Agent (targeted directories)    │  │
│  │    LinkedIn, Crunchbase, Wellfound, company pages   │  │
│  └──────────────────────┬──────────────────────────────┘  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │ 4. Skill Matcher Agent (LLM)                        │  │
│  │    Scores 0-100 against user profile                │  │
│  │    Filters out advanced TF/PyTorch roles            │  │
│  │    Favors sklearn/data-analysis/FastAPI jobs        │  │
│  └──────────────────────┬──────────────────────────────┘  │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │ 5. Outreach Draft Agent (LLM)                       │  │
│  │    Cold email + LinkedIn message per prospect       │  │
│  │    References portfolio, stats background           │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│              SQLite Database                               │
│  user_profile | jobs | prospects | outreach_drafts        │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│          Web Dashboard (FastAPI + Jinja2 + Tailwind CSS)   │
│  /dashboard | /jobs | /prospects | /drafts | /settings    │
└───────────────────────────────────────────────────────────┘
```

---

## 2. Data Model

### Table: `user_profile`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | |
| name | Text | Sium Ahameed |
| title | Text | Machine Learning Engineer |
| summary | Text | Your bio |
| skills | JSON | ["Python", "Scikit-learn", "Pandas", "NumPy", "FastAPI", "SQL", "Statistics", "Matplotlib", "Seaborn", "TensorFlow (learning)", "PyTorch (learning)"] |
| portfolio_urls | JSON | ["https://siumahameed.github.io/portfolio/", "https://github.com/siumahameed", "https://linkedin.com/in/sium11"] |
| experience_years | Integer | |
| location | Text | Dhaka, Bangladesh |
| preferred_roles | JSON | ["Data Analyst", "ML Engineer (Junior)", "Data Science Freelancer", "Python Developer", "FastAPI Developer", "AI Consultant (entry)"] |

### Table: `jobs`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | |
| title | Text | Job title |
| platform | Text | upwork/fiverr/freelancer/indeed/remote/web_search |
| url | Text | Original listing URL |
| description | Text | Full job description |
| required_skills | JSON | Skills extracted |
| budget | Text | Budget range if available |
| client_name | Text | Client/company name |
| client_location | Text | |
| posted_date | DateTime | |
| match_score | Integer | 0-100 from skill matcher |
| match_reason | Text | LLM explanation |
| source_query | Text | Which search query found it |
| status | Text | new/matched/drafted/archived |
| created_at | DateTime | |

### Table: `prospects`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | |
| company_name | Text | |
| industry | Text | |
| contact_name | Text | Decision-maker name |
| contact_title | Text | e.g. CTO, Head of AI |
| email | Text | |
| linkedin_url | Text | |
| company_url | Text | |
| source | Text | linkedin/crunchbase/wellfound/web_search/company_page |
| source_query | Text | Which query found them |
| notes | Text | LLM summary of what they do |
| relevance_score | Integer | 0-100 |
| relevance_reason | Text | |
| status | Text | new/contacted/replied/closed |
| created_at | DateTime | |

### Table: `outreach_drafts`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | |
| prospect_id | Integer FK → prospects.id | |
| job_id | Integer FK → jobs.id (nullable) | |
| email_subject | Text | |
| email_body | Text | Full email HTML |
| linkedin_message | Text | Short LinkedIn note |
| channel | Text | email/linkedin/both |
| status | Text | draft/sent/replied/declined |
| sent_at | DateTime | |
| created_at | DateTime | |

### Table: `scrape_sessions`
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | |
| source | Text | web_search/upwork/fiverr/etc |
| query | Text | Search query used |
| urls_found | Integer | |
| jobs_found | Integer | |
| prospects_found | Integer | |
| status | Text | running/completed/failed |
| error | Text | |
| created_at | DateTime | |

---

## 3. Web Search Agent (Dynamic Discovery)

The key differentiator — searches the entire web, not just predefined sites.

### Flow:
1. Read configurable search queries from `config/queries.yml`
2. For each query, search Google (via `googlesearch-python` or similar)
3. Collect top N results per query (configurable, default 20)
4. Crawl each result URL with httpx
5. Pass page content to LLM with extraction prompt:
   - "Is this a freelance opportunity or potential client?"
   - If yes: extract company, contact, skills, budget
6. Store as job or prospect in DB

### Default queries (config/queries.yml):
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
```

Users can add/edit queries anytime.

---

## 4. Scrapers (Known Platforms)

### Upwork Scraper (Playwright)
- Search: "machine learning", "data analysis", "Python", "scikit-learn"
- Extract: title, description, budget, client info, skills required
- Filter: entry-level, fixed-price projects prioritized

### Fiverr Scraper (Playwright)  
- Browse "machine learning", "data analysis", "python" categories
- Extract: gig requirements, buyer requests

### Freelancer.com Scraper (httpx + BS4)
- Search ML/AI/Python projects
- Extract: project details, skills, budget

### Indeed + We Work Remotely (httpx + BS4)
- Filter: freelance/contract, remote, ML/AI/data

---

## 5. Client Discovery Agent (Targeted)

### LinkedIn (Playwright)
- Search for "hiring ML freelancer", "looking for data scientist"
- Extract post authors → company → contact info
- Search company pages for decision-makers

### Crunchbase + Wellfound (httpx + BS4)
- Find AI/ML startups and companies
- Extract: company name, industry, funding, tech stack, contact

### Company Career Pages
- Configurable list of companies
- Scrape for ML/freelance openings

---

## 6. Skill Matcher Agent (LLM)

### Scoring logic per job/prospect:
```
User skills (weighted):
  Python           →  essential (required always)
  Scikit-learn     →  strong_match (+20)
  Pandas/NumPy     →  strong_match (+15)
  FastAPI          →  good_match (+15)
  SQL              →  good_match (+10)
  Statistics       →  good_match (+10)
  Data Analysis    →  strong_match (+15)
  Matplotlib/Seaborn → moderate (+5)
  TensorFlow       →  learning (+5, not penalized)
  PyTorch          →  learning (+5, not penalized)

Scoring rules:
  - "Must have PyTorch/TensorFlow expert" → score capped at 30
  - "Nice to have DL" → still score high
  - "Entry level", "Junior", "Beginner friendly" → bonus +10
  - Location "Remote" → bonus +5
```

### LLM Prompt instructs:
- Favor sklearn/data-analysis/basic-ML roles
- Flag hard DL-specialist roles as low match
- Explain reasoning in match_reason field

---

## 7. Outreach Draft Agent (LLM)

### For each matched prospect (score > 50):
1. Load user profile + portfolio
2. Pick 2 most relevant projects from portfolio
3. Generate cold email:
   - Subject: personalized to prospect's company/work
   - Body: intro → relevant project → stats background → value proposition → CTA
4. Generate LinkedIn message:
   - ~100 words
   - Connection request note format
   - Reference specific work the prospect is doing
5. Store in `outreach_drafts` table

### LLM Prompt includes:
- Prospect info (company, role, industry)
- User profile (skills, stats background, location)
- Portfolio links
- 2 most relevant projects from portfolio
- Tone: professional, confident, not desperate

---

## 8. CLI Interface

```bash
ggh search "<query>"     # Search web for opportunities
ggh scrape jobs          # Scrape known freelance platforms
ggh scrape prospects     # Find new prospects from directories
ggh match                # Run skill matcher on all un-scored items
ggh generate             # Generate outreach drafts for matched items
ggh serve                # Start web dashboard at localhost:8000
ggh run all              # Full pipeline: search → scrape → match → generate
ggh config show          # Show current config
ggh config set <key> <val>  # Update config
ggh stats                # Show database stats
```

---

## 9. Web Dashboard

Built with FastAPI + Jinja2 templates + Tailwind CSS (CDN for simplicity).

### Pages:

**Dashboard** `/dashboard`
- Stats cards: Total jobs, prospects, drafts ready, last scrape
- Recent activity timeline
- Quick action buttons

**Jobs** `/jobs`
- Table: Title, Platform, Match Score, Budget, Status
- Filters: platform, score range, status, search
- Click for detail view with description, skills, draft button

**Prospects** `/prospects`
- Table: Company, Contact, Email, LinkedIn, Score, Source
- Filters: source, score, industry, search
- Click for detail with notes, linked drafts

**Drafts** `/drafts`
- List of generated drafts grouped by prospect
- Each: email subject, full email body (copy button), LinkedIn message (copy button)
- Status toggle: mark as sent/replied
- "Copy email" and "Copy LinkedIn message" buttons

**Settings** `/settings`
- Edit user profile (name, title, summary, skills)
- Portfolio URLs
- Search queries management (add/edit/delete)
- API keys (OpenAI/Anthropic)

### Design:
- Tailwind CSS with a clean, modern theme
- Dark/light mode toggle
- Responsive (works on mobile)
- Copy-to-clipboard with visual feedback

---

## 10. Project Structure

```
E:\Desktop\ggh\
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── cli.py                  # Click CLI commands
│   ├── config.py               # Pydantic settings
│   ├── database.py             # SQLAlchemy engine + session
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic schemas
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py             # Base agent class
│   │   ├── web_search.py       # Web Search Agent (dynamic)
│   │   ├── job_scraper.py      # Known platform scrapers
│   │   ├── client_discovery.py # LinkedIn, Crunchbase, etc.
│   │   ├── matcher.py          # Skill Matcher Agent
│   │   └── outreach.py         # Outreach Draft Agent
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py             # Base scraper
│   │   ├── upwork.py
│   │   ├── fiverr.py
│   │   ├── freelancer.py
│   │   ├── indeed.py
│   │   ├── linkedin.py
│   │   ├── crunchbase.py
│   │   ├── wellfound.py
│   │   └── company_pages.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py           # OpenAI/Anthropic client
│   │   └── prompts.py          # All LLM prompts
│   ├── templates/
│   │   ├── base.html           # Base template with Tailwind
│   │   ├── dashboard.html
│   │   ├── jobs.html
│   │   ├── prospects.html
│   │   ├── drafts.html
│   │   └── settings.html
│   └── static/
│       ├── style.css           # Custom styles
│       └── script.js           # UI interactions
├── config/
│   ├── queries.yml             # Web search queries
│   └── companies.yml           # Company watchlist
├── outputs/                    # Exported drafts, logs
├── .env                        # API keys (not committed)
├── pyproject.toml              # Dependencies + scripts
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-06-01-freelancing-os-design.md
```

---

## 11. Dependencies

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]",
    "sqlalchemy>=2.0",
    "aiosqlite",
    "playwright",
    "beautifulsoup4",
    "httpx",
    "openai",           # LLM for matching + drafts
    "anthropic",        # Alternative LLM
    "googlesearch-python",  # Dynamic web search
    "jinja2",
    "pydantic>=2.0",
    "pydantic-settings",
    "python-dotenv",
    "click",
    "pyyaml",
]
```

---

## 12. Error Handling & Resilience

- **Scraper timeouts**: 30s per page, retry once, log failure
- **LLM failures**: Fallback to template-based drafts if API unavailable
- **Playwright crashes**: Auto-restart browser instance
- **Rate limiting**: 2s delay between requests, rotating user-agents
- **Duplicate detection**: Jobs/prospects deduped by URL
- **Session logging**: Every scrape run logged with status and error info

---

## 13. Future Enhancements (not in v1)

- Automated LinkedIn messaging via Playwright
- Email sending integration (draft → send)
- Outreach pipeline CRM (follow-up reminders)
- Weekly email report of new opportunities
- Chrome extension for one-click prospect saving
