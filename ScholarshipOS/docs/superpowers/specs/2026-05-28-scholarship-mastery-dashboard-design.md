# Scholarship Mastery Dashboard — Design Spec

## Overview

A dedicated "Scholarship Mastery" panel within the existing ScholarAI dashboard, providing deep-dive guidance for 8 target scholarships. Each scholarship gets a comprehensive info cloud with step-by-step application guidance, successful applicant profiles, tips & tricks, and interactive progress tracking.

## Target Scholarships

1. Erasmus Mundus Joint Masters (EMJM)
2. DAAD Development-Related Postgraduate Scholarship
3. Fulbright Foreign Student Program (Bangladesh)
4. Commonwealth Masters Scholarships
5. Eiffel Excellence Scholarship
6. Chevening Scholarships
7. Australian Government Research Training Program (RTP)
8. Italian Government Scholarships (MAECI)

## Architecture

### Approach: SQLite + Background Workers + Full CRUD

- **Database**: SQLite at `data/mastery.db` (no new dependencies — Python stdlib `sqlite3`)
- **Agent**: New `agents/mastery.py` for seeding + web scraping supplement
- **API**: New REST endpoints in `dashboard/app.py`
- **Frontend**: New Vue component `ScholarshipMastery.vue` as sidebar tab

### Data Flow

```
User opens Mastery tab
  → GET /api/mastery → loads all 8 scholarships from SQLite
  → User clicks a scholarship → GET /api/mastery/{slug} → full profile
  → User checks off steps → POST /api/mastery/{slug}/checklist → updates DB
  → User triggers rescan → POST /api/mastery/scan → background thread scrapes
  → GET /api/mastery/scan-status → poll progress
```

---

## Data Model (SQLite)

### Table: `scholarships`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | INTEGER | PK AUTOINCREMENT | |
| slug | TEXT | UNIQUE NOT NULL | URL-friendly (e.g., `erasmus-mundus`) |
| name | TEXT | NOT NULL | Full display name |
| country | TEXT | | Host country |
| provider | TEXT | | Scholarship provider |
| coverage_type | TEXT | | Full-Ride / Partial |
| coverage_details | TEXT | | Full coverage description |
| amount | TEXT | | Monetary value |
| currency | TEXT | | EUR/USD/GBP/etc |
| degree_level | TEXT | | MSc/Masters |
| target_fields | TEXT | | ML, AI, Data Science, etc |
| eligibility_nationality | TEXT | | Who can apply |
| eligibility_academics | TEXT | | GPA/degree requirements |
| eligibility_experience | TEXT | | Work experience requirements |
| required_documents | TEXT | | JSON array of documents |
| application_fee | TEXT | | Fee or "None" |
| application_language | TEXT | | English/German/etc |
| english_test_required | TEXT | | IELTS/TOEFL details |
| gre_required | TEXT | | GRE/GMAT details |
| deadline_start | TEXT | | When applications open |
| deadline_end | TEXT | | When applications close |
| duration | TEXT | | Program duration |
| interview_required | TEXT | | Yes/No/Possible |
| competitiveness | TEXT | | Acceptance rate info |
| application_portal | TEXT | | URL to apply |
| official_url | TEXT | | Official website |
| notification_date | TEXT | | When you hear back |
| match_score | INTEGER | | Fit score 0-100 |
| strategy_notes | TEXT | | Strategy tips for this scholarship |
| last_updated | TIMESTAMP | | Last scrape time |

### Table: `scholarship_steps`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | INTEGER | PK AUTOINCREMENT | |
| scholarship_id | INTEGER | FK → scholarships.id | |
| step_number | INTEGER | NOT NULL | Order |
| phase | TEXT | NOT NULL | "Preparation", "Application", "Post-Application" |
| title | TEXT | NOT NULL | Step name |
| description | TEXT | | Detailed instructions |
| timeline | TEXT | | "6 months before deadline" |
| tips | TEXT | | Tips for this step |
| is_critical | BOOLEAN | DEFAULT 0 | Must-do step |

### Table: `successful_applicants`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | INTEGER | PK AUTOINCREMENT | |
| scholarship_id | INTEGER | FK → scholarships.id | |
| name | TEXT | | Anonymized name |
| background | TEXT | | Education, GPA, university |
| country | TEXT | | Home country |
| field_of_study | TEXT | | What they studied |
| work_experience | TEXT | | Professional background |
| publications | TEXT | | Papers (if any) |
| test_scores | TEXT | | IELTS/GRE scores |
| application_strategy | TEXT | | How they applied |
| what_worked | TEXT | | Key success factors |
| advice | TEXT | | Their advice |
| source_url | TEXT | | Where info came from |

### Table: `tips_and_tricks`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | INTEGER | PK AUTOINCREMENT | |
| scholarship_id | INTEGER | FK → scholarships.id | |
| category | TEXT | NOT NULL | "Writing", "Interview", "Documents", "Timing", "General" |
| tip | TEXT | NOT NULL | The tip content |
| priority | TEXT | | "high", "medium", "low" |

### Table: `checklist_progress`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | INTEGER | PK AUTOINCREMENT | |
| scholarship_id | INTEGER | FK → scholarships.id | |
| step_id | INTEGER | FK → scholarship_steps.id | |
| completed | BOOLEAN | DEFAULT 0 | Done status |
| completed_at | TIMESTAMP | | When marked done |
| notes | TEXT | | User notes |

---

## Backend

### New File: `agents/mastery.py`

```python
class MasteryAgent(BaseAgent):
    """Deep research agent for the 8 target scholarships."""

    TARGET_SCHOLARSHIPS = [
        "Erasmus Mundus Joint Masters",
        "DAAD Development-Related Postgraduate",
        "Fulbright Foreign Student Program Bangladesh",
        "Commonwealth Masters Scholarships",
        "Eiffel Excellence Scholarship",
        "Chevening Scholarships",
        "Australian Government Research Training Program",
        "Italian Government Scholarships MAECI",
    ]

    def seed_database(self):
        """Insert all hardcoded baseline data into SQLite."""

    def scrape_applicant_stories(self, scholarship_name):
        """Search web for successful applicant profiles, insert into DB."""

    def scrape_tips(self, scholarship_name):
        """Search web for tips and tricks, insert into DB."""

    def run_full_scan(self, progress_callback=None):
        """Seed if empty, then scrape all scholarships."""
```

**Seed data** includes:
- Full scholarship details (coverage, eligibility, deadlines, etc.)
- 5-8 step-by-step application instructions per scholarship
- 3-5 successful applicant profiles per scholarship (compiled from Reddit, blogs, forums)
- 5-10 categorized tips per scholarship

**Scrape supplement** searches for:
- `"[scholarship name] successful applicant background reddit"`
- `"[scholarship name] tips application blog"`
- `"[scholarship name] how I got accepted"`
- Parses results and inserts new records

### New API Endpoints (in `dashboard/app.py`)

| Method | Endpoint | Request | Response |
|--------|----------|---------|----------|
| GET | `/api/mastery` | — | List of 8 scholarships with summary + progress % |
| GET | `/api/mastery/{slug}` | — | Full profile: scholarship + steps + applicants + tips |
| GET | `/api/mastery/{slug}/checklist` | — | Checklist items with completion status |
| POST | `/api/mastery/{slug}/checklist` | `{ step_id, completed, notes }` | Updated checklist |
| POST | `/api/mastery/scan` | — | `{ status: "started" }` |
| GET | `/api/mastery/scan-status` | — | `{ running, progress, done }` |

### Database Module: `storage/mastery_db.py`

```python
class MasteryDB:
    def __init__(self, db_path="data/mastery.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def init_tables(self):
        """Create tables if they don't exist."""

    def get_all_scholarships(self):
        """Return all 8 scholarships with summary info."""

    def get_scholarship(self, slug):
        """Return full profile including steps, applicants, tips."""

    def get_checklist(self, scholarship_id):
        """Return checklist progress for a scholarship."""

    def update_checklist_item(self, scholarship_id, step_id, completed, notes=None):
        """Mark a checklist item complete/incomplete."""

    def insert_scholarship(self, data):
        """Insert or update a scholarship."""

    def insert_steps(self, scholarship_id, steps):
        """Insert step-by-step instructions."""

    def insert_applicant(self, scholarship_id, applicant):
        """Insert a successful applicant profile."""

    def insert_tip(self, scholarship_id, tip):
        """Insert a tip."""
```

---

## Frontend

### New Component: `frontend/src/components/ScholarshipMastery.vue`

**Sidebar tab entry**:
```javascript
{ id: 'mastery', name: 'Scholarship Mastery', icon: '🎯' }
```

**Layout structure**:
```
ScholarshipMastery (root)
├── MasteryHeader (title + rescan button + overall progress)
├── ScholarshipMasteryCard (×8, one per scholarship)
│   ├── CardHeader (name, country, match score, progress bar)
│   └── SubTabs
│       ├── OverviewTab (full scholarship details)
│       ├── StepsTab (interactive checklist with phases)
│       ├── ApplicantsTab (successful applicant profiles)
│       └── TipsTab (categorized tips with priorities)
```

**Sub-tabs per scholarship**:

1. **Overview** — Reuses data from existing scholarship display but with more detail. Shows coverage, eligibility, deadlines, portal links, required documents.

2. **Steps** — Interactive checklist grouped by phase:
   - Phase 1: Preparation (6-12 months before)
   - Phase 2: Application (3-6 months before)
   - Phase 3: Submission (final month)
   - Phase 4: Post-Application (after submitting)
   
   Each step has a checkbox, description, tips, and timeline. Progress bar updates in real-time.

3. **Applicants** — Cards showing successful applicant profiles:
   - Background (education, GPA, university)
   - Test scores
   - Work experience
   - Publications
   - Application strategy
   - What worked / advice
   - Source link

4. **Tips** — Categorized tips with priority badges:
   - Writing (motivation letter, research proposal)
   - Interview (preparation, common questions)
   - Documents (CV format, transcript tips)
   - Timing (when to apply, early bird advantages)
   - General (miscellaneous advice)

**Styling**: Follows existing dark theme with glassmorphism. Uses same CSS variables (`--bg-primary`, `--card-bg`, `--border-color`, etc.). Consistent with `ScholarshipCard.vue` patterns.

### Modified File: `frontend/src/App.vue`

- Add `{ id: 'mastery', name: 'Scholarship Mastery', icon: '🎯' }` to `tabs` array
- Add corresponding tab pane in template
- Import `ScholarshipMastery` component
- Add mastery data to `data()` and `fetchData()`

---

## Implementation Steps

### Phase 1: Database Layer
1. Create `storage/mastery_db.py` with SQLite schema and CRUD operations
2. Create `agents/mastery.py` with seed data for all 8 scholarships
3. Seed the database on first run

### Phase 2: API Layer
4. Add mastery endpoints to `dashboard/app.py`
5. Add background scan thread for scraping
6. Test endpoints with curl/browser

### Phase 3: Frontend
7. Create `ScholarshipMastery.vue` component
8. Add sidebar tab and route in `App.vue`
9. Build the 4 sub-tabs (Overview, Steps, Applicants, Tips)
10. Implement checklist interactivity
11. Add rescan button with progress polling

### Phase 4: Polish
12. Add responsive design for mobile
13. Add loading states and error handling
14. Test full flow end-to-end

---

## Success Criteria

- [ ] 8 scholarships displayed with full details in dedicated tab
- [ ] Each scholarship has 5-8 step-by-step instructions
- [ ] Each scholarship has 3-5 successful applicant profiles
- [ ] Each scholarship has 5-10 categorized tips
- [ ] Interactive checklist works (mark complete, progress updates)
- [ ] Rescan button triggers background scrape for new applicant stories
- [ ] All data persisted in SQLite
- [ ] UI matches existing dark theme
- [ ] No regressions in existing functionality
