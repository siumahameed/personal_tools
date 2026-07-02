"""DynamicDocumentCrawler — auto-discovers real scholarship documents from across the internet.

Phases:
  1. GitHub Discovery: search repos, crawl for document files
  2. Link Crawling: follow links from discovered pages (depth 1)
  3. GROQ Gap Analysis: LLM generates targeted queries based on collection gaps
  4. GROQ Classification: classify candidates before adding to collection

State is saved to data/crawler_state.json for resumability.
"""
import os, json, re, time, hashlib, logging
from urllib.request import Request, urlopen
from urllib.parse import urlparse, quote

from agents.base import BaseAgent

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.join(os.path.dirname(__file__), '..', '..'), "data")
DOCUMENTS_FILE = os.path.join(DATA_DIR, "scholar_documents.json")
STATE_FILE = os.path.join(DATA_DIR, "crawler_state.json")

# ─── GitHub search queries ─────────────────────────────────────────
GITHUB_SEARCH_QUERIES = [
    "scholarship SOP",
    "statement of purpose scholarship",
    "scholarship application documents",
    "DAAD scholarship documents",
    "Fulbright SOP",
    "Erasmus Mundus motivation letter",
    "scholarship CV resume",
    "recommendation letter scholarship",
    "PhD application documents",
    "graduate school application documents",
    "study plan scholarship",
    "research proposal scholarship",
    "scholarship winners documents",
    "scholarship essay samples",
    "motivation letter scholarship",
]

# ─── Document detection ────────────────────────────────────────────
FILE_EXTENSIONS = {".pdf", ".md", ".txt", ".docx", ".doc", ".rtf", ".odt"}
SKIP_FILENAMES = {
    ".gitkeep", "readme.md", "readme", "readme.txt", "readme.rst",
    "license", "license.txt", "index.md", "contributing.md",
    "changelog.md", "package.json", "package-lock.json",
    "yarn.lock", "requirements.txt", "setup.py", "Makefile",
    "Dockerfile", ".dockerignore", ".gitignore", ".gitattributes",
    ".editorconfig", ".prettierrc", ".eslintrc", "tsconfig.json",
}
SKIP_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".go", ".rb", ".php", ".swift",
    ".kt", ".rs", ".scala", ".html", ".css", ".scss",
    ".less", ".json", ".xml", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".conf", ".sh", ".bat", ".ps1",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib",
    ".ipynb", ".csv", ".xlsx", ".xls",
    ".ppt", ".pptx",
}

SCHOLARSHIP_DOC_PATTERNS = [
    r'statement\s*of\s*purpose', r'\bsop\b', r'personal\s*statement',
    r'motivation\s*letter', r'cover\s*letter', r'scholarship\s*essay',
    r'study\s*plan', r'research\s*proposal', r'recommendation\s*letter',
    r'\blor\b', r'letter\s*of\s*recommendation', r'curriculum\s*vitae',
    r'\bcv\b', r'resume', r'certificate', r'application\s*essay',
    r'statement\s*of\s*purpose', r'personal\s*essay', r'academic\s*goals',
]

TYPE_KEYWORDS = {
    "sop": [r'statement\s*of\s*purpose', r'\bsop\b', r'personal\s*statement', r'application\s*essay'],
    "motivation_letter": [r'motivation\s*letter', r'cover\s*letter', r'motivational\s*letter', r'scholarship\s*essay'],
    "study_plan": [r'study\s*plan', r'studyplan', r'academic\s*plan', r'research\s*plan'],
    "research_proposal": [r'research\s*proposal', r'\bproposal\b', r'research\s*statement'],
    "recommendation": [r'recommendation\s*letter', r'\blor\b', r'letter\s*of\s*recommendation', r'reference\s*letter'],
    "resume": [r'curriculum\s*vitae', r'\bcv\b', r'resume', r'cv\_'],
    "certificate": [r'certificate', r'achievement', r'award', r'volunteer', r'participation'],
}


def get_groq_client():
    try:
        from groq import Groq
    except ImportError:
        return None
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        try:
            import dotenv
            dotenv.load_dotenv(os.path.join(DATA_DIR, "..", ".env"))
            api_key = os.environ.get("GROQ_API_KEY")
        except Exception:
            pass
    if not api_key:
        return None
    try:
        return Groq(api_key=api_key)
    except Exception:
        return None


def classify_with_groq(groq, title, url, snippet=""):
    """Ask GROQ to classify a candidate document. Returns dict or None."""
    if not groq:
        return None
    text = f"Title: {title}\nURL: {url}\nSnippet: {snippet}" if snippet else f"Title: {title}\nURL: {url}"
    try:
        resp = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "system",
                "content": (
                    "You classify scholarship application documents found online. "
                    "Return valid JSON with keys: document_type, scholarship, country, quality_score, is_real_document.\n"
                    "document_type: one of sop, motivation_letter, study_plan, research_proposal, recommendation, resume, certificate, other\n"
                    "scholarship: scholarship name (or null if unknown)\n"
                    "country: applicant's home country (or null)\n"
                    "quality_score: 1-5 (5 = real application document from a winner, 3+ means usable)\n"
                    "is_real_document: boolean (true if it's an actual application doc, not a template/guide)\n"
                    "Return ONLY the JSON, no other text."
                )
            }, {
                "role": "user",
                "content": f"Classify this document:\n{text}"
            }],
            temperature=0.1,
            max_tokens=100,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r'^```(?:json)?\s*|```\s*$', '', raw, flags=re.IGNORECASE).strip()
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"GROQ classification failed: {e}")
        return None


def generate_gap_queries(groq, stats):
    """Ask GROQ to generate search queries targeting collection gaps."""
    if not groq:
        return _default_gap_queries()
    prompt = (
        f"Current collection has these document types: {json.dumps(stats)}. "
        "Generate 5 web search queries to find missing real scholarship application documents "
        "(SOPs, CVs, recommendation letters) from actual winners worldwide. "
        "Return a JSON array of strings. No other text."
    )
    try:
        resp = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Return only a JSON array of 5 search query strings."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r'^```(?:json)?\s*|```\s*$', '', raw, flags=re.IGNORECASE).strip()
        queries = json.loads(raw)
        if isinstance(queries, list):
            return [q for q in queries if isinstance(q, str)][:5]
    except Exception as e:
        logger.warning(f"GROQ gap analysis failed: {e}")
    return _default_gap_queries()


def _default_gap_queries():
    return [
        "real scholarship winners CV resume PDF",
        "Fulbright scholarship recommendation letter example",
        "Erasmus Mundus motivation letter accepted sample",
        "DAAD study plan sample PDF",
        "scholarship application documents from winners blog post",
    ]


class DynamicDocumentCrawler:
    """Auto-discovers and collects real scholarship documents from across the web."""

    def __init__(self):
        self.base = BaseAgent("DynamicCrawler", interactive=False)
        self.groq = get_groq_client()
        self.state = self._load_state()
        self.existing_docs = self._load_existing_docs()
        self.existing_urls = {(d.get("url", "") or "").lower().strip() for d in self.existing_docs}
        self.existing_ids = {d.get("id", "") for d in self.existing_docs}
        self.new_docs = []
        self.github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")

    # ─── State Management ──────────────────────────────────────

    def _load_state(self):
        default = {
            "processed_github_repos": [],
            "processed_urls": [],
            "github_queries_run": [],
            "stats_before": {},
            "stats_after": {},
            "phase_progress": "idle",
        }
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, encoding="utf-8") as f:
                    return {**default, **json.load(f)}
            except Exception:
                pass
        return dict(default)

    def _save_state(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def _load_existing_docs(self):
        if os.path.exists(DOCUMENTS_FILE):
            try:
                with open(DOCUMENTS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("samples", [])
            except Exception:
                pass
        return []

    def _save_docs(self):
        all_samples = self.existing_docs + self.new_docs
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DOCUMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"samples": all_samples}, f, indent=2, ensure_ascii=False)

    # ─── Helpers ───────────────────────────────────────────────

    def _gen_id(self, url, prefix="ddc"):
        return f"{prefix}-{hashlib.md5(url.encode()).hexdigest()[:12]}"

    def _detect_type(self, filename):
        name_lower = filename.lower()
        for doc_type, patterns in TYPE_KEYWORDS.items():
            for pat in patterns:
                if re.search(pat, name_lower):
                    return doc_type
        return "other"

    def _is_document_file(self, filename):
        name_lower = filename.lower()
        if name_lower in SKIP_FILENAMES:
            return False
        ext = os.path.splitext(name_lower)[1].lower()
        if ext in SKIP_EXTENSIONS:
            return False
        if ext not in FILE_EXTENSIONS:
            return False
        stem = os.path.splitext(name_lower)[0]
        for pat in SCHOLARSHIP_DOC_PATTERNS:
            if re.search(pat, stem):
                return True
        return False

    def _is_actual_document_url(self, url):
        """Filter out generic sites — only keep real document hosting."""
        url_lower = url.lower().strip()
        skip_domains = {
            "scholarships.com", "scholars4dev.com", "scholarshipscorner.website",
            "globalscholarships.com", "scholarshipmonster.com",
            "internationalscholarships.com", "universityscholarships.net",
            "scholarship-positions.com", "scholarshipdb.net",
            "scholarshipbuddy.com", "scholars4.dev",
            "brokescholar.com", "scholarshiproar.com",
            "myscholarship.xyz", "scholarshipowl.com",
            "fastweb.com", "unigo.com", "cappex.com",
            "niche.com", "chegg.com", "peterson.com",
            "collegeboard.org", "bigfuture.collegeboard.org",
            "scholarshipamerica.org",
        }
        for domain in skip_domains:
            if domain in url_lower:
                return False
        good_extensions = (".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".odt")
        if url_lower.endswith(good_extensions):
            return True
        good_domains = {
            "github.com", "githubusercontent.com",
            "medium.com", "linkedin.com",
            "blogspot.com", "wordpress.com",
            "google.com", "docs.google.com",
            "drive.google.com",
        }
        parsed = urlparse(url)
        for gd in good_domains:
            if gd in parsed.netloc:
                return True
        return False

    def _is_duplicate(self, url):
        url_lower = url.lower().strip()
        if url_lower in self.existing_urls:
            return True
        sid = self._gen_id(url)
        if sid in self.existing_ids:
            return True
        for nd in self.new_docs:
            if nd.get("url", "").lower().strip() == url_lower:
                return True
            if nd.get("id", "") == sid:
                return True
        return False

    def _add_document(self, sample):
        sid = sample.get("id", "")
        url = (sample.get("url", "") or "").lower().strip()
        if sid in self.existing_ids:
            return False
        if url and url in self.existing_urls:
            return False
        self.new_docs.append(sample)
        self.existing_ids.add(sid)
        if url:
            self.existing_urls.add(url)
        return True

    def _detect_field(self, text):
        fields = {
            "computer science", "data science", "machine learning", "artificial intelligence",
            "statistics", "mathematics", "physics", "biology", "chemistry",
            "economics", "finance", "business", "engineering", "medicine",
            "law", "education", "psychology", "sociology", "political science",
            "environmental science", "public health", "neuroscience", "linguistics",
            "philosophy", "history", "literature", "anthropology", "archaeology",
        }
        text_lower = text.lower()
        matched = [f.title() for f in fields if f in text_lower]
        return ", ".join(matched[:3]) if matched else "General"

    def _github_headers(self):
        headers = {
            "User-Agent": "ScholarAI/1.0",
            "Accept": "application/vnd.github+json",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    def _fetch_json(self, url, headers=None):
        hdrs = {"User-Agent": "ScholarAI/1.0", "Accept": "application/json"}
        if headers:
            hdrs.update(headers)
        try:
            req = Request(url, headers=hdrs)
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            logger.debug(f"fetch_json failed: {url[:80]} -> {e}")
            return None

    # ═══════════════════════════════════════════════════════════
    # Phase 1: GitHub Discovery
    # ═══════════════════════════════════════════════════════════

    def _github_search(self, query, page=1):
        """Search GitHub repos. Returns list of repo items."""
        url = f"https://api.github.com/search/repositories?q={quote(query)}&sort=updated&per_page=30&page={page}"
        data = self._fetch_json(url, headers=self._github_headers())
        if data and "items" in data:
            return data["items"]
        return []

    def _list_github_contents(self, repo_full_name, path=""):
        """List files in a GitHub repo directory. Returns list of items."""
        api_url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}" if path else \
                  f"https://api.github.com/repos/{repo_full_name}/contents"
        items = self._fetch_json(api_url, headers=self._github_headers())
        return items if isinstance(items, list) else []

    def _crawl_repo(self, repo_full_name):
        """Traverse a GitHub repo looking for document files. Returns list of discovered docs."""
        discovered = []
        try:
            items = self._list_github_contents(repo_full_name)
        except Exception:
            return discovered
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            if item.get("type") == "dir":
                try:
                    sub_items = self._list_github_contents(repo_full_name, item["name"])
                except Exception:
                    continue
                for sub in sub_items:
                    if not isinstance(sub, dict):
                        continue
                    sub_name = sub.get("name", "")
                    if sub.get("type") != "file":
                        continue
                    if not self._is_document_file(sub_name):
                        continue
                    doc_url = sub.get("download_url", "")
                    if not doc_url:
                        continue
                    detected_type = self._detect_type(sub_name)
                    discovered.append({
                        "url": doc_url,
                        "name": sub_name,
                        "type": detected_type,
                        "repo": repo_full_name,
                    })
            elif item.get("type") == "file":
                if not self._is_document_file(name):
                    continue
                doc_url = item.get("download_url", "")
                if not doc_url:
                    continue
                detected_type = self._detect_type(name)
                discovered.append({
                    "url": doc_url,
                    "name": name,
                    "type": detected_type,
                    "repo": repo_full_name,
                })
            time.sleep(0.05)
        return discovered

    def run_github_discovery(self, max_repos_per_query=5):
        """Phase 1: Search GitHub for repos with scholarship docs, crawl each."""
        print("[Crawler] Phase 1: GitHub Discovery")
        total_added = 0
        for query in GITHUB_SEARCH_QUERIES:
            if query in self.state.get("github_queries_run", []):
                continue
            print(f"  Searching GitHub: {query[:50]}...")
            repos = self._github_search(query)
            if not repos:
                continue
            for repo in repos[:max_repos_per_query]:
                full_name = repo.get("full_name", "")
                if not full_name or full_name in self.state.get("processed_github_repos", []):
                    continue
                if repo.get("fork"):
                    continue
                lang = repo.get("language", "") or ""
                if lang.lower() not in ("", "python", "jupyter notebook", "html", "css", "javascript", "typescript", "none"):
                    continue
                print(f"    Crawling repo: {full_name}")
                docs = self._crawl_repo(full_name)
                if not docs:
                    continue
                added = 0
                for d in docs:
                    if self._is_duplicate(d["url"]):
                        continue
                    sample = {
                        "id": self._gen_id(d["url"], "gh-dynamic"),
                        "type": d["type"],
                        "title": d["name"].rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()[:200],
                        "scholar_name": f"GitHub – {full_name.split('/')[0]}",
                        "scholarship_name": "Multiple Scholarships",
                        "university": "Various",
                        "program": "Graduate Program",
                        "country": "Worldwide",
                        "field": self._detect_field(d["name"] + " " + full_name),
                        "url": d["url"],
                        "source": f"github:{full_name}",
                        "discovered_by": "github_dynamic",
                        "date_added": datetime.now().strftime("%Y-%m-%d"),
                    }
                    if self._add_document(sample):
                        added += 1
                total_added += added
                print(f"      +{added} new documents")
                self.state.setdefault("processed_github_repos", []).append(full_name)
                time.sleep(0.2)
            self.state.setdefault("github_queries_run", []).append(query)
            self._save_state()
        print(f"  GitHub Discovery done: +{total_added} documents")
        return total_added

    # ═══════════════════════════════════════════════════════════
    # Phase 2: Link Crawling
    # ═══════════════════════════════════════════════════════════

    def run_link_crawling(self, max_links_per_source=5, max_docs=30):
        """Phase 2: For each new doc URL, fetch parent page and extract links."""
        print("[Crawler] Phase 2: Link Crawling")
        candidates = [d for d in (self.existing_docs + self.new_docs) if d.get("discovered_by") != "github_dynamic"]
        candidates = candidates[:50]
        total_found = 0
        for doc in candidates:
            url = doc.get("url", "")
            if not url or url in self.state.get("processed_urls", []):
                continue
            print(f"  Crawling links from: {url[:70]}...")
            try:
                soup = self.base.fetch_page(url, cache=False)
            except Exception:
                continue
            if not soup:
                continue
            links = self.base.extract_links(soup, "a[href]", base_url=url)
            crawled = 0
            for link in links[:max_links_per_source]:
                target = link.get("url", "")
                if not target or self._is_duplicate(target):
                    continue
                if not self._is_actual_document_url(target):
                    continue
                if total_found >= max_docs:
                    break
                title = link.get("text", "") or os.path.basename(target)
                detected_type = self._detect_type(title + " " + target)
                sample = {
                    "id": self._gen_id(target, "link-crawl"),
                    "type": detected_type,
                    "title": title[:200] if title else os.path.basename(target)[:200],
                    "scholar_name": "Web Discovery",
                    "scholarship_name": "Multiple Scholarships",
                    "university": "Various",
                    "program": "Graduate Program",
                    "country": "Worldwide",
                    "field": self._detect_field(title + " " + target),
                    "url": target,
                    "source": url,
                    "discovered_by": "link_crawl",
                    "date_added": datetime.now().strftime("%Y-%m-%d"),
                }
                if self._add_document(sample):
                    total_found += 1
                    crawled += 1
            self.state.setdefault("processed_urls", []).append(url)
            self._save_state()
            if total_found >= max_docs:
                break
        print(f"  Link Crawling done: +{total_found} documents")
        return total_found

    # ═══════════════════════════════════════════════════════════
    # Phase 3: GROQ Gap Analysis
    # ═══════════════════════════════════════════════════════════

    def run_gap_analysis(self, max_queries=5):
        """Phase 3: Use GROQ to generate targeted queries, run web search."""
        print("[Crawler] Phase 3: Gap Analysis")
        all_docs = self.existing_docs + self.new_docs
        stats = {}
        for d in all_docs:
            t = d.get("type", "unknown")
            stats[t] = stats.get(t, 0) + 1

        queries = generate_gap_queries(self.groq, stats) if self.groq else _default_gap_queries()
        queries = queries[:max_queries]
        print(f"  Generated {len(queries)} gap queries")
        total_found = 0
        for q in queries:
            print(f"  Searching: {q[:60]}...")
            results = self.base.search_web(q, num_results=5)
            if not results:
                continue
            for r in results:
                url = r.get("url", "")
                if not url or self._is_duplicate(url):
                    continue
                if not self._is_actual_document_url(url):
                    continue
                title = r.get("title", "") or os.path.basename(url)
                detected_type = self._detect_type(title + " " + url)
                if detected_type == "other" and self.groq:
                    cls = classify_with_groq(self.groq, title, url, r.get("snippet", ""))
                    if cls:
                        detected_type = cls.get("document_type", "other")
                        q_score = cls.get("quality_score", 1)
                        if not cls.get("is_real_document", False) or q_score < 3:
                            continue
                if detected_type == "other":
                    continue
                sample = {
                    "id": self._gen_id(url, "gap-search"),
                    "type": detected_type,
                    "title": title[:200],
                    "scholar_name": "Web Discovery",
                    "scholarship_name": "Multiple Scholarships",
                    "university": "Various",
                    "program": "Graduate Program",
                    "country": "Worldwide",
                    "field": self._detect_field(title + " " + url),
                    "url": url,
                    "source": f"web_search:{q[:40]}",
                    "discovered_by": "groq_query",
                    "date_added": datetime.now().strftime("%Y-%m-%d"),
                }
                if self._add_document(sample):
                    total_found += 1
            self._save_state()
        print(f"  Gap Analysis done: +{total_found} documents")
        return total_found

    # ═══════════════════════════════════════════════════════════
    # Orchestrator
    # ═══════════════════════════════════════════════════════════

    def run(self, github_only=False, link_crawl=False):
        """Run all phases sequentially."""
        print("=" * 60)
        print("DynamicDocumentCrawler — Starting")
        print("=" * 60)
        self.state["stats_before"] = self._get_stats()
        total = 0
        total += self.run_github_discovery()
        if not github_only:
            if link_crawl:
                total += self.run_link_crawling()
            total += self.run_gap_analysis()
        self._save_docs()
        self.state["stats_after"] = self._get_stats()
        self.state["phase_progress"] = "done"
        self._save_state()
        print(f"\n{'=' * 60}")
        print(f"Done. +{total} new documents added to scholar_documents.json")
        print(f"Total: {len(self.existing_docs) + len(self.new_docs)} documents")
        print(f"{'=' * 60}")
        return total

    def _get_stats(self):
        all_docs = self.existing_docs + self.new_docs
        stats = {}
        for d in all_docs:
            t = d.get("type", "unknown")
            stats[t] = stats.get(t, 0) + 1
        order = ["sop", "motivation_letter", "study_plan", "research_proposal", "recommendation", "resume", "certificate", "other"]
        return {k: stats.get(k, 0) for k in order}


# ─── CLI entry point ───────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DynamicDocumentCrawler")
    parser.add_argument("--github-only", action="store_true", help="Only run GitHub discovery phase")
    parser.add_argument("--link-crawl", action="store_true", help="Also run link crawling phase (slow)")
    args = parser.parse_args()
    crawler = DynamicDocumentCrawler()
    crawler.run(github_only=args.github_only, link_crawl=args.link_crawl)
