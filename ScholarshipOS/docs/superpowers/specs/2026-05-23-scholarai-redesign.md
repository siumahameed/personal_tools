# ScholarAI Redesign — Vue 3 Frontend + Enhanced Scan Engine

## Overview

Full redesign of ScholarAI's user interface and scan workflow. Flask becomes a pure JSON API backend. A Vue 3 + Vite frontend serves a modern, clean dashboard. The scan engine is enhanced to deep-scrape followed professors' research papers and prioritize followed items on re-scan.

## Architecture

```
Vue 3 + Vite (frontend/)  ──HTTP JSON──>  Flask API (dashboard/app.py)
                                              │
                                    ┌─────────┴──────────┐
                                    │  Agents & Features  │
                                    │  PaperScraper (new) │
                                    └─────────┬──────────┘
                                              │
                                    ┌─────────▼──────────┐
                                    │  Google Sheets      │
                                    │  + local JSON       │
                                    └────────────────────┘
```

- Flask serves **only JSON** at `/api/*` — no HTML templates
- Vue 3 dev server proxies `/api` to Flask during development
- Production: Vue build output served by Flask as static files

## Google Sheets Layout

| Worksheet | Content | Append Behavior |
|-----------|---------|-----------------|
| `Scholarships` | All scholarship data | Append rows each scan |
| `Professors` | All professor data + paper links | Append rows each scan |
| `Universities` | All university data | Append rows each scan |
| `Following` | Loved/followed items with timestamps | Append on toggle |
| `Updates Log` | Scan history, timestamps, item counts | Append each scan |

Every row includes a `Scan Timestamp` column for traceability.

## Frontend (Vue 3 + Vite)

### Tabs
1. **Dashboard** — Match scores, timeline, quick stats, last scan time
2. **Scholarships** — Full scholarship list with expandable details, search/filter
3. **Professors** — Professor list with research paper links (basic), expandable details
4. **Following** — Only loved scholarships & professors. Shows deep paper links for followed professors

### Components
- `NavBar.vue` — Top navigation with brand + profile info
- `ScholarshipCard.vue` — Card with expandable details, heart toggle, match badge
- `ProfessorCard.vue` — Card with research interests, expandable, heart toggle, paper links
- `FollowingSection.vue` — Aggregated view of all loved items
- `ScanButton.vue` — Trigger scan with progress indicator
- `DetailModal.vue` — Full info modal when clicking into an item
- `PaperList.vue` — List of paper links with title, venue, year, DOI/PDF

### Detail Views
Every scholarship card expands to show: country, provider, coverage, amount, deadline, eligibility, documents, language, GRE, duration, strategy, official link, match score.

Every professor card expands to show: title, email, department, research interests, h-index, funding, courses, strategy. Research paper section shows links (basic for all, deep for followed).

## PaperScraper (New Feature)

### Behavior
- When a professor is marked as "followed", on the next scan:
  1. Visit their Google Scholar URL
  2. Extract top 10 paper titles, years, venues, and PDF/DOI links
  3. Store in Google Sheets `Professors` worksheet with timestamp
- For non-followed professors: basic info only (Google Scholar link, h-index)

### Scraping approach
- Use requests + BeautifulSoup (existing infrastructure)
- Parse Google Scholar profile page for paper entries
- Extract: title, authors, venue, year, citation count, PDF link
- Handle rate limiting with delays between requests

## Scan Workflow (Enhanced)

```
1. Load followed list from JSON
2. Deep scan: For each followed professor → PaperScraper
3. Deep scan: For each followed scholarship → web search for updates
4. General scan: Discover new scholarships (same as now)
5. General scan: Discover new professors (same as now)
6. Append ALL data to Google Sheets in sequence with timestamps
7. Log scan to Updates Log worksheet
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/data` | GET | All scholarships, professors, universities, scores, timeline, followed |
| `/api/scan` | POST | Trigger new scan |
| `/api/scan-status` | GET | Current scan progress |
| `/api/followed` | GET/POST | Get/set followed items |
| `/api/scholarship/<name>` | GET | Single scholarship full detail |
| `/api/professor/<email>` | GET | Single professor full detail |
| `/api/professor/<email>/papers` | GET | Deep paper links for a professor |
| `/api/match-scores` | GET | Match score calculations |
| `/api/timeline` | GET | Application timeline |

## Files Changed / Created

### New files
- `frontend/package.json` — Vue 3 + Vite dependencies
- `frontend/vite.config.js` — Vite config with proxy to Flask
- `frontend/index.html` — App entry point
- `frontend/src/App.vue` — Root component with tab navigation
- `frontend/src/components/*.vue` — All UI components (8-10 files)
- `features/paper_scraper.py` — PaperScraper class

### Modified files
- `dashboard/app.py` — Strip HTML, convert to pure JSON API; add paper scraper endpoint
- `config.py` — Add paper scraper config if needed
- `orchestrator.py` — Enhanced scan workflow with deep-follow logic
- `requirements.txt` — Add CORS for dev

### Removed
- `dashboard/templates/base.html` — No longer needed (Vue handles UI)

## Design Constraints

- No build step for users: `python main.py --web` still works, Vue is pre-built or proxied
- Google Sheets data is append-only, never overwritten
- Follow state stored in local `data/followed.json` (fast reads)
- Throttle Google Scholar scraping to avoid being blocked
- Mobile-responsive Vue UI
