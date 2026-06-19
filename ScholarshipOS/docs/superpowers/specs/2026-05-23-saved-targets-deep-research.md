# Saved Targets Deep Research Enhancement

## Motivation

The existing saved targets system follows scholarships, universities, and professors but only extracts basic fields (amount, deadline, tuition). Users need comprehensive detail collection from official pages to make informed application decisions without manually browsing each site.

## Data Model — New Fields

### Scholarships (7 new fields)

| Field | Extraction Method | Example Value |
|-------|-------------------|---------------|
| `application_portal` | URL extraction from page | `https://portal.daad.de/` |
| `contact_email` | Email regex on page | `scholarships@daad.de` |
| `selection_criteria` | Text near "selection criteria" | "Academic merit, motivation, development relevance" |
| `success_rate` | Percentage near "awarded"/"applicants" | "~5% acceptance rate" |
| `number_of_awards` | "up to X" pattern | "Up to 200 scholarships per year" |
| `age_limit` | "age" + number pattern | "Age limit: 36 years" |
| `bond_requirement` | "return" / "home country" pattern | "Must return to home country for 2 years" |
| `funding_specifics` | Tuition + stipend + travel breakdown | "€992 monthly stipend + travel + insurance" |
| `eligible_nationalities` | Country list / "developing countries" | "Bangladesh, India, Pakistan, ..." |

### Universities (7 new fields)

| Field | Extraction Method | Example Value |
|-------|-------------------|---------------|
| `acceptance_rate` | "acceptance" + percentage | "~8% acceptance rate" |
| `ra_ta_positions` | "teaching assistant" / "research assistant" | "HiWi positions available (10-12 hrs/week)" |
| `cost_of_living_monthly` | Currency + number + "/month" | "~€934/month (Munich)" |
| `housing_options` | "dormitory" / "housing" / "accommodation" | "Student dormitories: €400-600/month" |
| `program_structure` | "thesis" / "coursework" / "project" | "4 semesters: 3 coursework + 1 thesis" |
| `prerequisite_courses` | "prerequisite" / "previous coursework" | "60 ECTS in CS or related field" |
| `department_contact` | Email + phone patterns | "cs-admissions@tum.de" |

### Professors (4 new fields)

| Field | Extraction Method | Example Value |
|-------|-------------------|---------------|
| `open_positions` | "open positions" / "hiring" / "join" | "2 PhD positions available for 2025" |
| `lab_website` | Link extraction near "lab" / "group" | `https://ml.inf.ethz.ch/` |
| `past_phd_students` | Alumni/people list | "5 PhD graduates, 3 now professors" |
| `research_projects` | "projects" / "research" section | "ELLIS, DFG priority program" |

## Enhanced Agent Pipeline

### Search Strategy

- **Scholarships**: Search 5 results (up from 3) with query:
  `"{name} official application requirements deadline eligibility coverage funding"`
  Scrape all available URLs.

- **Universities**: Run 2 queries per university:
  1. `"{name} {program} admission requirements tuition fees deadlines"` (3 results)
  2. `"{name} cost of living acceptance rate"` (3 results)
  Scrape up to 5 unique URLs total.

- **Professors**: Scrape lab website + personal page + Google Scholar.
  Extract openings, lab info, past students from lab/personal page.

### Extraction Logic — Enhanced Regex Patterns

**Scholarships** (`ScholarshipResearcherAgent.parse_scholarship_text()`):
- Add `selection_criteria`: look for text blocks after "Selection criteria" / "How we select" headers
- Add `success_rate`: `(\d+)[%]?\s*(?:acceptance|success rate|awarded|selected)`
- Add `number_of_awards`: `(?:up to|approximately)\s*(\d+)\s*(?:scholarships|awards|fellowships)`
- Add `age_limit`: `(?:age\s*limit|maximum\s*age|aged?\s*(\d+))`
- Add `bond_requirement`: check for "return to home country" / "bond" / "serve"
- Enhance `funding_specifics`: capture all euro/USD amounts with per-month/per-year context

**Universities** (`UniversityResearcherAgent.parse_university_text()`):
- Add `acceptance_rate`: `(?:acceptance|admission)\s*(?:rate)?\s*[:\-]?\s*([\d.]+)[%]`
- Add `ra_ta_positions`: presence of "HiWi" / "teaching assistant" / "research assistant" + details
- Add `cost_of_living_monthly`: `(?:€|EUR)\s*(\d{3,4})\s*(?:per\s*month|/month|monthly)`
- Add `housing_options`: capture text near "dormitory" / "accommodation" / "housing"
- Add `program_structure`: detect "semester" counts + "thesis"/"coursework" balance
- Add `prerequisites`: capture text after "requirement" / "prerequisite" / "previous degree"
- Add `department_email`: email regex scoped to university domain

**Professors** (`ProfessorResearcherAgent.parse_professor_text()`):
- Add `open_positions`: search for "PhD"/"postdoc"/"position" + "open"/"available"
- Add `lab_website`: extract link containing "lab"/"group"/"institute" from page
- Add `past_phd_students`: "PhD"/"graduate" + "alumni" section text
- Add `research_projects`: capture text after "current projects" / "research projects"

### Pipeline Integration

The `SavedTargetsResearchManager.run_priority_research()` continues to orchestrate all three agent types. Changes:

1. Scholarship search query enhanced, 5 results instead of 3
2. University research runs 2 queries sequentially per university
3. All new fields merged into corresponding JSON stores
4. Existing field overwrite rules preserved (placeholder check, only overwrite empty/generic)

## API & Frontend

### New API Endpoint

```
POST /api/enrich-saved
  → Returns {"status": "started"}
  → Runs SavedTargetsResearchManager.run_priority_research() in background thread
  → Same pattern as existing POST /api/scan
GET /api/enrich-saved-status
  → Returns {"running": bool, "progress": str, "done": bool}
```

### Frontend: FollowingSection.vue

- Add "Enrich Saved Targets" button above the saved items
- Button triggers `POST /api/enrich-saved`, polls `/api/enrich-saved-status`
- Shows progress text during enrichment
- Upon completion, re-fetches `/api/data` to show new fields

### Frontend: Card Displays

Each card type gets additional meta rows for new enriched fields:

- **Scholarship cards**: show selection criteria, success rate, funding breakdown, age limit, bond
- **University cards**: show acceptance rate, RA/TA availability, cost of living, housing, program structure
- **Professor cards**: show open positions, lab website, research projects

New fields shown only if non-empty (v-if guards).

## Scope

**In scope**: Agent extraction logic, new fields, pipeline changes, API endpoint, frontend display.
**Out of scope**: LLM integration, database migration, multi-user auth, automated scheduling.

## Success Criteria

1. Running scan triggers deep enrichment on all 3 saved universities, 2 saved scholarships, 9 professors
2. scholarships.json contains new fields populated for DAAD and Erasmus Mundus
3. universities.json contains acceptance rate, cost of living, housing for TUM, NUS, ETH Zurich
4. professors.json contains open positions, lab website for followed professors
5. Frontend "Enrich Saved Targets" button triggers background job and refreshes data
