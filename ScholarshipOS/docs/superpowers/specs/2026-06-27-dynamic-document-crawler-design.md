# Dynamic Document Crawler Design

## Purpose
Auto-discover and collect real scholarship application documents (SOPs, CVs, recommendation letters) from across the internet — not limited to hardcoded repos or winners. Uses GitHub API + GROQ + recursive link crawling as primary discovery mechanisms, with web search as secondary fallback.

## Architecture

```
DynamicDocumentCrawler
  ├── Phase 1: GitHub Discovery
  ├── Phase 2: Link Crawling
  ├── Phase 3: GROQ Gap Analysis
  └── Phase 4: Classification & Enrichment
        │
        └── writes to data/scholar_documents.json
        └── maintains data/crawler_state.json
```

Single new file: `agents/dynamic_document_crawler.py`. No existing files modified unless search fallback in `base.py` needs minor improvement.

## Phase Details

### Phase 1: GitHub Discovery
- **Search** `api.github.com/search/repositories?q=...` with curated keywords:
  - `scholarship SOP`, `statement of purpose`, `scholarship documents`
  - `DAAD application`, `Fulbright SOP`, `Erasmus motivation letter`
  - `PhD application documents`, `graduate school application`
- **Filter** results: exclude repos already in `processed_github_repos` state set
- **Crawl** each new repo: list contents via GitHub Contents API, traverse directories
- **Classify** files by extension (`.pdf`, `.docx`, `.txt`, `.md`) + filename heuristics
- **Add** new documents with `discovered_by: "github_dynamic"`
- Rate limit: 60 req/hr (unauthenticated). Batch queries conservatively.

### Phase 2: Link Crawling
- For each newly discovered document URL, fetch the parent HTML page
- Extract all `<a href="...">` links
- Filter links: skip navigation, social media, ads. Keep blog posts, personal sites, Google Drive, GitHub, Medium.
- Crawl each filtered link (depth 1, max 5 links per source)
- Check each crawled page for document download links
- Deduplicate via URL normalization

### Phase 3: GROQ Gap Analysis
- Read current collection stats: count by document_type, scholarship, country
- Call GROQ with prompt asking: "What are we missing? Generate 5 search queries."
- Example GROQ prompt: `Collection has {stats}. Gaps: few CVs from Fulbright winners, no docs from Australia. Generate 5 web search queries to find these.`
- Run resulting queries through `BaseAgent.search_web()`
- Collect candidate URLs

### Phase 4: Classification & Enrichment
- For each candidate URL, fetch title + snippet via `fetch_page()`
- Call GROQ to extract structured metadata:
  ```json
  {
    "document_type": "sop|cv|recommendation|motivation_letter|study_plan|research_proposal",
    "scholarship": "Fulbright|DAAD|Erasmus|...",
    "country": "Bangladesh|India|Pakistan|...",
    "quality_score": 1-5,
    "is_real_document": true|false
  }
  ```
- Add document if `quality_score >= 3` and `is_real_document == true`
- Use existing `_is_actual_document()` filter from `document_collector.py`

## State Management (`data/crawler_state.json`)
```json
{
  "processed_github_repos": ["owner/repo1", "owner/repo2"],
  "processed_urls": ["https://..."],
  "github_queries_run": ["scholarship SOP"],
  "stats_before": {"sop": 57, "cv": 4, ...},
  "stats_after": {"sop": 62, "cv": 6, ...},
  "phase_progress": "idle|github_discovery|link_crawling|gap_analysis|done"
}
```
Resumable: if interrupted, skip already-processed items on restart.

## Integration Points
- Writes to `data/scholar_documents.json` using same `_gen_id()` ID scheme
- Reuses `BaseAgent.search_web()` for web search fallback
- Reuses `_is_actual_document()` filter from `document_collector.py`
- New documents get a `discovered_by` field for provenance tracking
- Testable via: `python -c "from agents.dynamic_document_crawler import DynamicDocumentCrawler; DynamicDocumentCrawler().run(github_only=True)"`

## Constraints
- No paid APIs. GitHub API 60 req/hr without token.
- GROQ API calls limited to ~20 per run (classification + query gen).
- DuckDuckGo HTML endpoint blocked — Bing/Google fallback is slow.
- `professors.json` has 0 relative scholar URLs (confirmed).
- `build_professors()` dedup bug is already fixed.

## Success Criteria
1. Discovers at least 5 new GitHub repos with real scholarship docs on first full run
2. Classifies and adds at least 20 new documents per run
3. Zero regressions in existing `data/scholar_documents.json` entries
4. Resumable: crash mid-run, restart picks up where it left off
