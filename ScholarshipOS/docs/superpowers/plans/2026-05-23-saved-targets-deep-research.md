# Saved Targets Deep Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the 3 research agents (scholarship, university, professor) to extract comprehensive details from official pages for saved targets.

**Architecture:** Expand existing `SavedTargetsResearchManager` pipeline with more search results, more regex extraction patterns, and more fields per item type. Add on-demand API endpoint. Display new fields in frontend.

**Tech Stack:** Python 3 (BeautifulSoup, regex), Vue 3, FastAPI

**Files to modify:**
- `agents/target_researchers.py` — extraction logic for all 3 agents
- `dashboard/app.py` — API endpoints, data builder mappings
- `frontend/src/components/FollowingSection.vue` — enrich button, new field display

---

### Task 1: Enhanced Scholarship Researcher Agent

**Files:**
- Modify: `agents/target_researchers.py:29-164`

- [ ] **Step 1: Write tests for scholarship extraction**

Create file `tests/test_scholarship_researcher.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.target_researchers import ScholarshipResearcherAgent

agent = ScholarshipResearcherAgent()

SAMPLE_TEXT = """
DAAD Development-Related Postgraduate Scholarship
Selection Criteria: Academic qualification, motivation, development relevance of the project.
Success rate: approximately 3% of applicants are awarded each year.
Up to 200 scholarships are awarded annually.
Age limit: 36 years at the time of application.
Candidates must return to their home country after completion of studies.
Monthly stipend of 992 EUR plus travel allowance and health insurance.
Eligible nationalities: Bangladesh, India, Pakistan, Nepal, Sri Lanka.
Application portal: https://www.daad.de/en/apply/
Contact: scholarships@daad.de
"""

def test_scholarship_extracts_selection_criteria():
    result = agent.parse_scholarship_text(SAMPLE_TEXT)
    assert "selection criteria" in str(result).lower() or "Academic qualification" in str(result)

def test_scholarship_extracts_success_rate():
    result = agent.parse_scholarship_text(SAMPLE_TEXT)
    assert "3%" in str(result) or "3 %" in str(result)

def test_scholarship_extracts_number_of_awards():
    result = agent.parse_scholarship_text(SAMPLE_TEXT)
    assert "200" in str(result)

def test_scholarship_extracts_age_limit():
    result = agent.parse_scholarship_text(SAMPLE_TEXT)
    assert "36" in str(result)

def test_scholarship_extracts_bond():
    result = agent.parse_scholarship_text(SAMPLE_TEXT)
    assert "return" in str(result).lower()

def test_scholarship_extracts_funding_details():
    result = agent.parse_scholarship_text(SAMPLE_TEXT)
    assert "992" in str(result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scholarship_researcher.py -v`
Expected: all 6 FAIL with AssertionError

- [ ] **Step 3: Enhance search query and result count**

In `agents/target_researchers.py`, modify `ScholarshipResearcherAgent.research()`:

Change `search_web(query, num_results=3)` to `search_web(query, num_results=5)`

Update the query to:
```python
query = f"{name} official application requirements deadline eligibility coverage funding selection criteria"
```

- [ ] **Step 4: Add new extraction fields to parse_scholarship_text()**

In `agents/target_researchers.py`, update `ScholarshipResearcherAgent.parse_scholarship_text()`.

Add after the existing `# 8. Strategy Notes summary` block:

```python
        # 9. Selection Criteria
        criteria_match = re.search(
            r'(?:selection\s*criteria|how\s*we\s*select|evaluation\s*criteria)\s*:?\s*(.*?)(?:\n\s*\n|\Z)',
            text, re.IGNORECASE | re.DOTALL
        )
        if criteria_match:
            info["Selection Criteria"] = criteria_match.group(1).strip()[:200]

        # 10. Success Rate
        rate_match = re.search(
            r'(?:approximately|about|around|~)\s*(\d+(?:\.\d+)?)\s*[%]\s*(?:of\s*applicants|acceptance|success|awarded|selected)',
            text, re.IGNORECASE
        )
        if not rate_match:
            rate_match = re.search(
                r'(\d+(?:\.\d+)?)\s*[%]\s*(?:acceptance|success|awarded|selected)',
                text, re.IGNORECASE
            )
        if rate_match:
            info["Success Rate"] = f"{rate_match.group(1)}%"

        # 11. Number of Awards
        awards_match = re.search(
            r'(?:up\s*to|approximately|about)\s*(\d[\d,]*)\s*(?:scholarships|awards|fellowships|grants|positions)',
            text, re.IGNORECASE
        )
        if awards_match:
            info["Number of Awards"] = awards_match.group(1).replace(",", "")

        # 12. Age Limit
        age_match = re.search(
            r'(?:age\s*limit|maximum\s*age|aged?\s*at\s*most|under\s*the\s*age\s*of)\s*:?\s*(\d{2})',
            text, re.IGNORECASE
        )
        if age_match:
            info["Age Limit"] = f"{age_match.group(1)} years"

        # 13. Bond / Return Requirement
        bond_patterns = [
            r'return\s+to\s+(?:their\s+)?(?:home\s+)?country',
            r'return\s+(?:to\s+)?(?:after\s+)?completion',
            r'obliged?\s+to\s+return',
            r'bond\s+(?:agreement|requirement)',
        ]
        for pat in bond_patterns:
            if re.search(pat, text, re.IGNORECASE):
                info["Bond / Return Requirement"] = "Must return to home country after studies"
                break

        # 14. Funding Specifics
        funding_items = []
        stipend_match = re.search(
            r'(?:€|EUR|euro|euros|USD|US\$|\$)\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s*month|/month|monthly)\s*(?:stipend|allowance)',
            text, re.IGNORECASE
        )
        if stipend_match:
            funding_items.append(f"Monthly stipend: {stipend_match.group(0)}")
        if "travel" in text_lower or "flights" in text_lower:
            funding_items.append("Travel expenses covered")
        if "health insurance" in text_lower or "medical insurance" in text_lower:
            funding_items.append("Health insurance covered")
        if "tuition" in text_lower and ("waiver" in text_lower or "free" in text_lower):
            funding_items.append("Tuition waiver")
        if funding_items:
            info["Funding Specifics"] = " | ".join(funding_items)

        # 15. Eligible Nationalities
        nat_match = re.search(
            r'(?:eligible\s*)?nationalit(?:y|ies)\s*:?\s*(.*?)(?:\.|$)(?:\s|$)',
            text, re.IGNORECASE
        )
        if nat_match:
            info["Eligible Nationalities"] = nat_match.group(1).strip()[:200]

        # 16. Application Portal
        portal_match = re.search(
            r'(?:application\s*portal|apply\s*(?:here|online|now)|online\s*application)\s*:?\s*(https?://[^\s]+)',
            text, re.IGNORECASE
        )
        if portal_match:
            info["Application Portal"] = portal_match.group(1).strip()

        # 17. Contact Email
        emails_found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if emails_found:
            valid_emails = [e for e in emails_found if "ref" not in e and "webmaster" not in e and "support" not in e]
            if valid_emails:
                info["Contact Email"] = valid_emails[0]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_scholarship_researcher.py -v`
Expected: all 6 PASS

- [ ] **Step 6: Commit**

```bash
git add tests/test_scholarship_researcher.py agents/target_researchers.py
git commit -m "feat: enhance scholarship researcher with 9 new extraction fields"
```

---

### Task 2: Enhanced University Researcher Agent

**Files:**
- Modify: `agents/target_researchers.py:167-278`

- [ ] **Step 1: Write tests for university extraction**

Create file `tests/test_university_researcher.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.target_researchers import UniversityResearcherAgent

agent = UniversityResearcherAgent()

SAMPLE_TEXT = """
Technical University of Munich - MSc Data Science
Acceptance rate: approximately 8% of applicants are admitted.
RA/TA positions: HiWi positions available for 10-12 hours per week.
Cost of living: approximately 934 EUR per month in Munich.
Housing options: Student dormitories available from 400-600 EUR per month.
Program structure: 4 semesters consisting of 3 coursework semesters and 1 master thesis semester.
Prerequisites: 60 ECTS in computer science or related field, strong mathematics background.
Department contact: admissions@cs.tum.edu, +49 89 289 12345.
"""

def test_university_extracts_acceptance_rate():
    result = agent.parse_university_text(SAMPLE_TEXT)
    assert "8%" in str(result)

def test_university_extracts_ra_ta():
    result = agent.parse_university_text(SAMPLE_TEXT)
    assert "HiWi" in str(result) or "teaching assistant" in str(result).lower()

def test_university_extracts_cost_of_living():
    result = agent.parse_university_text(SAMPLE_TEXT)
    assert "934" in str(result) or "EUR" in str(result)

def test_university_extracts_housing():
    result = agent.parse_university_text(SAMPLE_TEXT)
    assert "dormitor" in str(result).lower() or "housing" in str(result).lower()

def test_university_extracts_program_structure():
    result = agent.parse_university_text(SAMPLE_TEXT)
    assert "semester" in str(result).lower()

def test_university_extracts_prerequisites():
    result = agent.parse_university_text(SAMPLE_TEXT)
    assert "ECTS" in str(result) or "prerequisite" in str(result).lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_university_researcher.py -v`
Expected: all 6 FAIL

- [ ] **Step 3: Add second search query for universities**

In `agents/target_researchers.py`, modify `UniversityResearcherAgent.research()`:

```python
def research(self, name, program, current_data):
    self.log(f"Starting deep search for followed university program: {name} - {program}")

    # Query 1: Admissions & program details
    query1 = f"{name} {program} application deadline tuition requirements IELTS TOEFL GRE GPA"
    search_results1 = self.search_web(query1, num_results=3)

    # Query 2: Cost & acceptance rate
    query2 = f"{name} {program} acceptance rate cost of living student housing"
    search_results2 = self.search_web(query2, num_results=3)

    all_results = (search_results1 or []) + (search_results2 or [])
    if not all_results:
        self.log("  No search results found.")
        return {}

    combined_text = ""
    urls_visited = []
    seen_urls = set()
    for r in all_results:
        url = r.get("url")
        if url and url.startswith("http") and url not in seen_urls:
            seen_urls.add(url)
            self.log(f"  Scraping: {url[:60]}")
            soup = self.fetch_page(url)
            if soup:
                urls_visited.append(url)
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()
                combined_text += " " + soup.get_text(separator=" ")

    if not combined_text:
        self.log("  Failed to extract university page content.")
        return {}

    extracted = self.parse_university_text(combined_text)

    if urls_visited and is_placeholder(current_data.get("portal")):
        extracted["Application Portal / Platform"] = urls_visited[0]
    if urls_visited and len(urls_visited) > 1 and is_placeholder(current_data.get("dept_url")):
        extracted["Department / Faculty URL"] = urls_visited[1]

    return extracted
```

- [ ] **Step 4: Add new extraction fields to parse_university_text()**

In `agents/target_researchers.py`, update `UniversityResearcherAgent.parse_university_text()`.

Add after the existing `# 9. Program Duration` block:

```python
        # 10. Acceptance Rate
        rate_match = re.search(
            r'(?:acceptance|admission)\s*(?:rate)?\s*[:\-]?\s*(?:approximately|about|around|~)?\s*([\d.]+)\s*[%]',
            text, re.IGNORECASE
        )
        if rate_match:
            info["Acceptance Rate"] = f"{rate_match.group(1)}%"

        # 11. RA/TA Positions
        ra_ta = []
        if re.search(r'HiWi|teaching assistant|research assistant|student assistant|wissenschaftliche Hilfskraft', text, re.IGNORECASE):
            hours_match = re.search(r'(\d+)\s*(?:-?\s*\d+)?\s*(?:hours|hrs|h)\s*(?:per|/)\s*(?:week|wk)', text, re.IGNORECASE)
            if hours_match:
                ra_ta.append(f"Available ({hours_match.group(0)})")
            else:
                ra_ta.append("Available (check department)")
            info["RA/TA Positions"] = ", ".join(ra_ta)

        # 12. Cost of Living
        col_match = re.search(
            r'(?:cost\s*of\s*living|living\s*costs|living\s*expenses)\s*[:\-]?\s*(?:approximately|about|around|~)?\s*(?:€|EUR|euro)?\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s*month|/month|monthly)',
            text, re.IGNORECASE
        )
        if col_match:
            info["Cost of Living (Monthly)"] = f"€{col_match.group(1).replace(',', '')}/month"

        # 13. Housing Options
        housing_info = []
        dorm_match = re.search(
            r'(?:dormitor|housing|accommodation|studentwohnheim)\s*(?:ies|y|s)?\s*(?:are|is|:)?\s*(?:available|from)?\s*(?:€|EUR)?\s*(\d[\d.,]*)\s*(?:-|to)\s*(?:€|EUR)?\s*(\d[\d.,]*)\s*(?:per\s*month|/month)',
            text, re.IGNORECASE
        )
        if dorm_match:
            housing_info.append(f"Dormitories: {dorm_match.group(0)}")
        if re.search(r'private\s+housing|private\s+accommodation|wg|apartment', text, re.IGNORECASE):
            housing_info.append("Private housing available")
        if housing_info:
            info["Housing Options"] = " | ".join(housing_info)

        # 14. Program Structure
        struct_parts = []
        sem_count = re.search(r'(\d+)\s*semesters?', text_lower)
        if sem_count:
            struct_parts.append(f"{sem_count.group(1)} semesters")
        if re.search(r'thesis', text_lower):
            struct_parts.append("Thesis required")
        if re.search(r'coursework|course\s*work', text_lower):
            struct_parts.append("Coursework")
        if struct_parts:
            info["Program Structure"] = ", ".join(struct_parts)

        # 15. Prerequisite Courses
        prereq_match = re.search(
            r'(?:prerequisite|prerequisites|required\s*background|previous\s*(?:degree|coursework)|prior\s*knowledge)\s*[:\-]?\s*(.*?)(?:\.|$)(?:\s|$)',
            text, re.IGNORECASE
        )
        if prereq_match:
            prereq_text = prereq_match.group(1).strip()[:200]
            if prereq_text:
                info["Prerequisite Courses"] = prereq_text

        # 16. Department Contact
        dept_email = re.search(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:edu|de|ch|uk|sg|ca|au)\b',
            text
        )
        if dept_email:
            email_val = dept_email.group(0)
            if "admission" in email_val.lower() or "apply" in email_val.lower() or "info" in email_val.lower():
                info["Department Contact"] = email_val
            elif not info.get("Department Contact"):
                info["Department Contact"] = email_val
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_university_researcher.py -v`
Expected: all 6 PASS

- [ ] **Step 6: Commit**

```bash
git add tests/test_university_researcher.py agents/target_researchers.py
git commit -m "feat: enhance university researcher with 7 new extraction fields + dual query"
```

---

### Task 3: Enhanced Professor Researcher Agent

**Files:**
- Modify: `agents/target_researchers.py:281-388`

- [ ] **Step 1: Write tests for professor extraction**

Create file `tests/test_professor_researcher.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agents.target_researchers import ProfessorResearcherAgent

agent = ProfessorResearcherAgent()

SAMPLE_TEXT = """
Prof. Frank Hutter - Machine Learning Lab
Open Positions: We are hiring 2 PhD students and 1 postdoc for 2025.
Lab Website: https://ml.inf.ethz.ch/
Past PhD Students: 5 PhD graduates, 3 now professors at top universities.
Research Projects: ELLIS Unit, DFG Priority Program on Automated Machine Learning.
"""

def test_professor_extracts_open_positions():
    result = agent.parse_professor_text(SAMPLE_TEXT)
    assert "open" in str(result).lower() or "position" in str(result).lower() or "hiring" in str(result).lower()

def test_professor_extracts_lab_website():
    result = agent.parse_professor_text(SAMPLE_TEXT)
    assert "ml.inf.ethz.ch" in str(result)

def test_professor_extracts_past_students():
    result = agent.parse_professor_text(SAMPLE_TEXT)
    assert "PhD" in str(result) or "graduate" in str(result)

def test_professor_extracts_research_projects():
    result = agent.parse_professor_text(SAMPLE_TEXT)
    assert "ELLIS" in str(result) or "project" in str(result).lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_professor_researcher.py -v`
Expected: all 4 FAIL

- [ ] **Step 3: Enhance professor search + add new extraction fields**

Modify `ProfessorResearcherAgent.research()` — after the existing general web search, add a third search for lab/project info:

```python
        # 3. Lab and project research
        lab_query = f"{name} {university} lab research group projects"
        lab_results = self.search_web(lab_query, num_results=3)
        for r in lab_results:
            url = r.get("url")
            if url and url.startswith("http") and "scholar.google" not in url and url not in urls_visited:
                self.log(f"  Scraping lab page: {url[:60]}")
                soup = self.fetch_page(url)
                if soup:
                    urls_visited.append(url)
                    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        tag.decompose()
                    combined_text += " " + soup.get_text(separator=" ")
```

Update `parse_professor_text()` — add after the existing `# 4. Funding Available` block:

```python
        # 5. Open Positions
        pos_patterns = [
            r'(?:open\s*positions?|position[s]?\s*available|hiring|we\s*are\s*looking\s*for|join\s*(?:the\s*)?(?:lab|team|group))\s*[:\-]?\s*(.*?)(?:\.|$)(?:\s|$)',
            r'(\d+\s*(?:PhD|postdoc|master|student|research)\s*(?:position|opening))',
        ]
        for pat in pos_patterns:
            pos_match = re.search(pat, text, re.IGNORECASE)
            if pos_match:
                pos_text = pos_match.group(0).strip()[:200]
                if pos_text:
                    if "openings" in pos_text.lower() and not any(kw in str(info.get("Open Positions", "")).lower() for kw in ["openings", "hiring", "positions"]):
                        info["Open Positions"] = pos_text
                    elif "phd" in pos_text.lower() or "postdoc" in pos_text.lower() or "hiring" in pos_text.lower() or "position" in pos_text.lower():
                        info["Open Positions"] = pos_text
                    break

        # 6. Lab Website
        lab_url_match = re.search(
            r'(?:lab\s*website|group\s*website|lab\s*page|group\s*page)\s*[:\-]?\s*(https?://[^\s,;]+)',
            text, re.IGNORECASE
        )
        if not lab_url_match:
            lab_url_match = re.search(
                r'(https?://[^\s,;]+(?:lab|group|institute)[^\s,;]*)',
                text, re.IGNORECASE
            )
        if lab_url_match:
            candidate = lab_url_match.group(1).strip().rstrip(".)")
            if "scholar.google" not in candidate:
                info["Lab Website"] = candidate

        # 7. Past PhD Students / Alumni
        alumni_match = re.search(
            r'(?:past\s+(?:PhD|graduate|doctoral)\s+students?|alumni|former\s+(?:PhD|group)\s+members?)\s*[:\-]?\s*(.*?)(?:\.|$)(?:\s|$)',
            text, re.IGNORECASE
        )
        if alumni_match:
            info["Past PhD Students"] = alumni_match.group(1).strip()[:200]

        # 8. Research Projects
        proj_match = re.search(
            r'(?:current\s+projects?|research\s+projects?|active\s+projects?|funded\s+projects?)\s*[:\-]?\s*(.*?)(?:\.\s*(?:We|The|Our|I\s)|$)',
            text, re.IGNORECASE | re.DOTALL
        )
        if proj_match:
            proj_text = proj_match.group(1).strip()[:300]
            if proj_text and len(proj_text) > 10:
                info["Research Projects"] = proj_text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_professor_researcher.py -v`
Expected: all 4 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_professor_researcher.py agents/target_researchers.py
git commit -m "feat: enhance professor researcher with 4 new extraction fields + lab query"
```

---

### Task 4: API Endpoints for On-Demand Enrichment

**Files:**
- Modify: `dashboard/app.py`

- [ ] **Step 1: Add enrichment status tracking**

In `dashboard/app.py`, after the `SCAN_STATUS` block (around line 68):

```python
ENRICH_STATUS = {"running": False, "progress": "", "done": False}
ENRICH_LOCK = threading.Lock()

def set_enrich_progress(progress):
    with ENRICH_LOCK:
        ENRICH_STATUS["progress"] = progress

def set_enrich_done():
    with ENRICH_LOCK:
        ENRICH_STATUS["done"] = True
        ENRICH_STATUS["running"] = False
```

- [ ] **Step 2: Add enrichment runner function**

In `dashboard/app.py`, add before the API routes section:

```python
def run_enrich_saved():
    with ENRICH_LOCK:
        ENRICH_STATUS["running"] = True
        ENRICH_STATUS["progress"] = "Starting deep enrichment of saved targets..."
        ENRICH_STATUS["done"] = False
    try:
        from agents.target_researchers import SavedTargetsResearchManager
        mgr = SavedTargetsResearchManager(sheets_client)
        mgr.run_priority_research(set_progress_callback=set_enrich_progress)
        set_enrich_progress("Done! Enriched all saved targets.")
        set_enrich_done()
    except Exception as e:
        print(f"Enrichment error: {e}")
        set_enrich_progress(f"Error: {str(e)[:150]}")
        set_enrich_done()
    finally:
        with ENRICH_LOCK:
            ENRICH_STATUS["running"] = False
```

- [ ] **Step 3: Add /api/enrich-saved and /api/enrich-saved-status endpoints**

In `dashboard/app.py`, after the scan endpoints (around line 400):

```python
@app.post("/api/enrich-saved")
def start_enrich_saved():
    with ENRICH_LOCK:
        if ENRICH_STATUS["running"]:
            return JSONResponse(status_code=400, content={"error": "Enrichment already running"})
    thread = threading.Thread(target=run_enrich_saved, daemon=True)
    thread.start()
    return {"status": "started"}

@app.get("/api/enrich-saved-status")
def enrich_saved_status():
    return ENRICH_STATUS
```

- [ ] **Step 4: Add new field mappings in data builders**

In `dashboard/app.py`, update `build_scholarships()` — add new fields after existing mappings (after line 173):

Add inside the scraped scholarship block:
```python
            "application_portal": s.get("application_portal", ""),
            "contact_email": s.get("contact_email", ""),
            "selection_criteria": s.get("selection_criteria", ""),
            "success_rate": s.get("success_rate", ""),
            "number_of_awards": s.get("number_of_awards", ""),
            "age_limit": s.get("age_limit", ""),
            "bond_requirement": s.get("bond_requirement", ""),
            "funding_specifics": s.get("funding_specifics", ""),
            "eligible_nationalities": s.get("eligible_nationalities", ""),
```

Update `build_universities()` — add after existing mappings (after line 225):
```python
            "acceptance_rate": u.get("acceptance_rate", ""),
            "ra_ta_positions": u.get("ra_ta_positions", ""),
            "cost_of_living_monthly": u.get("cost_of_living_monthly", ""),
            "housing_options": u.get("housing_options", ""),
            "program_structure": u.get("program_structure", ""),
            "prerequisite_courses": u.get("prerequisite_courses", ""),
            "department_contact": u.get("department_contact", ""),
```

Update `build_professors()` — add after existing mappings (after line 272):
```python
            "open_positions": p.get("open_positions", ""),
            "lab_website": p.get("lab_website", ""),
            "past_phd_students": p.get("past_phd_students", ""),
            "research_projects": p.get("research_projects", ""),
```

- [ ] **Step 5: Test the endpoint**

Run: `python -c "from dashboard.app import app; print('Import OK')"`
Expected: `Import OK`

- [ ] **Step 6: Commit**

```bash
git add dashboard/app.py
git commit -m "feat: add /api/enrich-saved endpoint + new field mappings in data builders"
```

---

### Task 5: Frontend — Enrich Button in FollowingSection

**Files:**
- Modify: `frontend/src/components/FollowingSection.vue`

- [ ] **Step 1: Add enrich button and status display in template**

In `frontend/src/components/FollowingSection.vue`, add after the `quick-add-widget` div (around line 45):

```html
    <!-- Enrich Saved Targets Button -->
    <div class="enrich-section">
      <div class="enrich-controls">
        <button
          class="enrich-btn"
          :disabled="enrichRunning"
          @click="startEnrich"
        >
          {{ enrichRunning ? '⟳ Enriching...' : '🔍 Enrich Saved Targets' }}
        </button>
        <span v-if="enrichProgress" class="enrich-progress">{{ enrichProgress }}</span>
      </div>
    </div>
```

- [ ] **Step 2: Add enrich data and methods**

In the `<script>` section, add to `data()`:
```javascript
      enrichRunning: false,
      enrichProgress: '',
      enrichPollTimer: null,
```

Add new methods:
```javascript
    async startEnrich() {
      if (this.enrichRunning) return;
      this.enrichRunning = true;
      this.enrichProgress = 'Starting enrichment...';
      try {
        await fetch('/api/enrich-saved', { method: 'POST' });
        this.pollEnrichStatus();
      } catch (e) {
        this.enrichProgress = 'Error starting enrichment';
        this.enrichRunning = false;
      }
    },
    pollEnrichStatus() {
      this.enrichPollTimer = setInterval(async () => {
        try {
          const resp = await fetch('/api/enrich-saved-status');
          const status = await resp.json();
          this.enrichProgress = status.progress || '';
          if (status.done) {
            clearInterval(this.enrichPollTimer);
            this.enrichPollTimer = null;
            this.enrichRunning = false;
            this.$emit('refresh-data');
          }
        } catch (e) {
          clearInterval(this.enrichPollTimer);
          this.enrichPollTimer = null;
          this.enrichRunning = false;
        }
      }, 1000);
    },
```

Add to `beforeUnmount()` (add if not present):
```javascript
  beforeUnmount() {
    if (this.enrichPollTimer) {
      clearInterval(this.enrichPollTimer);
    }
  },
```

- [ ] **Step 3: Add enrich button styles**

Add to `<style scoped>`:
```css
.enrich-section {
  background: rgba(99, 102, 241, 0.06);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 12px;
  padding: 1rem 1.2rem;
}

.enrich-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.enrich-btn {
  padding: 0.5rem 1.2rem;
  background: #6366f1;
  color: white;
  border: 1px solid #6366f1;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.enrich-btn:hover:not(:disabled) {
  background: #4f46e5;
  border-color: #4f46e5;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
  transform: translateY(-1px);
}

.enrich-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.enrich-progress {
  color: #a5b4fc;
  font-size: 0.8rem;
  font-style: italic;
}
```

- [ ] **Step 4: Ensure App.vue handles refresh-data event**

Check `frontend/src/App.vue` — search for `toggle-follow` handler and add a handler for `refresh-data` that re-fetches `/api/data`:

```javascript
    async refreshData() {
      try {
        const resp = await fetch('/api/data');
        const data = await resp.json();
        this.scholarships = data.scholarships || [];
        this.universities = data.universities || [];
        this.professors = data.professors || [];
        this.followedNames = data.followed || { scholarships: [], professors: [], universities: [] };
      } catch (e) {
        console.error('Refresh data error:', e);
      }
    },
```

And bind it in the template: `@refresh-data="refreshData"` on `<FollowingSection>`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/FollowingSection.vue frontend/src/App.vue
git commit -m "feat: add enrich saved targets button + refresh-data event in frontend"
```

---

### Task 6: Frontend — Display New Enriched Fields

**Files:**
- Modify: `frontend/src/components/FollowingSection.vue`

- [ ] **Step 1: Add new scholarship fields display**

In `frontend/src/components/FollowingSection.vue`, inside the scholarship card template (after the existing meta div around line 79), add:

```html
          <div class="enriched-section" v-if="s.selection_criteria || s.success_rate || s.number_of_awards">
            <h5 class="enriched-title">📋 Enriched Details</h5>
            <div class="enriched-grid">
              <div class="enriched-item" v-if="s.selection_criteria">
                <span class="e-label">Selection Criteria</span>
                <span class="e-value">{{ s.selection_criteria }}</span>
              </div>
              <div class="enriched-item" v-if="s.success_rate">
                <span class="e-label">Success Rate</span>
                <span class="e-value text-red">{{ s.success_rate }}</span>
              </div>
              <div class="enriched-item" v-if="s.number_of_awards">
                <span class="e-label">Awards</span>
                <span class="e-value">{{ s.number_of_awards }} scholarships/year</span>
              </div>
              <div class="enriched-item" v-if="s.age_limit">
                <span class="e-label">Age Limit</span>
                <span class="e-value">{{ s.age_limit }}</span>
              </div>
              <div class="enriched-item" v-if="s.funding_specifics">
                <span class="e-label">Funding</span>
                <span class="e-value">{{ s.funding_specifics }}</span>
              </div>
              <div class="enriched-item" v-if="s.bond_requirement">
                <span class="e-label">Bond</span>
                <span class="e-value text-amber">{{ s.bond_requirement }}</span>
              </div>
              <div class="enriched-item" v-if="s.eligible_nationalities">
                <span class="e-label">Eligible</span>
                <span class="e-value">{{ s.eligible_nationalities }}</span>
              </div>
              <div class="enriched-item" v-if="s.contact_email">
                <span class="e-label">Contact</span>
                <a :href="'mailto:' + s.contact_email" class="e-link">{{ s.contact_email }}</a>
              </div>
            </div>
          </div>
```

- [ ] **Step 2: Add new university fields display**

Inside the university card template (after the existing meta div around line 128), add:

```html
          <div class="enriched-section" v-if="u.acceptance_rate || u.cost_of_living_monthly || u.housing_options">
            <h5 class="enriched-title">📋 Enriched Details</h5>
            <div class="enriched-grid">
              <div class="enriched-item" v-if="u.acceptance_rate">
                <span class="e-label">Acceptance Rate</span>
                <span class="e-value text-red">{{ u.acceptance_rate }}</span>
              </div>
              <div class="enriched-item" v-if="u.ra_ta_positions">
                <span class="e-label">RA/TA</span>
                <span class="e-value text-green">{{ u.ra_ta_positions }}</span>
              </div>
              <div class="enriched-item" v-if="u.cost_of_living_monthly">
                <span class="e-label">Monthly Cost</span>
                <span class="e-value">{{ u.cost_of_living_monthly }}</span>
              </div>
              <div class="enriched-item" v-if="u.housing_options">
                <span class="e-label">Housing</span>
                <span class="e-value">{{ u.housing_options }}</span>
              </div>
              <div class="enriched-item" v-if="u.program_structure">
                <span class="e-label">Structure</span>
                <span class="e-value">{{ u.program_structure }}</span>
              </div>
              <div class="enriched-item" v-if="u.prerequisite_courses">
                <span class="e-label">Prerequisites</span>
                <span class="e-value">{{ u.prerequisite_courses }}</span>
              </div>
              <div class="enriched-item" v-if="u.department_contact">
                <span class="e-label">Dept Contact</span>
                <a :href="'mailto:' + u.department_contact" class="e-link">{{ u.department_contact }}</a>
              </div>
            </div>
          </div>
```

- [ ] **Step 3: Add new professor fields display**

Inside the professor card template (after the publications section around line 174), add:

```html
          <div class="prof-enriched" v-if="p.open_positions || p.lab_website || p.past_phd_students || p.research_projects">
            <h5 class="enriched-title">🔬 Research & Openings</h5>
            <div class="enriched-grid">
              <div class="enriched-item full-width" v-if="p.open_positions">
                <span class="e-label">Open Positions</span>
                <span class="e-value text-green">{{ p.open_positions }}</span>
              </div>
              <div class="enriched-item" v-if="p.lab_website">
                <span class="e-label">Lab</span>
                <a :href="p.lab_website" target="_blank" class="e-link">Visit Lab ↗</a>
              </div>
              <div class="enriched-item full-width" v-if="p.research_projects">
                <span class="e-label">Projects</span>
                <span class="e-value">{{ p.research_projects }}</span>
              </div>
              <div class="enriched-item full-width" v-if="p.past_phd_students">
                <span class="e-label">Past Students</span>
                <span class="e-value">{{ p.past_phd_students }}</span>
              </div>
            </div>
          </div>
```

- [ ] **Step 4: Add enriched section styles**

Add to `<style scoped>`:
```css
.enriched-section,
.prof-enriched {
  margin-top: 1rem;
  padding-top: 0.8rem;
  border-top: 1px dashed rgba(99, 102, 241, 0.2);
}

.enriched-title {
  font-family: 'Outfit', sans-serif;
  font-size: 0.7rem;
  font-weight: 700;
  color: #818cf8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.6rem;
}

.enriched-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem 1rem;
}

.enriched-item {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.enriched-item.full-width {
  grid-column: span 2;
}

.e-label {
  font-size: 0.6rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.e-value {
  font-size: 0.75rem;
  color: #cbd5e1;
  line-height: 1.3;
}

.e-link {
  font-size: 0.75rem;
  color: #60a5fa;
  text-decoration: none;
  font-weight: 500;
}

.e-link:hover {
  text-decoration: underline;
  color: #93c5fd;
}

.text-amber {
  color: #fbbf24;
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/FollowingSection.vue
git commit -m "feat: display new enriched fields in saved targets cards"
```

---

### Task 7: Verify End-to-End

- [ ] **Step 1: Verify backend starts**

Run: `python -c "from dashboard.app import app; print('Backend OK')"`
Expected: `Backend OK`

- [ ] **Step 2: Verify frontend builds**

Run: `cd frontend && npx vite build 2>&1 | tail -5`
Expected: Build completes without errors

- [ ] **Step 3: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All 16 tests PASS

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete saved targets deep research enhancement"
```
