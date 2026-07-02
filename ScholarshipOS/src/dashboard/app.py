import sys, os, threading, time, json, copy
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from config import PROFILE, SHEETS_CONFIG, PROJECT_ROOT, DATA_DIR
from storage.sheets import GoogleSheetsClient
from data.data_loader import load_core_scholarships, load_core_universities, load_core_professors
from features.match_score import MatchScoreCalculator
from features.timeline import TimelineGenerator
from features.cost import CostComparison
from storage.mastery_db import MasteryDB
from agents.mastery import MasteryAgent
from features.my_doc_generator import MyDocGenerator, get_supported_types, DOCUMENT_TEMPLATES
from dashboard.mastery_content_routes import router as mastery_content_router

CORE_SCHOLARSHIPS = load_core_scholarships()
ALL_UNIVERSITIES = load_core_universities()
ALL_PROFESSORS = load_core_professors()

try:
    from features.paper_scraper import PaperScraper
except ImportError:
    class PaperScraper:
        def scrape_google_scholar(self, url, max_papers=10):
            return []
        def scrape_by_author_name(self, name, max_papers=10):
            return []

BASE = os.path.join(os.path.dirname(__file__), '..', '..')
DATA_DIR = os.path.join(BASE, "data")
FOLLOWED_FILE = os.path.join(DATA_DIR, "followed.json")
PAPERS_CACHE_FILE = os.path.join(DATA_DIR, "papers_cache.json")
os.makedirs(DATA_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_papers_cache():
    if os.path.exists(PAPERS_CACHE_FILE):
        try:
            with open(PAPERS_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_papers_cache(data):
    try:
        with open(PAPERS_CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving papers cache: {e}")

creds_path = os.path.join(BASE, "credentials.json")
sheets_client = None
if os.path.exists(creds_path):
    sheets_client = GoogleSheetsClient(creds_path, SHEETS_CONFIG["spreadsheet_id"])

SCAN_STATUS = {"running": False, "progress": "", "done": False}
SCAN_LOCK = threading.Lock()

ENRICH_STATUS = {"running": False, "progress": "", "done": False}
ENRICH_LOCK = threading.Lock()

mastery_db = MasteryDB()

# Auto-seed scholarship mastery data if database is empty
try:
    _mastery_agent = MasteryAgent(sheets_client, interactive=False)
    _mastery_agent.seed_if_empty()
except Exception as e:
    print(f"Mastery seed error (non-fatal): {e}")

MASTERY_SCAN_STATUS = {"running": False, "progress": "", "done": False}
MASTERY_SCAN_LOCK = threading.Lock()

DOC_RESEARCH_STATUS = {"running": False, "progress": "", "done": False, "added": 0}
DOC_RESEARCH_LOCK = threading.Lock()

def set_mastery_scan_progress(progress):
    with MASTERY_SCAN_LOCK:
        MASTERY_SCAN_STATUS["progress"] = progress

def set_mastery_scan_done():
    with MASTERY_SCAN_LOCK:
        MASTERY_SCAN_STATUS["done"] = True
        MASTERY_SCAN_STATUS["running"] = False

def run_mastery_scan():
    with MASTERY_SCAN_LOCK:
        MASTERY_SCAN_STATUS["running"] = True
        MASTERY_SCAN_STATUS["progress"] = "Seeding database..."
        MASTERY_SCAN_STATUS["done"] = False
    try:
        agent = MasteryAgent(sheets_client, interactive=False)
        agent.run_full_scan(seed_only=False, progress_callback=set_mastery_scan_progress)
        set_mastery_scan_done()
    except Exception as e:
        print(f"Mastery scan error: {e}")
        set_mastery_scan_progress(f"Error: {str(e)[:150]}")
        set_mastery_scan_done()
    finally:
        with MASTERY_SCAN_LOCK:
            MASTERY_SCAN_STATUS["running"] = False

def run_mastery_refresh():
    with MASTERY_SCAN_LOCK:
        MASTERY_SCAN_STATUS["running"] = True
        MASTERY_SCAN_STATUS["progress"] = "Refreshing scholarship data..."
        MASTERY_SCAN_STATUS["done"] = False
    try:
        agent = MasteryAgent(sheets_client, interactive=False)
        agent.run_refresh_scan(progress_callback=set_mastery_scan_progress)
        set_mastery_scan_done()
    except Exception as e:
        print(f"Mastery refresh error: {e}")
        set_mastery_scan_progress(f"Error: {str(e)[:150]}")
        set_mastery_scan_done()
    finally:
        with MASTERY_SCAN_LOCK:
            MASTERY_SCAN_STATUS["running"] = False

def set_scan_progress(progress):
    with SCAN_LOCK:
        SCAN_STATUS["progress"] = progress

def set_scan_done():
    with SCAN_LOCK:
        SCAN_STATUS["done"] = True
        SCAN_STATUS["running"] = False

def set_enrich_progress(progress):
    with ENRICH_LOCK:
        ENRICH_STATUS["progress"] = progress

def set_enrich_done():
    with ENRICH_LOCK:
        ENRICH_STATUS["done"] = True
        ENRICH_STATUS["running"] = False

def set_doc_research_progress(progress):
    with DOC_RESEARCH_LOCK:
        DOC_RESEARCH_STATUS["progress"] = progress

def set_doc_research_done(added=0):
    with DOC_RESEARCH_LOCK:
        DOC_RESEARCH_STATUS["done"] = True
        DOC_RESEARCH_STATUS["running"] = False
        DOC_RESEARCH_STATUS["added"] = added

def run_deep_document_research(force=False, quick=True):
    with DOC_RESEARCH_LOCK:
        DOC_RESEARCH_STATUS["running"] = True
        DOC_RESEARCH_STATUS["progress"] = "Initializing deep document research..."
        DOC_RESEARCH_STATUS["done"] = False
        DOC_RESEARCH_STATUS["added"] = 0
    try:
        from agents.deep_document_researcher import DeepDocumentResearcher
        researcher = DeepDocumentResearcher(
            progress_callback=set_doc_research_progress,
        )
        added = researcher.run(force=force, quick=quick)
        set_doc_research_done(added=added)
    except Exception as e:
        print(f"Deep doc research error: {e}")
        set_doc_research_progress(f"Error: {str(e)[:200]}")
        set_doc_research_done(added=0)
    finally:
        with DOC_RESEARCH_LOCK:
            DOC_RESEARCH_STATUS["running"] = False

def load_followed():
    if os.path.exists(FOLLOWED_FILE):
        try:
            with open(FOLLOWED_FILE, "r") as f:
                data = json.load(f)
                if "scholarships" not in data: data["scholarships"] = []
                if "professors" not in data: data["professors"] = []
                if "universities" not in data: data["universities"] = []
                return data
        except Exception:
            pass
    return {"scholarships": [], "professors": [], "universities": []}

def save_followed(data):
    with open(FOLLOWED_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_scraped_data(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data or len(data) < 2:
                return []
            headers = [h.lower().replace(" ", "_").replace("/", "_") for h in data[0]]
            results = []
            for row in data[1:]:
                item = {}
                for i, val in enumerate(row):
                    if i < len(headers):
                        item[headers[i]] = val
                results.append(item)
            return results
    except Exception as e:
        print(f"Error loading scraped data {filename}: {e}")
        return []

def append_to_sheet(sheet_name, row_data):
    if not sheets_client or not sheets_client._spreadsheet:
        return
    try:
        ws = sheets_client._spreadsheet.worksheet(sheet_name)
        ws.append_row(row_data, value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"Sheet write error: {e}")

def build_scholarships():
    results = []
    seen = set()
    for s in CORE_SCHOLARSHIPS:
        k = s.get("name","").lower()[:60]
        if k in seen: continue
        seen.add(k)
        out = copy.deepcopy(s)
        out["_scan_date"] = datetime.now().strftime("%Y-%m-%d")
        results.append(out)
        
    scraped = load_scraped_data("scholarships.json")
    for s in scraped:
        name = s.get("scholarship_name") or s.get("name")
        if not name: continue
        k = name.lower()[:60]
        if k in seen: continue
        seen.add(k)
        out = {
            "country": s.get("country", "Germany"),
            "name": name,
            "provider": s.get("provider", "Web Discovery"),
            "coverage_type": s.get("coverage_type") or s.get("coverage", "Check website"),
            "coverage": s.get("coverage_details") or s.get("coverage", "Check website"),
            "amount": s.get("amount") or s.get("amount_per_year", "Check website"),
            "currency": s.get("currency", "EUR"),
            "degree": s.get("degree_level") or s.get("degree", "MSc"),
            "fields": s.get("target_fields") or s.get("fields", "AI/ML/Data Science"),
            "nationality": s.get("eligibility_nationality") or s.get("nationality", "Check eligibility"),
            "academics": s.get("eligibility_academics") or s.get("academics", "Check requirements"),
            "experience": s.get("eligibility_experience") or s.get("experience", ""),
            "documents": s.get("required_documents") or s.get("documents", ""),
            "fee": s.get("application_fee") or s.get("fee", "Unknown"),
            "lang_app": s.get("language_of_application") or s.get("lang_app", "English"),
            "english_test": s.get("english_test_required") or s.get("english_test", ""),
            "gre": s.get("gre_gmat_required") or s.get("gre", ""),
            "deadline_start": s.get("deadline_start", ""),
            "deadline_end": s.get("deadline_end", ""),
            "duration": s.get("duration", ""),
            "interview": s.get("interview_required") or s.get("interview", ""),
            "competition": s.get("success_rate_competitiveness") or s.get("competition", ""),
            "portal": s.get("application_portal") or s.get("portal", ""),
            "url": s.get("official_url") or s.get("url", ""),
            "match": int(s.get("match_score") or s.get("match") or 50),
            "strategy": s.get("strategy_notes") or s.get("strategy", ""),
            "selection_criteria": s.get("selection_criteria", ""),
            "number_of_awards": s.get("number_of_awards", ""),
            "age_limit": s.get("age_limit", ""),
            "bond_requirement": s.get("bond_requirement", ""),
            "contact_email": s.get("contact_email", ""),
            "_scan_date": datetime.now().strftime("%Y-%m-%d")
        }
        results.append(out)
    return results

def build_universities():
    results = []
    seen = set()
    for u in ALL_UNIVERSITIES:
        k = u.get("name","").lower()[:60]
        if k in seen: continue
        seen.add(k)
        out = copy.deepcopy(u)
        out["_scan_date"] = datetime.now().strftime("%Y-%m-%d")
        results.append(out)
        
    scraped = load_scraped_data("universities.json")
    for u in scraped:
        name = u.get("university_name") or u.get("name")
        if not name: continue
        k = name.lower()[:60]
        if k in seen: continue
        seen.add(k)
        out = {
            "country": u.get("country", ""),
            "name": name,
            "location": u.get("location", ""),
            "type": u.get("university_type") or u.get("type", ""),
            "qs_rank": u.get("qs_world_ranking_2025") or u.get("qs_rank", ""),
            "the_rank": u.get("the_world_ranking_2025") or u.get("the_rank", ""),
            "program": u.get("program_name") or u.get("program", ""),
            "degree": u.get("degree", ""),
            "field": u.get("field___specialization") or u.get("field", ""),
            "language": u.get("teaching_language") or u.get("language", "English"),
            "tuition": u.get("tuition_per_semester") or u.get("tuition", "0"),
            "currency": u.get("currency", "EUR"),
            "semester_fee": u.get("semester_fee___contribution") or u.get("semester_fee", ""),
            "app_fee": u.get("application_fee") or u.get("app_fee", ""),
            "deadline_winter": u.get("application_deadline_winter") or u.get("deadline_winter", ""),
            "deadline_summer": u.get("application_deadline_summer") or u.get("deadline_summer", ""),
            "requirements": u.get("admission_requirements") or u.get("requirements", ""),
            "english": u.get("english_test_requirement") or u.get("english", ""),
            "gre": u.get("gre_gmat_required") or u.get("gre", ""),
            "min_gpa": u.get("minimum_gpa_required") or u.get("min_gpa", ""),
            "duration": u.get("program_duration_semesters") or u.get("duration", ""),
            "ects": u.get("ects_credits") or u.get("ects", ""),
            "scholarships": u.get("scholarship_availability") or u.get("scholarships", ""),
            "portal": u.get("application_portal___platform") or u.get("portal", ""),
            "dept_url": u.get("department___faculty_url") or u.get("dept_url", ""),
            "research": u.get("research_strengths") or u.get("research", ""),
            "living_cost": u.get("cost_of_living_monthly_eur_usd") or u.get("living_cost", ""),
            "strategy": u.get("strategy_notes") or u.get("strategy", ""),
            "acceptance_rate": u.get("acceptance_rate", ""),
            "ra_ta_positions": u.get("ra_ta_positions", ""),
            "housing_options": u.get("housing_options", ""),
            "program_structure": u.get("program_structure", ""),
            "prerequisite_courses": u.get("prerequisite_courses", ""),
            "department_contact": u.get("department_contact", ""),
            "_scan_date": datetime.now().strftime("%Y-%m-%d")
        }
        results.append(out)
    return results

def build_professors():
    results = []
    seen = {}  # name -> index in results
    for p in ALL_PROFESSORS:
        k = p.get("name","").lower()[:60]
        if k in seen: continue
        seen[k] = len(results)
        out = copy.deepcopy(p)
        out["_scan_date"] = datetime.now().strftime("%Y-%m-%d")
        results.append(out)
        
    scraped = load_scraped_data("professors.json")
    for p in scraped:
        name = p.get("professor_name") or p.get("name")
        if not name: continue
        k = name.lower()[:60]
        if k in seen:
            # Merge enriched fields from scraped data into existing core entry
            idx = seen[k]
            existing = results[idx]
            enriched = {
                "open_positions": p.get("open_positions", ""),
                "lab_website": p.get("lab_website", ""),
                "past_phd_students": p.get("past_phd_students", ""),
                "research_projects": p.get("research_projects", ""),
            }
            for key, val in enriched.items():
                if val:
                    existing[key] = val
            continue
        seen[k] = len(results)
        out = {
            "country": p.get("country", ""),
            "university": p.get("university", ""),
            "name": name,
            "title": p.get("title___position") or p.get("title", ""),
            "email": p.get("email", ""),
            "phone": p.get("phone___office") or p.get("phone", ""),
            "department": p.get("department___institute") or p.get("department", ""),
            "interests": p.get("research_interests_full_list") or p.get("interests", ""),
            "group": p.get("research_group___lab") or p.get("group", ""),
            "scholar_url": p.get("google_scholar_url") or p.get("scholar_url", ""),
            "citations": p.get("google_scholar_citations") or p.get("citations", ""),
            "h_index": p.get("h_index") or p.get("h-index", ""),
            "papers": p.get("recent_publications_top_3") or p.get("papers", ""),
            "venues": p.get("top_publication_venues") or p.get("venues", ""),
            "students": p.get("current_phd_msc_students") or p.get("students", ""),
            "funding": p.get("funding_available") or p.get("funding", ""),
            "collab": p.get("collaboration_interests") or p.get("collab", ""),
            "office_hours": p.get("office_hours___availability") or p.get("office_hours", ""),
            "courses": p.get("courses_taught") or p.get("courses", ""),
            "supervisor_for": p.get("potential_supervisor_for") or p.get("supervisor_for", ""),
            "contact": p.get("recommended_contact_method") or p.get("contact", ""),
            "profile_url": p.get("profile_page_url") or p.get("profile_url", ""),
            "strategy": p.get("strategy_notes") or p.get("strategy", ""),
            "open_positions": p.get("open_positions", ""),
            "lab_website": p.get("lab_website", ""),
            "past_phd_students": p.get("past_phd_students", ""),
            "research_projects": p.get("research_projects", ""),
            "_scan_date": datetime.now().strftime("%Y-%m-%d")
        }
        results.append(out)
    return results

def run_scan():
    with SCAN_LOCK:
        SCAN_STATUS["running"] = True
        SCAN_STATUS["progress"] = "Starting scan..."
        SCAN_STATUS["done"] = False
    try:
        from agents.scholarship import ScholarshipAgent
        from agents.university import UniversityAgent
        from agents.professor import ProfessorAgent

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        followed = load_followed()
        papers_cache = load_papers_cache()

        # 1. Scholarship agent (uses DuckDuckGo directly, no slow Google retries)
        set_scan_progress("Discovering new scholarships...")
        sch_agent = ScholarshipAgent(sheets_client, interactive=False)
        sch_agent.run()

        # 2. University agent
        set_scan_progress("Discovering new university programs...")
        uni_agent = UniversityAgent(sheets_client, interactive=False)
        uni_agent.run()

        # 3. Professor agent (scoped to target universities)
        set_scan_progress("Discovering new professors...")
        prof_agent = ProfessorAgent(sheets_client, interactive=False)
        scouted_unis = build_universities()
        target_unis = [{"name": u["name"], "country": u["country"]} for u in scouted_unis]
        prof_agent.run(target_unis=target_unis)

        # 4. Compute features
        set_scan_progress("Computing match scores...")
        scholarships = build_scholarships()
        universities = build_universities()
        professors = build_professors()
        MatchScoreCalculator(PROFILE).calculate(scholarships)

        set_scan_progress("Computing cost comparisons...")
        CostComparison(PROFILE).show()

        set_scan_progress("Generating timeline...")
        TimelineGenerator(PROFILE).generate()

        set_scan_progress("Computing deadlines...")
        from features.deadlines import DeadlineTracker
        DeadlineTracker(PROFILE).calculate(scholarships, universities)

        # 5. Deep scan followed professors via Semantic Scholar API
        scraper = PaperScraper()
        for pname in followed.get("professors", []):
            set_scan_progress(f"Deep scraping publications for: {pname[:30]}...")
            papers = scraper.scrape_by_author_name(pname)
            if papers:
                papers_cache[pname] = papers
                append_to_sheet("Updates Log", [timestamp, "deep_scan", f"Professor: {pname}", f"{len(papers)} papers scraped"])
            time.sleep(1)

        save_papers_cache(papers_cache)

        # 6. Collect new document samples
        set_scan_progress("Collecting new document samples from GitHub...")
        from agents.document_collector import DocumentCollector
        doc_collector = DocumentCollector(interactive=False)
        new_docs = doc_collector.run(progress_callback=lambda msg: set_scan_progress(msg))
        if new_docs:
            append_to_sheet("Updates Log", [timestamp, "doc_scan", f"DocumentCollector", f"{new_docs} new samples"])

        # 7. Enrich followed targets with full data
        set_scan_progress("Enriching followed targets with full details...")
        from agents.target import TargetEnricherAgent
        enricher = TargetEnricherAgent(PROFILE, sheets_client, interactive=False)
        enricher.enrich()

        set_scan_progress(f"Done! {len(scholarships)} scholarships, {len(universities)} universities, {len(professors)} professors")
        set_scan_done()
    except Exception as e:
        print(f"Scan execution error: {e}")
        set_scan_progress(f"Error: {str(e)[:150]}")
        set_scan_done()
    finally:
        with SCAN_LOCK:
            SCAN_STATUS["running"] = False

# ─── API Routes ──────────────────────────────────

app.include_router(mastery_content_router)

# ─── API Routes ──────────────────────────────────

@app.get("/api/data")
def get_data():
    scholarships = build_scholarships()
    universities = build_universities()
    professors = build_professors()
    matcher = MatchScoreCalculator(PROFILE)
    scores = matcher.calculate(scholarships)
    tl = TimelineGenerator(PROFILE)
    timeline = tl.generate()
    followed = load_followed()

    costs = CostComparison(PROFILE).show()

    # Calculate deadlines dynamically
    from features.deadlines import DeadlineTracker
    dt = DeadlineTracker(PROFILE)
    deadlines = dt.calculate(scholarships, universities)

    # Attach cached deep papers to followed professors
    papers_cache = load_papers_cache()
    for p in professors:
        if p["name"] in followed.get("professors", []):
            p["_deep_papers"] = papers_cache.get(p["name"], [])

    # Load application tracker
    from features.tracker import ApplicationTracker
    _tracker = ApplicationTracker(sheets_client)
    
    return {
        "scholarships": scholarships,
        "universities": universities,
        "professors": professors,
        "scores": scores,
        "timeline": timeline,
        "followed": followed,
        "costs": costs,
        "deadlines": deadlines,
        "tracker": _tracker.applications,
        "profile": PROFILE
    }

@app.post("/api/scan")
def start_scan():
    with SCAN_LOCK:
        if SCAN_STATUS["running"]:
            return JSONResponse(status_code=400, content={"error": "Scan already running"})
    thread = threading.Thread(target=run_scan, daemon=True)
    thread.start()
    return {"status": "started"}

@app.get("/api/scan-status")
def scan_status():
    return SCAN_STATUS

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

@app.post("/api/enrich-saved")
def start_enrich_saved():
    with ENRICH_LOCK:
        if ENRICH_STATUS["running"]:
            return JSONResponse(status_code=400, content={"error": "Enrichment already running"})
        # Force-reset any stale status before starting
        ENRICH_STATUS["progress"] = ""
        ENRICH_STATUS["done"] = False
    thread = threading.Thread(target=run_enrich_saved, daemon=True)
    thread.start()
    return {"status": "started"}

@app.post("/api/enrich-saved-reset")
def reset_enrich_saved():
    with ENRICH_LOCK:
        ENRICH_STATUS["running"] = False
        ENRICH_STATUS["progress"] = ""
        ENRICH_STATUS["done"] = False
    return {"status": "reset"}

@app.get("/api/enrich-saved-status")
def enrich_saved_status():
    return ENRICH_STATUS

def log_follow_actions(old_data, new_data):
    if not sheets_client or not sheets_client._spreadsheet:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    categories = ["scholarships", "professors", "universities"]
    cat_names = {
        "scholarships": "Scholarship",
        "professors": "Professor",
        "universities": "University"
    }
    for cat in categories:
        old_set = set(old_data.get(cat, []))
        new_set = set(new_data.get(cat, []))
        display_name = cat_names.get(cat, cat.capitalize())
        
        # Added (Followed)
        for item in (new_set - old_set):
            append_to_sheet("Following", [timestamp, display_name, item, "Followed"])
            
        # Removed (Unfollowed)
        for item in (old_set - new_set):
            append_to_sheet("Following", [timestamp, display_name, item, "Unfollowed"])

@app.get("/api/followed")
def get_followed():
    return load_followed()

@app.post("/api/followed")
async def post_followed(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Request must be JSON"})
    if not data:
        return JSONResponse(status_code=400, content={"error": "Request must be JSON"})
    valid_keys = {"scholarships", "professors", "universities"}
    if not all(k in valid_keys for k in data):
        return JSONResponse(status_code=400, content={"error": "Invalid key in payload. Only scholarships, professors, universities allowed."})
    current = load_followed()
    old_followed = copy.deepcopy(current)
    for key in ["scholarships", "professors", "universities"]:
        if key in data and isinstance(data[key], list):
            current[key] = data[key]
    save_followed(current)
    try:
        log_follow_actions(old_followed, current)
    except Exception as e:
        print(f"Error logging follow actions: {e}")
    return {"status": "ok"}

@app.get("/api/scholarship/{name:path}")
def scholarship_detail(name: str):
    for s in CORE_SCHOLARSHIPS:
        if s.get("name","").lower() == name.lower():
            return s
    return JSONResponse(status_code=404, content={"error": "Not found"})

@app.get("/api/professor/{email:path}/papers")
def professor_papers(email: str):
    cache = load_papers_cache()
    for p in ALL_PROFESSORS:
        if p.get("email","").lower() == email.lower():
            papers = cache.get(p["name"], [])
            return papers
    return JSONResponse(status_code=404, content={"error": "Not found"})

@app.get("/api/professor/{email:path}")
def professor_detail(email: str):
    for p in ALL_PROFESSORS:
        if p.get("email","").lower() == email.lower():
            return p
    return JSONResponse(status_code=404, content={"error": "Not found"})

@app.get("/api/match-scores")
def get_match_scores():
    scholarships = build_scholarships()
    matcher = MatchScoreCalculator(PROFILE)
    return matcher.calculate(scholarships)

@app.get("/api/timeline")
def get_timeline():
    tl = TimelineGenerator(PROFILE)
    return tl.generate()

@app.get("/api/documents")
def get_documents():
    import json, os
    path = os.path.join(DATA_DIR, "scholar_documents.json")
    if not os.path.exists(path):
        return {"samples": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/documents/clear")
def clear_documents():
    import json, os
    path = os.path.join(DATA_DIR, "scholar_documents.json")
    if os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"samples": [], "last_updated": datetime.now().isoformat()}, f)
    log_path = os.path.join(DATA_DIR, "deep_research_log.json")
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except Exception:
            pass
    return {"status": "cleared"}

@app.post("/api/documents/deep-research")
async def start_doc_deep_research(request: Request):
    force = False
    quick = True
    try:
        body = await request.json()
        force = bool(body.get("force", False))
        quick = bool(body.get("quick", True))
    except Exception:
        pass
    with DOC_RESEARCH_LOCK:
        if DOC_RESEARCH_STATUS["running"]:
            return JSONResponse(status_code=400, content={"error": "Deep research already running"})
    thread = threading.Thread(target=run_deep_document_research, kwargs={"force": force, "quick": quick}, daemon=True)
    thread.start()
    return {"status": "started", "force": force, "quick": quick}

@app.get("/api/documents/deep-research-status")
def doc_deep_research_status():
    with DOC_RESEARCH_LOCK:
        status = dict(DOC_RESEARCH_STATUS)
    log_path = os.path.join(DATA_DIR, "deep_research_log.json")
    if os.path.exists(log_path):
        try:
            with open(log_path, encoding="utf-8") as f:
                status["last_result"] = json.load(f)
        except Exception:
            pass
    return status

@app.get("/api/mastery")
def get_mastery_scholarships():
    scholarships = mastery_db.get_all_scholarships()
    result = []
    for s in scholarships:
        detail = mastery_db.get_scholarship(s["slug"])
        result.append({
            "slug": s["slug"],
            "name": s["name"],
            "country": s["country"],
            "coverage_type": s["coverage_type"],
            "amount": s["amount"],
            "currency": s["currency"],
            "match_score": s["match_score"],
            "deadline_end": s["deadline_end"],
            "total_steps": s["total_steps"],
            "completed_steps": s["completed_steps"],
            "competitiveness": s["competitiveness"],
            "provider": s["provider"],
            "coverage_details": (detail or s).get("coverage_details", ""),
            "required_documents": (detail or s).get("required_documents", ""),
            "english_test_required": (detail or s).get("english_test_required", ""),
            "gre_required": (detail or s).get("gre_required", ""),
            "eligibility_nationality": (detail or s).get("eligibility_nationality", ""),
            "eligibility_academics": (detail or s).get("eligibility_academics", ""),
            "degree_level": (detail or s).get("degree_level", ""),
            "target_fields": (detail or s).get("target_fields", ""),
            "application_fee": (detail or s).get("application_fee", ""),
            "deadline_start": (detail or s).get("deadline_start", ""),
            "duration": (detail or s).get("duration", ""),
            "interview_required": (detail or s).get("interview_required", ""),
            "strategy_notes": (detail or s).get("strategy_notes", ""),
        })
    return result

@app.post("/api/mastery/scan")
def start_mastery_scan():
    with MASTERY_SCAN_LOCK:
        if MASTERY_SCAN_STATUS["running"]:
            return JSONResponse(status_code=400, content={"error": "Scan already running"})
    thread = threading.Thread(target=run_mastery_scan, daemon=True)
    thread.start()
    return {"status": "started"}

@app.post("/api/mastery/refresh")
def start_mastery_refresh():
    with MASTERY_SCAN_LOCK:
        if MASTERY_SCAN_STATUS["running"]:
            return JSONResponse(status_code=400, content={"error": "Scan already running"})
    thread = threading.Thread(target=run_mastery_refresh, daemon=True)
    thread.start()
    return {"status": "started", "mode": "refresh"}

@app.get("/api/mastery/scan-status")
def mastery_scan_status():
    return MASTERY_SCAN_STATUS

@app.get("/api/mastery/{slug}")
def get_mastery_scholarship(slug: str):
    s = mastery_db.get_scholarship(slug)
    if not s:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    s["news"] = mastery_db.get_news(slug)
    return s

@app.get("/api/mastery/{slug}/news")
def get_mastery_news(slug: str):
    return mastery_db.get_news(slug)

@app.get("/api/mastery/{slug}/checklist")
def get_mastery_checklist(slug: str):
    s = mastery_db.get_scholarship(slug)
    if not s:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    checklist = mastery_db.get_checklist(s["id"])
    return checklist

# ─── My Doc Generator ────────────────────────────────────────

MYDOC_GEN = MyDocGenerator()
MYDOC_GEN_LOCK = threading.Lock()
MYDOC_STATUS = {"running": False, "progress": "", "done": False, "total": 0, "current": 0}

def run_mydoc_generate():
    global MYDOC_STATUS
    with MYDOC_GEN_LOCK:
        MYDOC_STATUS["running"] = True
        MYDOC_STATUS["done"] = False
        MYDOC_STATUS["progress"] = "Starting generation..."
        MYDOC_STATUS["total"] = 0
        MYDOC_STATUS["current"] = 0
    try:
        from data.data_loader import load_core_scholarships
        import json, os
        followed_path = os.path.join(DATA_DIR, "followed.json")
        if not os.path.exists(followed_path):
            MYDOC_STATUS["progress"] = "No followed scholarships found"
            MYDOC_STATUS["done"] = True
            return
        with open(followed_path, "r") as f:
            followed_data = json.load(f)
        names = followed_data.get("scholarships", [])

        all_schs = load_core_scholarships()
        name_map = {s["name"].lower().strip(): s for s in all_schs}
        targets = []
        for n in names:
            key = n.lower().strip()
            if key in name_map:
                targets.append(name_map[key])

        doc_type_count = len(get_supported_types())
        MYDOC_STATUS["total"] = len(targets) * doc_type_count
        MYDOC_STATUS["progress"] = f"Generating docs for {len(targets)} scholarships..."

        gen = MyDocGenerator()
        if not gen.is_available():
            MYDOC_STATUS["progress"] = "Groq API not configured. Add GROQ_API_KEY to .env"
            MYDOC_STATUS["done"] = True
            return

        results = {}
        for i, sch in enumerate(targets):
            name = sch["name"]
            MYDOC_STATUS["progress"] = f"[{i+1}/{len(targets)}] Generating {name}..."
            docs = gen.generate_all(sch)
            results[name] = docs
            MYDOC_STATUS["current"] = (i + 1) * doc_type_count

        gen._save(results)
        MYDOC_STATUS["progress"] = f"Done! Generated docs for {len(targets)} scholarships."
        MYDOC_STATUS["done"] = True
    except Exception as e:
        MYDOC_STATUS["progress"] = f"Error: {str(e)[:200]}"
        MYDOC_STATUS["done"] = True
    finally:
        with MYDOC_GEN_LOCK:
            MYDOC_STATUS["running"] = False

@app.get("/api/my-docs")
def get_my_docs():
    gen = MyDocGenerator()
    return gen.get_all_docs()

@app.get("/api/my-docs/supported-types")
def my_docs_types():
    return get_supported_types()

@app.get("/api/my-docs/status")
def my_docs_status():
    return MYDOC_STATUS

@app.post("/api/my-docs/generate")
def start_my_docs_generate():
    with MYDOC_GEN_LOCK:
        if MYDOC_STATUS["running"]:
            return JSONResponse(status_code=400, content={"error": "Generation already running"})
    thread = threading.Thread(target=run_mydoc_generate, daemon=True)
    thread.start()
    return {"status": "started"}

@app.post("/api/my-docs/generate-single")
async def generate_single_doc(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Request must be JSON"})
    name = body.get("name", "")
    if not name:
        return JSONResponse(status_code=400, content={"error": "name required"})

    all_schs = load_core_scholarships()
    sch = None
    for s in all_schs:
        if s["name"].lower().strip() == name.lower().strip():
            sch = s
            break
    if not sch:
        return JSONResponse(status_code=404, content={"error": "Scholarship not found"})

    gen = MyDocGenerator()
    if not gen.is_available():
        return JSONResponse(status_code=400, content={"error": "Groq API not configured. Add GROQ_API_KEY to .env"})

    docs = gen.generate_all(sch)
    gen._save({sch["name"]: docs})
    return docs

@app.get("/api/my-docs/export-pdf")
def export_my_doc_pdf(name: str = Query(...), doc_type: str = Query("sop")):
    gen = MyDocGenerator()
    docs = gen.get_scholarship_docs(name)
    if not docs:
        return JSONResponse(status_code=404, content={"error": f"No docs found for '{name}'"})

    if doc_type not in docs:
        return JSONResponse(status_code=404, content={"error": f"Doc type '{doc_type}' not found for '{name}'"})

    content = docs[doc_type].get("content", "")
    template_info = DOCUMENT_TEMPLATES.get(doc_type, {})
    label = template_info.get("label", doc_type.upper())

    try:
        import markdown
        html_body = markdown.markdown(content)
    except ImportError:
        html_body = content.replace("\n", "<br>\n")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{name} - {label}</title>
<style>
  @page {{ margin: 2.5cm 2cm; }}
  body {{ font-family: 'Georgia', 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; color: #1a1a1a; max-width: 800px; margin: 0 auto; padding: 20px; }}
  h2 {{ font-family: 'Helvetica', 'Arial', sans-serif; font-size: 18pt; color: #1e3a5f; border-bottom: 2px solid #3b82f6; padding-bottom: 6px; margin-top: 30px; }}
  h1 {{ font-family: 'Helvetica', 'Arial', sans-serif; font-size: 22pt; color: #1e3a5f; text-align: center; margin-bottom: 5px; }}
  .subtitle {{ text-align: center; color: #666; font-size: 10pt; margin-bottom: 30px; }}
  p {{ margin: 8px 0; text-align: justify; }}
  ul {{ margin: 6px 0; }}
  li {{ margin: 3px 0; }}
  @media print {{ body {{ padding: 0; }} }}
</style></head><body>
<h1>{label}</h1>
<div class="subtitle">{name} &mdash; Generated by ScholarAI</div>
{html_body}
</body></html>"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)

@app.get("/api/my-docs/{scholarship_name:path}")
def get_scholarship_docs(scholarship_name: str):
    gen = MyDocGenerator()
    docs = gen.get_scholarship_docs(scholarship_name)
    if not docs:
        return JSONResponse(status_code=404, content={"error": "No docs found for this scholarship. Generate first."})
    return docs

@app.post("/api/my-docs/regenerate-section")
async def regenerate_section(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Request must be JSON"})
    name = body.get("name", "")
    doc_type = body.get("doc_type", "")
    section = body.get("section", "")
    if not name or not doc_type or not section:
        return JSONResponse(status_code=400, content={"error": "name, doc_type, and section required"})
    gen = MyDocGenerator()
    result = gen.regenerate_section(name, doc_type, section)
    return result

# ─── Application Tracker API ────────────────────────────────

@app.get("/api/tracker")
def get_tracker():
    from features.tracker import ApplicationTracker
    t = ApplicationTracker(sheets_client)
    return t.applications

@app.post("/api/tracker/add")
async def tracker_add(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Request must be JSON"})
    item_type = body.get("item_type", "scholarship")
    name = body.get("name", "")
    university = body.get("university", "")
    deadline = body.get("deadline", "")
    notes = body.get("notes", "")
    if not name:
        return JSONResponse(status_code=400, content={"error": "name required"})
    from features.tracker import ApplicationTracker
    t = ApplicationTracker(sheets_client)
    t.add(item_type, name, university, deadline, notes)
    return {"status": "added", "application": t.applications[-1]}

@app.post("/api/tracker/update")
async def tracker_update(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Request must be JSON"})
    index = body.get("index", -1)
    status = body.get("status", "")
    date_accepted = body.get("date_accepted", "")
    if index < 0 or not status:
        return JSONResponse(status_code=400, content={"error": "index and status required"})
    from features.tracker import ApplicationTracker
    t = ApplicationTracker(sheets_client)
    t.update_status(index, status, date_accepted)
    return {"status": "updated"}

@app.post("/api/mastery/{slug}/checklist")
async def update_mastery_checklist(slug: str, request: Request):
    s = mastery_db.get_scholarship(slug)
    if not s:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Request must be JSON"})
    step_id = data.get("step_id")
    completed = data.get("completed", False)
    notes = data.get("notes", None)
    if not step_id:
        return JSONResponse(status_code=400, content={"error": "step_id required"})
    mastery_db.update_checklist_item(s["id"], step_id, completed, notes)
    return {"status": "ok"}

@app.get("/")
def index():
    return FileResponse(os.path.join(BASE, "web", "frontend", "dist", "index.html"))

# Mount static files (ensure this is registered after all dynamic routes)
app.mount("/", StaticFiles(directory=os.path.join(BASE, "web", "frontend", "dist"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
