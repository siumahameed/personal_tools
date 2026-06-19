# ScholarAI Redesign — Vue 3 Frontend + Enhanced Scan Engine

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert ScholarAI from Flask-templated dashboard to Vue 3 + Vite frontend with pure JSON API backend, add deep Google Scholar scraping for followed professors, and enhance scan workflow.

**Architecture:** Flask becomes pure JSON API at `/api/*`. Vue 3 + Vite frontend in `frontend/` serves the UI. New `PaperScraper` feature scrapes Google Scholar for followed professors. Data appends sequentially to Google Sheets.

**Tech Stack:** Vue 3 (Composition API), Vite, Flask, gspread, BeautifulSoup

---

### Task 1: Convert Flask to Pure JSON API + Add CORS

**Files:**
- Modify: `dashboard/app.py` — full rewrite
- Modify: `requirements.txt` — add flask-cors

- [ ] **Step 1: Add flask-cors to requirements**

```
flask==3.1.0
flask-cors==5.0.0
gspread==6.1.4
google-auth==2.37.0
requests==2.32.3
beautifulsoup4==4.12.3
lxml==5.3.0
python-dateutil==2.9.0
```

- [ ] **Step 2: Rewrite dashboard/app.py as pure JSON API**

Replace the entire file:

```python
import sys, os, threading, time, json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, request
from flask_cors import CORS
from config import PROFILE, SHEETS_CONFIG
from storage.sheets import GoogleSheetsClient
from agents.scholarship import CORE_SCHOLARSHIPS
from agents.university import GERMAN_UNIVERSITIES, USA_UNIVERSITIES
from agents.professor import GERMAN_PROFESSORS, USA_PROFESSORS
from features.match_score import MatchScoreCalculator
from features.timeline import TimelineGenerator
from features.paper_scraper import PaperScraper

app = Flask(__name__)
CORS(app)

BASE = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE, "data")
FOLLOWED_FILE = os.path.join(DATA_DIR, "followed.json")
os.makedirs(DATA_DIR, exist_ok=True)

creds_path = os.path.join(BASE, "credentials.json")
sheets_client = None
if os.path.exists(creds_path):
    sheets_client = GoogleSheetsClient(creds_path, SHEETS_CONFIG["spreadsheet_id"])

SCAN_STATUS = {"running": False, "progress": "", "done": False}

def load_followed():
    if os.path.exists(FOLLOWED_FILE):
        with open(FOLLOWED_FILE, "r") as f:
            return json.load(f)
    return {"scholarships": [], "professors": []}

def save_followed(data):
    with open(FOLLOWED_FILE, "w") as f:
        json.dump(data, f, indent=2)

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
        k = s.get("name","")[:60].lower()
        if k in seen: continue
        seen.add(k)
        s["_scan_date"] = datetime.now().strftime("%Y-%m-%d")
        results.append(s)
    return results

def build_universities():
    results = []
    seen = set()
    for u in GERMAN_UNIVERSITIES + USA_UNIVERSITIES:
        k = u.get("name","")[:60].lower()
        if k in seen: continue
        seen.add(k)
        u["_scan_date"] = datetime.now().strftime("%Y-%m-%d")
        results.append(u)
    return results

def build_professors():
    results = []
    seen = set()
    for p in GERMAN_PROFESSORS + USA_PROFESSORS:
        k = p.get("name","")[:60].lower()
        if k in seen: continue
        seen.add(k)
        p["_scan_date"] = datetime.now().strftime("%Y-%m-%d")
        results.append(p)
    return results

def run_scan():
    global SCAN_STATUS
    SCAN_STATUS = {"running": True, "progress": "Starting scan...", "done": False}
    try:
        followed = load_followed()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Ensure worksheets exist
        sheet_names = ["Scholarships", "Professors", "Universities", "Following", "Updates Log"]
        for name in sheet_names:
            try:
                if sheets_client and sheets_client._spreadsheet:
                    sheets_client._spreadsheet.worksheet(name)
            except:
                if sheets_client and sheets_client._spreadsheet:
                    ws = sheets_client._spreadsheet.add_worksheet(title=name, rows=2000, cols=20)
                    ws.append_row(["Timestamp", "Type", "Item", "Detail"])

        # --- Step 1: Deep scan followed professors ---
        scraper = PaperScraper()
        for pname in followed.get("professors", []):
            SCAN_STATUS["progress"] = f"Deep scanning professor: {pname[:40]}..."
            time.sleep(0.5)
            prof = None
            for p in GERMAN_PROFESSORS + USA_PROFESSORS:
                if p["name"] == pname:
                    prof = p
                    break
            if prof and prof.get("scholar_url"):
                papers = scraper.scrape_google_scholar(prof["scholar_url"])
                prof["_deep_papers"] = papers
                prof["_scan_type"] = "deep"
                prof["_scan_date"] = timestamp
                append_to_sheet("Updates Log", [timestamp, "deep_scan", f"Professor: {pname}", f"{len(papers)} papers scraped"])

        # --- Step 2: Deep scan followed scholarships ---
        for sname in followed.get("scholarships", []):
            SCAN_STATUS["progress"] = f"Checking scholarship updates: {sname[:40]}..."
            time.sleep(0.3)
            append_to_sheet("Updates Log", [timestamp, "deep_scan", f"Scholarship: {sname}", "Update check queued"])

        # --- Step 3: General scan scholarships ---
        SCAN_STATUS["progress"] = "Scanning scholarships..."
        time.sleep(0.3)
        scholarships = build_scholarships()
        for s in scholarships:
            row = [timestamp, s.get("name",""), s.get("country",""), s.get("provider",""),
                   s.get("coverage_type",""), s.get("amount",""), s.get("currency",""),
                   s.get("deadline_end","") or s.get("deadline_start",""), str(s.get("match","")),
                   s.get("url",""), (s.get("strategy","") or "")[:200], "general"]
            append_to_sheet("Scholarships", row)

        # --- Step 4: General scan universities ---
        SCAN_STATUS["progress"] = "Scanning universities..."
        time.sleep(0.3)
        universities = build_universities()
        for u in universities:
            row = [timestamp, u.get("name",""), u.get("country",""), str(u.get("qs_rank","")),
                   u.get("program",""), u.get("tuition",""), u.get("deadline_winter","") or u.get("deadline_summer",""),
                   u.get("language",""), u.get("scholarships",""), u.get("dept_url","") or u.get("portal",""), "general"]
            append_to_sheet("Universities", row)

        # --- Step 5: General scan professors ---
        SCAN_STATUS["progress"] = "Scanning professors..."
        time.sleep(0.3)
        professors = build_professors()
        for p in professors:
            papers_str = (p.get("papers","") or "")[:200]
            deep_papers = p.get("_deep_papers", [])
            papers_json = json.dumps(deep_papers) if deep_papers else ""
            row = [timestamp, p.get("name",""), p.get("university",""), p.get("email",""),
                   p.get("title",""), (p.get("interests","") or "")[:200], str(p.get("h_index","")),
                   papers_str, p.get("scholar_url",""), p.get("profile_url",""),
                   papers_json, p.get("_scan_type", "general")]
            append_to_sheet("Professors", row)

        # --- Step 6: Log updates ---
        SCAN_STATUS["progress"] = f"Done! {len(scholarships)} scholarships, {len(universities)} universities, {len(professors)} professors"
        SCAN_STATUS["done"] = True
    except Exception as e:
        SCAN_STATUS["progress"] = f"Error: {str(e)[:300]}"
        SCAN_STATUS["done"] = True
    finally:
        SCAN_STATUS["running"] = False

# ─── API Routes ──────────────────────────────────

@app.route("/api/data")
def get_data():
    scholarships = build_scholarships()
    universities = build_universities()
    professors = build_professors()
    matcher = MatchScoreCalculator(PROFILE)
    scores = matcher.calculate()
    tl = TimelineGenerator(PROFILE)
    timeline = tl.generate()
    followed = load_followed()

    # Attach deep papers to followed professors
    scraper = PaperScraper()
    for p in professors:
        if p["name"] in followed.get("professors", []):
            if p.get("scholar_url"):
                p["_deep_papers"] = scraper.scrape_google_scholar(p["scholar_url"])
            else:
                p["_deep_papers"] = []

    return jsonify({
        "scholarships": scholarships,
        "universities": universities,
        "professors": professors,
        "scores": scores,
        "timeline": timeline,
        "followed": followed,
    })

@app.route("/api/scan", methods=["POST"])
def start_scan():
    if SCAN_STATUS["running"]:
        return jsonify({"error": "Scan already running"}), 400
    thread = threading.Thread(target=run_scan, daemon=True)
    thread.start()
    return jsonify({"status": "started"})

@app.route("/api/scan-status")
def scan_status():
    return jsonify(SCAN_STATUS)

@app.route("/api/followed", methods=["GET", "POST"])
def handle_followed():
    if request.method == "POST":
        data = request.json
        current = load_followed()
        for key in ["scholarships", "professors"]:
            if key in data:
                current[key] = data[key]
        save_followed(current)
        return jsonify({"status": "ok"})
    return jsonify(load_followed())

@app.route("/api/scholarship/<path:name>")
def scholarship_detail(name):
    for s in CORE_SCHOLARSHIPS:
        if s.get("name","").lower() == name.lower():
            return jsonify(s)
    return jsonify({"error": "Not found"}), 404

@app.route("/api/professor/<path:email>")
def professor_detail(email):
    for p in GERMAN_PROFESSORS + USA_PROFESSORS:
        if p.get("email","").lower() == email.lower():
            return jsonify(p)
    return jsonify({"error": "Not found"}), 404

@app.route("/api/professor/<path:email>/papers")
def professor_papers(email):
    for p in GERMAN_PROFESSORS + USA_PROFESSORS:
        if p.get("email","").lower() == email.lower():
            if p.get("scholar_url"):
                scraper = PaperScraper()
                papers = scraper.scrape_google_scholar(p["scholar_url"])
                return jsonify(papers)
            return jsonify([])
    return jsonify({"error": "Not found"}), 404

@app.route("/api/match-scores")
def get_match_scores():
    matcher = MatchScoreCalculator(PROFILE)
    return jsonify(matcher.calculate())

@app.route("/api/timeline")
def get_timeline():
    tl = TimelineGenerator(PROFILE)
    return jsonify(tl.generate())

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
```

- [ ] **Step 3: Verify Flask starts cleanly**

Run: `cd C:\Users\MSI\Desktop\Plan\scholarship-agent && python -c "from dashboard.app import app; print('Flask API loaded OK')"`
Expected: Prints "Flask API loaded OK" with no errors

- [ ] **Step 4: Commit**

Run: `git add dashboard/app.py requirements.txt && git commit -m "refactor: convert Flask to pure JSON API + add CORS"`

---

### Task 2: Create PaperScraper Feature

**Files:**
- Create: `features/paper_scraper.py`

- [ ] **Step 1: Write features/paper_scraper.py**

```python
import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime


class PaperScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def scrape_google_scholar(self, scholar_url, max_papers=10):
        try:
            resp = self.session.get(scholar_url, timeout=20)
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, "html.parser")
            papers = []
            for entry in soup.select("#gsc_a_b .gsc_a_tr")[:max_papers]:
                title_el = entry.select_one(".gsc_a_at")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link = title_el.get("href", "")
                if link and not link.startswith("http"):
                    link = "https://scholar.google.com" + link

                authors_venue = entry.select_one(".gs_gray")
                authors_venue_text = authors_venue.get_text(strip=True) if authors_venue else ""

                year_el = entry.select_one(".gsc_a_y span")
                year = year_el.get_text(strip=True) if year_el else ""

                cited_el = entry.select_one(".gsc_a_c a")
                citations = cited_el.get_text(strip=True) if cited_el else "0"

                papers.append({
                    "title": title,
                    "url": link,
                    "authors_venue": authors_venue_text,
                    "year": year,
                    "citations": citations,
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                time.sleep(1)
            return papers
        except Exception as e:
            print(f"  PaperScraper error for {scholar_url[:60]}: {e}")
            return []
```

- [ ] **Step 2: Test that PaperScraper loads**

Run: `cd C:\Users\MSI\Desktop\Plan\scholarship-agent && python -c "from features.paper_scraper import PaperScraper; ps = PaperScraper(); print('PaperScraper loaded OK')"`
Expected: Prints "PaperScraper loaded OK"

- [ ] **Step 3: Commit**

Run: `git add features/paper_scraper.py && git commit -m "feat: add PaperScraper for Google Scholar deep scraping"`

---

### Task 3: Enhance Orchestrator Scan Workflow

**Files:**
- Modify: `orchestrator.py`

- [ ] **Step 1: Add PaperScraper to orchestrator imports and scan**

Edit orchestrator.py line 16 to add:
```python
from features.paper_scraper import PaperScraper
```

Edit `run_all()` method to add deep scan of followed items before general scan:

```python
    def run_all(self):
        print("\n" + "=" * 60)
        print("  FULL SYSTEM SCAN (Deep + General)")
        print("=" * 60)

        proceed = input("\n  This will deep-scan followed items, then run full scan. Continue? (yes/no): ").strip().lower()
        if proceed != "yes":
            print("  Cancelled.")
            return

        # Deep scan followed professors
        followed = self._load_followed()
        scraper = PaperScraper()
        for pname in followed.get("professors", []):
            print(f"  Deep scanning professor: {pname}")
            prof = None
            for p in GERMAN_PROFESSORS + USA_PROFESSORS:
                if p["name"] == pname:
                    prof = p
                    break
            if prof and prof.get("scholar_url"):
                papers = scraper.scrape_google_scholar(prof["scholar_url"])
                print(f"    Found {len(papers)} papers for {pname}")
                # Save papers to data file
                import json, os
                papers_file = os.path.join(os.path.dirname(__file__), "data", "papers_cache.json")
                cache = {}
                if os.path.exists(papers_file):
                    with open(papers_file, "r") as f:
                        cache = json.load(f)
                cache[pname] = papers
                with open(papers_file, "w") as f:
                    json.dump(cache, f, indent=2)

        # Deep scan followed scholarships
        for sname in followed.get("scholarships", []):
            print(f"  Checking updates for scholarship: {sname}")

        # General scan
        self.scholarship_agent.run()
        self.university_agent.run()
        self.professor_agent.run()
        self.matcher.get_recommendations()
        self.cost_comp.show()
        self.timeline_gen.generate()

        print("\n  ✓ Full scan complete! Check the dashboard for all results.")

    def _load_followed(self):
        import json, os
        fpath = os.path.join(os.path.dirname(__file__), "data", "followed.json")
        if os.path.exists(fpath):
            with open(fpath, "r") as f:
                return json.load(f)
        return {"scholarships": [], "professors": []}
```

- [ ] **Step 2: Verify orchestrator loads**

Run: `cd C:\Users\MSI\Desktop\Plan\scholarship-agent && python -c "from orchestrator import Orchestrator; print('Orchestrator loaded OK')"`
Expected: Prints "Orchestrator loaded OK"

- [ ] **Step 3: Commit**

Run: `git add orchestrator.py && git commit -m "feat: enhance scan workflow with deep follow scanning"`

---

### Task 4: Set Up Vue 3 + Vite Frontend

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/App.vue`

- [ ] **Step 1: Create frontend/package.json**

```json
{
  "name": "scholarai-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^6.0.0"
  }
}
```

- [ ] **Step 2: Create frontend/vite.config.js**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
```

- [ ] **Step 3: Create frontend/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ScholarAI</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎓</text></svg>">
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/App.vue"></script>
</body>
</html>
```

- [ ] **Step 4: Create frontend/src/App.vue**

```vue
<script setup>
import { ref, onMounted } from 'vue'

const activeTab = ref('dashboard')
const data = ref(null)
const followed = ref({ scholarships: [], professors: [] })
const scanStatus = ref(null)

function toggle(tab) { activeTab.value = tab }

async function loadData() {
  try {
    const res = await fetch('/api/data')
    data.value = await res.json()
    followed.value = data.value.followed || { scholarships: [], professors: [] }
  } catch (e) {
    console.error('Failed to load data', e)
  }
}

async function toggleFollow(type, name) {
  const idx = followed.value[type].indexOf(name)
  if (idx > -1) {
    followed.value[type].splice(idx, 1)
  } else {
    followed.value[type].push(name)
  }
  await fetch('/api/followed', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ [type]: followed.value[type] })
  })
  loadData()
}

async function startScan() {
  const res = await fetch('/api/scan', { method: 'POST' })
  if (res.ok) {
    scanStatus.value = 'started'
    checkScan()
  }
}

async function checkScan() {
  const res = await fetch('/api/scan-status')
  const s = await res.json()
  scanStatus.value = s
  if (!s.done) {
    setTimeout(checkScan, 2000)
  } else {
    loadData()
  }
}

function clr(p) {
  p = parseInt(p) || 0
  return p >= 80 ? '#22c55e' : p >= 60 ? '#f97316' : '#ef4444'
}

function cmp(a, b) {
  return (parseInt(b.match) || 0) - (parseInt(a.match) || 0)
}

function isFav(type, name) {
  return (followed.value[type] || []).includes(name)
}

onMounted(loadData)
</script>

<template>
  <div class="app">
    <!-- Nav -->
    <nav class="nav">
      <div class="nav-brand">ScholarAI</div>
      <div class="nav-tabs">
        <button :class="{ active: activeTab === 'dashboard' }" @click="toggle('dashboard')">Dashboard</button>
        <button :class="{ active: activeTab === 'scholarships' }" @click="toggle('scholarships')">
          Scholarships <span class="badge">{{ data?.scholarships?.length || 0 }}</span>
        </button>
        <button :class="{ active: activeTab === 'professors' }" @click="toggle('professors')">
          Professors <span class="badge">{{ data?.professors?.length || 0 }}</span>
        </button>
        <button :class="{ active: activeTab === 'following' }" @click="toggle('following')">
          Following <span class="badge">{{ (followed.scholarships?.length || 0) + (followed.professors?.length || 0) }}</span>
        </button>
      </div>
      <div class="nav-scan">
        <button class="scan-btn" @click="startScan" :disabled="scanStatus?.running">
          {{ scanStatus?.running ? 'Scanning...' : '⟳ Scan' }}
        </button>
      </div>
    </nav>

    <!-- Scan Progress -->
    <div v-if="scanStatus?.running" class="scan-bar">
      <div class="scan-progress"></div>
      <span>{{ scanStatus.progress }}</span>
    </div>

    <!-- Dashboard Tab -->
    <div v-if="activeTab === 'dashboard'" class="tab-content">
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-num">{{ data?.scholarships?.length || 0 }}</div>
          <div class="stat-label">Scholarships</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ data?.professors?.length || 0 }}</div>
          <div class="stat-label">Professors</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ data?.universities?.length || 0 }}</div>
          <div class="stat-label">Universities</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ (followed.scholarships?.length || 0) + (followed.professors?.length || 0) }}</div>
          <div class="stat-label">Following</div>
        </div>
      </div>

      <h3>Match Scores</h3>
      <div v-for="s in (data?.scores || [])" :key="s.name" class="match-card">
        <div class="match-header">
          <span class="match-name">{{ s.name }}</span>
          <span class="match-score" :style="{ color: clr(parseFloat(s.overall) * 10) }">{{ s.overall }}/10</span>
        </div>
        <div class="match-bar">
          <div :style="{ width: (parseFloat(s.overall) * 10) + '%', background: clr(parseFloat(s.overall) * 10) }"></div>
        </div>
        <div class="match-rec">{{ s.recommendation }}</div>
      </div>

      <h3>Timeline</h3>
      <div v-for="m in (data?.timeline || [])" :key="m.phase" class="tl-item" :class="{ critical: (m.priority||'').toLowerCase() === 'critical' }">
        <div class="tl-phase">{{ m.priority ? '['+m.priority+'] ' : '' }}{{ m.phase }} — {{ m.period }}</div>
        <div class="tl-tasks">
          <div v-for="t in (m.tasks || [])" :key="t">• {{ t }}</div>
        </div>
      </div>
    </div>

    <!-- Scholarships Tab -->
    <div v-if="activeTab === 'scholarships'" class="tab-content">
      <div class="card-grid">
        <div v-for="s in [...(data?.scholarships || [])].sort(cmp)" :key="s.name" class="card">
          <button class="heart" :class="{ loved: isFav('scholarships', s.name) }" @click="toggleFollow('scholarships', s.name)">
            {{ isFav('scholarships', s.name) ? '❤' : '♡' }}
          </button>
          <div class="card-name">{{ s.name }}</div>
          <div class="card-sub">{{ s.provider || '' }} · {{ s.country || '' }}</div>
          <div class="card-tags">
            <span v-if="s.coverage_type">{{ s.coverage_type }}</span>
            <span v-if="s.amount">{{ s.amount }} {{ s.currency }}</span>
            <span class="match-pct" :style="{ background: clr(s.match) }">{{ s.match || '?' }}%</span>
          </div>
          <div class="card-stats">Deadline: <b>{{ s.deadline_end || s.deadline_start || 'Check website' }}</b></div>
          <details>
            <summary>Details</summary>
            <div class="detail-row"><span class="dl">Coverage</span><span>{{ s.coverage || '-' }}</span></div>
            <div class="detail-row"><span class="dl">Eligibility</span><span>{{ s.nationality || '-' }}</span></div>
            <div class="detail-row"><span class="dl">Documents</span><span>{{ s.documents || '-' }}</span></div>
            <div class="detail-row"><span class="dl">Language</span><span>{{ s.lang_app || '-' }} | Test: {{ s.english_test || '-' }}</span></div>
            <div class="detail-row"><span class="dl">GRE</span><span>{{ s.gre || '-' }}</span></div>
            <div class="detail-row"><span class="dl">Duration</span><span>{{ s.duration || '-' }}</span></div>
            <div class="detail-row"><span class="dl">Interview</span><span>{{ s.interview || '-' }}</span></div>
            <div class="detail-row"><span class="dl">Portal</span><span><a :href="s.portal" target="_blank" v-if="s.portal">{{ s.portal.slice(0, 60) }}...</a></span></div>
            <div class="detail-row"><span class="dl">URL</span><span><a :href="s.url" target="_blank" v-if="s.url">Open →</a></span></div>
            <div class="detail-row"><span class="dl">Strategy</span><span>{{ s.strategy || '-' }}</span></div>
          </details>
        </div>
      </div>
    </div>

    <!-- Professors Tab -->
    <div v-if="activeTab === 'professors'" class="tab-content">
      <div class="card-grid">
        <div v-for="p in (data?.professors || [])" :key="p.name + p.university" class="card">
          <button class="heart" :class="{ loved: isFav('professors', p.name) }" @click="toggleFollow('professors', p.name)">
            {{ isFav('professors', p.name) ? '❤' : '♡' }}
          </button>
          <div class="card-name">{{ p.name }}</div>
          <div class="card-sub">{{ p.title || '' }} @ {{ p.university || '' }}</div>
          <div class="card-tags">
            <span>h-index: {{ p.h_index || '?' }}</span>
            <span v-if="p.email">{{ p.email }}</span>
          </div>
          <details>
            <summary>Details</summary>
            <div class="detail-row"><span class="dl">Department</span><span>{{ p.department || '-' }}</span></div>
            <div class="detail-row"><span class="dl">Research</span><span>{{ p.interests || '-' }}</span></div>
            <div class="detail-row"><span class="dl">Funding</span><span>{{ p.funding || '-' }}</span></div>
            <div class="detail-row"><span class="dl">Courses</span><span>{{ p.courses || '-' }}</span></div>

            <div class="detail-row"><span class="dl">Google Scholar</span><span><a :href="p.scholar_url" target="_blank" v-if="p.scholar_url">Open →</a></span></div>
            <div class="detail-row"><span class="dl">Profile</span><span><a :href="p.profile_url" target="_blank" v-if="p.profile_url">Open →</a></span></div>
            <div class="detail-row"><span class="dl">Strategy</span><span>{{ p.strategy || '-' }}</span></div>

            <!-- Deep Papers for followed professors -->
            <div v-if="isFav('professors', p.name) && p._deep_papers && p._deep_papers.length > 0" class="papers-section">
              <div class="papers-title">Recent Publications</div>
              <div v-for="(paper, i) in p._deep_papers" :key="i" class="paper-row">
                <a :href="paper.url" target="_blank" v-if="paper.url">{{ paper.title }}</a>
                <span v-else>{{ paper.title }}</span>
                <div class="paper-meta">{{ paper.authors_venue }} · {{ paper.year }} · Cited: {{ paper.citations }}</div>
              </div>
            </div>
          </details>
        </div>
      </div>
    </div>

    <!-- Following Tab -->
    <div v-if="activeTab === 'following'" class="tab-content">
      <h3>Followed Scholarships</h3>
      <div v-if="(followed.scholarships || []).length === 0" class="empty">No followed scholarships yet. Click ♡ on any scholarship.</div>
      <div class="card-grid">
        <div v-for="s in (data?.scholarships || []).filter(s => isFav('scholarships', s.name))" :key="s.name" class="card">
          <button class="heart loved" @click="toggleFollow('scholarships', s.name)">❤</button>
          <div class="card-name">{{ s.name }}</div>
          <div class="card-sub">{{ s.provider }} · {{ s.country }}</div>
          <div class="card-tags">
            <span>{{ s.coverage_type }}</span>
            <span>{{ s.amount }} {{ s.currency }}</span>
            <span class="match-pct" :style="{ background: clr(s.match) }">{{ s.match }}%</span>
          </div>
          <details>
            <summary>Details</summary>
            <div class="detail-row"><span class="dl">Deadline</span><span>{{ s.deadline_end || s.deadline_start }}</span></div>
            <div class="detail-row"><span class="dl">Strategy</span><span>{{ s.strategy }}</span></div>
            <div class="detail-row"><span class="dl">URL</span><span><a :href="s.url" target="_blank">Open →</a></span></div>
          </details>
        </div>
      </div>

      <h3>Followed Professors</h3>
      <div v-if="(followed.professors || []).length === 0" class="empty">No followed professors yet. Click ♡ on any professor.</div>
      <div class="card-grid">
        <div v-for="p in (data?.professors || []).filter(p => isFav('professors', p.name))" :key="p.name" class="card">
          <button class="heart loved" @click="toggleFollow('professors', p.name)">❤</button>
          <div class="card-name">{{ p.name }}</div>
          <div class="card-sub">{{ p.title }} @ {{ p.university }}</div>
          <div class="card-tags"><span>h-index: {{ p.h_index }}</span></div>
          <details>
            <summary>Details & Papers</summary>
            <div class="detail-row"><span class="dl">Email</span><span>{{ p.email }}</span></div>
            <div class="detail-row"><span class="dl">Research</span><span>{{ p.interests }}</span></div>
            <div class="detail-row"><span class="dl">Scholar</span><span><a :href="p.scholar_url" target="_blank">Open →</a></span></div>
            <div v-if="p._deep_papers && p._deep_papers.length > 0" class="papers-section">
              <div class="papers-title">Recent Publications</div>
              <div v-for="(paper, i) in p._deep_papers" :key="i" class="paper-row">
                <a :href="paper.url" target="_blank" v-if="paper.url">{{ paper.title }}</a>
                <span v-else>{{ paper.title }}</span>
                <div class="paper-meta">{{ paper.authors_venue }} · {{ paper.year }} · {{ paper.citations }} citations</div>
              </div>
            </div>
          </details>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0b1120;color:#e2e8f0;line-height:1.5}

.app{max-width:1200px;margin:0 auto;padding:16px}

/* Nav */
.nav{background:linear-gradient(135deg,#1a365d,#0b1120);border-radius:10px;padding:12px 18px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;border:1px solid #1e3a5f;margin-bottom:12px}
.nav-brand{font-size:20px;font-weight:700;background:linear-gradient(90deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.nav-tabs{display:flex;gap:4px;flex:1;flex-wrap:wrap}
.nav-tabs button{padding:6px 14px;border-radius:6px;border:1px solid transparent;background:transparent;color:#94a3b8;cursor:pointer;font-size:13px;font-weight:500;transition:all .2s}
.nav-tabs button:hover{background:#1e293b;color:#e2e8f0}
.nav-tabs button.active{background:#1e3a5f;color:#60a5fa;border-color:#3b82f6}
.badge{background:#334155;color:#94a3b8;font-size:10px;padding:1px 7px;border-radius:8px;margin-left:4px}
.scan-btn{padding:8px 20px;background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer}
.scan-btn:hover{background:linear-gradient(135deg,#2563eb,#1d4ed8)}
.scan-btn:disabled{opacity:.4;cursor:not-allowed}

/* Scan progress */
.scan-bar{background:#1e293b;padding:8px 14px;border-radius:6px;margin-bottom:10px;font-size:12px;color:#94a3b8;display:flex;align-items:center;gap:10px}
.scan-progress{width:14px;height:14px;border:2px solid #3b82f6;border-top-color:transparent;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* Stats */
.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:16px}
.stat-card{background:linear-gradient(135deg,#1e293b,#0f172a);border:1px solid #2d3a50;border-radius:8px;padding:14px;text-align:center}
.stat-num{font-size:28px;font-weight:700;color:#60a5fa}
.stat-label{font-size:11px;color:#94a3b8;margin-top:2px}

/* Cards */
.card-grid{display:grid;gap:6px}
.card{background:#1e293b;border:1px solid #2d3a50;border-radius:7px;padding:10px 12px;position:relative;transition:border-color .2s}
.card:hover{border-color:#3b82f6}
.card-name{font-weight:600;font-size:13px;color:#e2e8f0;padding-right:24px}
.card-sub{color:#94a3b8;font-size:11px;margin-top:2px}
.card-tags{display:flex;gap:4px;margin-top:5px;flex-wrap:wrap}
.card-tags span{background:#0f172a;padding:1px 6px;border-radius:4px;font-size:10px;color:#93c5fd;border:1px solid #1e3a5f}
.card-stats{font-size:11px;color:#94a3b8;margin-top:5px}
.card-stats b{color:#e2e8f0}
.match-pct{font-weight:600;color:#fff;padding:1px 7px;border-radius:4px;font-size:10px}

/* Heart */
.heart{position:absolute;top:8px;right:10px;cursor:pointer;font-size:16px;color:#475569;transition:all .2s;background:none;border:none;z-index:2}
.heart.loved{color:#ef4444}
.heart:hover{transform:scale(1.2)}

/* Details */
details{margin-top:6px}
summary{color:#60a5fa;font-size:11px;cursor:pointer;display:inline-block;padding:2px 0}
summary:hover{text-decoration:underline}
.detail-row{display:flex;padding:3px 0;gap:8px;font-size:12px;border-bottom:1px solid #0f172a}
.detail-row:last-child{border-bottom:none}
.dl{color:#64748b;min-width:100px;flex-shrink:0}
.detail-row a{color:#60a5fa;text-decoration:none}
.detail-row a:hover{text-decoration:underline}

/* Papers */
.papers-section{margin-top:8px;padding-top:6px;border-top:1px solid #3b82f6}
.papers-title{font-weight:600;font-size:12px;color:#60a5fa;margin-bottom:4px}
.paper-row{padding:4px 0;font-size:11px}
.paper-row a{color:#60a5fa;text-decoration:none;font-weight:500}
.paper-row a:hover{text-decoration:underline}
.paper-meta{color:#64748b;font-size:10px;margin-top:1px}

/* match */
.match-card{background:#0f172a;border-radius:5px;padding:8px 12px;margin-bottom:4px}
.match-header{display:flex;justify-content:space-between;align-items:center}
.match-name{font-weight:600;font-size:13px;color:#60a5fa}
.match-score{font-weight:700;font-size:13px}
.match-bar{background:#334155;height:5px;border-radius:3px;margin:5px 0;overflow:hidden}
.match-bar div{height:100%;border-radius:3px;transition:width .3s}
.match-rec{font-size:11px;color:#94a3b8}

/* timeline */
.tl-item{padding:6px 12px;border-left:3px solid #3b82f6;margin-bottom:4px;background:#0f172a;border-radius:0 4px 4px 0;font-size:12px}
.tl-item.critical{border-left-color:#ef4444}
.tl-phase{font-weight:600;font-size:13px;color:#60a5fa}
.tl-tasks{padding-left:12px;margin-top:3px;color:#94a3b8}

.tab-content h3{font-size:14px;font-weight:600;color:#e2e8f0;margin:14px 0 8px}
.empty{color:#64748b;font-size:12px;padding:12px;text-align:center;background:#1e293b;border-radius:6px;border:1px dashed #2d3a50}
</style>
```

- [ ] **Step 5: Install npm dependencies**

Run: `cd C:\Users\MSI\Desktop\Plan\scholarship-agent\frontend && npm install`
Expected: npm installs vue, vite, @vitejs/plugin-vue

- [ ] **Step 6: Verify Vue dev server starts**

Run: `cd C:\Users\MSI\Desktop\Plan\scholarship-agent\frontend && npx vite --port 3000`
Expected: Vite dev server starts on port 3000. (Ctrl+C to stop after confirming)

- [ ] **Step 7: Commit**

Run: `git add frontend/ && git commit -m "feat: add Vue 3 + Vite frontend"`

---

### Task 5: Update main.py and Config

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update main.py to serve Vue build in production**

Edit main.py's `--web` branch to serve the frontend dist if it exists:

```python
    elif args.web:
        print("Starting Web Dashboard...")
        os.chdir(os.path.dirname(__file__))
        from dashboard.app import app
        # Serve Vue build if available
        vue_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
        if os.path.exists(vue_dist):
            from flask import send_from_directory
            @app.route("/")
            def serve_vue():
                return send_from_directory(vue_dist, "index.html")
            @app.route("/assets/<path:path>")
            def serve_assets(path):
                return send_from_directory(os.path.join(vue_dist, "assets"), path)
        import webbrowser
        webbrowser.open("http://localhost:5000")
        app.run(debug=True, port=5000)
```

- [ ] **Step 2: Verify main.py loads**

Run: `cd C:\Users\MSI\Desktop\Plan\scholarship-agent && python -c "import main; print('main.py loaded OK')"`
Expected: Prints "main.py loaded OK"

- [ ] **Step 3: Commit**

Run: `git add main.py && git commit -m "feat: serve Vue frontend from Flask in production"`

---

### Task 6: End-to-End Smoke Test

- [ ] **Step 1: Build Vue frontend**

Run: `cd C:\Users\MSI\Desktop\Plan\scholarship-agent\frontend && npx vite build`
Expected: Builds to frontend/dist/

- [ ] **Step 2: Start Flask server**

Run: `cd C:\Users\MSI\Desktop\Plan\scholarship-agent && python main.py --web`
Expected: Flask starts on port 5000, opens browser

- [ ] **Step 3: Hit API endpoint to verify**

Run: `curl http://localhost:5000/api/data 2>$null | Select-Object -First 5`
Expected: Returns JSON with scholarships, professors, universities data

- [ ] **Step 4: Stop server**

Press Ctrl+C in the Flask terminal

- [ ] **Step 5: Commit any final changes**

Run: `git add -A && git commit -m "chore: final adjustments after smoke test"`
