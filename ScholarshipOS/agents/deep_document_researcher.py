import os
import re
import json
import time
import random
import hashlib
from datetime import datetime
from urllib.parse import urlparse, quote_plus
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from agents.base import BaseAgent

DOCUMENTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "scholar_documents.json"
)

DEEP_RESEARCH_LOG = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "deep_research_log.json"
)

FIELD_KEYWORDS = [
    "machine learning", "deep learning", "artificial intelligence",
    "data science", "statistics", "computer science", "computer vision",
    "nlp", "data engineering", "ml", "ai", "software engineering",
    "electrical engineering", "computer engineering", "robotics",
    "renewable energy", "power engineering", "bioengineering",
    "signal processing", "embedded systems", "data analytics",
    "mathematics", "applied math", "quantitative", "actuarial",
    "physics", "chemistry", "biology", "biochemistry", "neuroscience",
    "economics", "finance", "business", "psychology",
    "environmental science", "civil engineering", "mechanical engineering",
]

TYPE_KEYWORDS = {
    "sop": ["sop", "statement of purpose", "motivation letter", "personal statement",
            "application essay", "study plan", "research proposal", "motivation",
            "statement-of-purpose", "personal-statement", "study-plan"],
    "resume": ["cv", "resume", "curriculum vitae", "curriculum-vitae"],
    "recommendation": ["lor", "recommendation", "reference letter", "letter of recommendation",
                       "recommendation-letter", "reference"],
}


class DeepDocumentResearcher:
    """Advanced document researcher that uses multiple APIs and web sources to find real scholar documents."""

    def __init__(self, progress_callback=None, force=False):
        self.progress_callback = progress_callback
        self.force = force
        self.existing_docs = self._load_existing()
        self.existing_urls = {(d.get("url", "") or "").lower().strip() for d in self.existing_docs}
        self.existing_ids = {d.get("id", "") for d in self.existing_docs}
        self.new_samples = []
        self.research_log = self._load_log()

    def _load_existing(self):
        if os.path.exists(DOCUMENTS_FILE):
            try:
                with open(DOCUMENTS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("samples", [])
            except Exception:
                return []
        return []

    def _load_log(self):
        if os.path.exists(DEEP_RESEARCH_LOG):
            try:
                with open(DEEP_RESEARCH_LOG, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        all_samples = self.existing_docs + self.new_samples
        with open(DOCUMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"samples": all_samples}, f, indent=2, ensure_ascii=False)
        with open(DEEP_RESEARCH_LOG, "w", encoding="utf-8") as f:
            json.dump(self.research_log, f, indent=2, ensure_ascii=False)

    def _progress(self, msg):
        if self.progress_callback:
            self.progress_callback(msg)

    def _gen_id(self, prefix, url):
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"{prefix}-{url_hash}"

    def _detect_field(self, text):
        text_lower = text.lower()
        matched = []
        for kw in FIELD_KEYWORDS:
            if kw in text_lower:
                matched.append(kw.title())
        return ", ".join(matched[:3]) if matched else "General"

    def _detect_type(self, text, filename=""):
        combined = f"{filename} {text}".lower()
        for doc_type, keywords in TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in combined:
                    return doc_type
        return "document"

    def _add_sample(self, sample):
        sid = sample.get("id", "")
        url = sample.get("url", "").lower().strip()
        if sid in self.existing_ids:
            return False
        if url and url in self.existing_urls:
            return False
        self.new_samples.append(sample)
        self.existing_ids.add(sid)
        if url:
            self.existing_urls.add(url)
        return True

    def _fetch_json(self, url, headers=None):
        default_headers = {"User-Agent": "ScholarAI/1.0", "Accept": "application/json"}
        if headers:
            default_headers.update(headers)
        try:
            req = Request(url, headers=default_headers)
            with urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    def _fetch_text(self, url):
        try:
            req = Request(url, headers={"User-Agent": "ScholarAI/1.0"})
            with urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None

    def _github_headers(self):
        headers = {
            "User-Agent": "ScholarAI/1.0",
            "Accept": "application/vnd.github+json",
        }
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def phase_1_github_discovery(self):
        """Discover new GitHub repos with scholarship documents."""
        self._progress("Phase 1/6: Discovering GitHub repositories with scholarship documents...")
        added = 0

        search_queries = [
            "scholarship application documents",
            "sop scholarship winner",
            "statement of purpose samples",
            "motivation letter scholarship",
            "study plan scholarship",
            "graduate school sop",
            "phd application sop",
            "erasmus mundus sop",
            "fulbright sop",
            "daad sop",
        ]

        discovered_repos = set()
        for query in search_queries:
            try:
                search_url = f"https://api.github.com/search/repositories?q={quote_plus(query)}&sort=stars&order=desc&per_page=5"
                data = self._fetch_json(search_url, headers=self._github_headers())
                if data and "items" in data:
                    for repo in data["items"]:
                        full_name = repo.get("full_name", "")
                        if full_name:
                            discovered_repos.add(full_name)
            except Exception:
                pass
            time.sleep(0.2)

        self.research_log["github_repos_found"] = len(discovered_repos)
        if discovered_repos:
            self._progress(f"  Found {len(discovered_repos)} repositories to scan")

        for repo in discovered_repos:
            added += self._scan_github_repo(repo)

        return added

    def _scan_github_repo(self, repo_slug):
        """Scan a single GitHub repo for document files."""
        added = 0
        folders_to_check = [
            "", "SOP", "Statement-of-Purpose", "sop", "Statements", "Personal-Statement",
            "Essays", "Motivation", "Motivation-Letter", "documents",
            "CV", "Resume", "cv", "resume", "Curriculum-Vitae",
            "Recommendation-Letters", "LOR", "lor", "Recommendations",
            "Reference-Letters", "samples", "examples",
        ]

        for folder in folders_to_check:
            try:
                api_url = f"https://api.github.com/repos/{repo_slug}/contents/{folder}" if folder else \
                          f"https://api.github.com/repos/{repo_slug}/contents"
                items = self._fetch_json(api_url, headers=self._github_headers())
                if not items or not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") != "file":
                        continue
                    name = item.get("name", "")
                    if name.lower() in (".gitkeep", "readme.md", "license", "license.txt"):
                        continue
                    doc_url = item.get("download_url", "")
                    if not doc_url:
                        continue
                    field = self._detect_field(name)
                    doc_type = self._detect_type(name, name)
                    title = name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
                    sample = {
                        "id": self._gen_id("gh", doc_url),
                        "type": doc_type,
                        "title": title[:200],
                        "scholar_name": "GitHub Repository",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "Global",
                        "field": field,
                        "url": doc_url,
                        "source": f"GitHub: {repo_slug}",
                        "description": f"Application document from GitHub repository {repo_slug}",
                        "key_takeaways": [
                            "Study real successful application documents",
                            "Note formatting and content structure",
                            "Adapt to your own background and goals"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
            except Exception:
                pass
        return added

    def phase_2_semantic_scholar(self):
        """Search Semantic Scholar API for relevant open-access papers."""
        self._progress("Phase 2/6: Searching Semantic Scholar for relevant papers...")
        added = 0

        queries = [
            "machine learning scholarship",
            "data science graduate admission",
            "artificial intelligence research",
            "deep learning applications",
            "statistical learning theory",
            "natural language processing",
            "computer vision advances",
            "reinforcement learning",
        ]

        for query in queries:
            try:
                url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote_plus(query)}&limit=10&fields=title,url,openAccessPdf,year,authors,externalIds"
                data = self._fetch_json(url)
                if not data or "data" not in data:
                    continue
                for paper in data["data"]:
                    title = paper.get("title", "")
                    if not title:
                        continue
                    paper_url = paper.get("url", "")
                    pdf_url = ""
                    oa = paper.get("openAccessPdf")
                    if oa and isinstance(oa, dict):
                        pdf_url = oa.get("url", "")
                    if not pdf_url:
                        pdf_url = paper_url
                    if not pdf_url:
                        continue
                    sample = {
                        "id": self._gen_id("ss", pdf_url),
                        "type": "paper",
                        "title": title[:200],
                        "scholar_name": "Research Paper",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "Global",
                        "field": self._detect_field(title),
                        "url": pdf_url,
                        "source": "Semantic Scholar",
                        "description": f"Academic paper in your target field: {title[:120]}",
                        "key_takeaways": [
                            "Reference cutting-edge research in your applications",
                            "Demonstrate knowledge of current research trends",
                            "Cite relevant papers in your statement of purpose"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
            except Exception:
                pass
            time.sleep(1)

        return added

    def phase_3_arxiv(self):
        """Fetch recent papers from arXiv in target categories."""
        self._progress("Phase 3/6: Fetching recent papers from arXiv...")
        added = 0

        categories = [
            "cs.AI", "cs.LG", "stat.ML", "cs.CV", "cs.CL",
            "cs.NE", "cs.IR", "cs.MA", "stat.CO",
        ]

        for cat in categories:
            try:
                url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&sortBy=submittedDate&sortOrder=descending&max_results=5"
                text = self._fetch_text(url)
                if not text:
                    continue
                import xml.etree.ElementTree as ET
                root = ET.fromstring(text)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                for entry in root.findall("atom:entry", ns):
                    title_el = entry.find("atom:title", ns)
                    title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""
                    id_el = entry.find("atom:id", ns)
                    paper_url = id_el.text.strip() if id_el is not None and id_el.text else ""
                    pdf_url = paper_url.replace("abs", "pdf") if paper_url else ""
                    if not title or not pdf_url:
                        continue
                    sample = {
                        "id": self._gen_id("arxiv", pdf_url),
                        "type": "paper",
                        "title": title[:200],
                        "scholar_name": "Research Paper",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "Global",
                        "field": self._detect_field(title),
                        "url": pdf_url,
                        "source": "arXiv",
                        "description": f"Recent arXiv paper in {cat}: {title[:120]}",
                        "key_takeaways": [
                            "Stay current with latest research in your field",
                            "Show admissions committees you follow cutting-edge work"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
            except Exception:
                pass
            time.sleep(0.5)

        return added

    def phase_4_web_search(self):
        """Search the web for publicly shared application documents."""
        self._progress("Phase 4/6: Searching web for shared application documents...")
        added = 0

        searches = [
            # General
            'site:docs.google.com "statement of purpose" "machine learning"',
            'site:docs.google.com "statement of purpose" "data science"',
            'site:docs.google.com "personal statement" "graduate school"',
            'site:medium.com "statement of purpose" "grad school"',
            'site:medium.com "how I got into" "PhD" "machine learning"',
            'site:reddit.com "statement of purpose" "review" "scholarship"',
            'site:reddit.com "SOP" "admitted" "graduate"',
            '"statement of purpose" "scholarship winner" pdf',
            '"motivation letter" "erasmus mundus" pdf',
            '"study plan" "scholarship" pdf sample',
            # Bangladeshi students
            '"statement of purpose" "Bangladesh" "scholarship" pdf',
            '"SOP" "Dhaka University" "masters" scholarship',
            '"motivation letter" "Bangladeshi" "DAAD" pdf',
            '"study plan" "Bangladesh" "Germany" scholarship',
            '"personal statement" "BUET" "graduate"',
            '"statement of purpose" "Bangladeshi student" "USA"',
            # Indian students
            '"statement of purpose" "Indian" "scholarship" "USA"',
            '"SOP" "IIT" "masters" "admission"',
            '"statement of purpose" "India" "DAAD" scholarship',
            '"motivation letter" "Indian student" "Germany" pdf',
            '"personal statement" "India" "MS" "Computer Science"',
            '"study plan" "Indian" "scholarship" "abroad"',
            # Pakistani students
            '"statement of purpose" "Pakistan" "scholarship" pdf',
            '"SOP" "NUST" "LUMS" "graduate"',
            '"motivation letter" "Pakistani" "HEC" scholarship',
            '"personal statement" "Pakistan" "MS" "abroad"',
            # South Asian general
            '"statement of purpose" "South Asian" "scholarship"',
            '"SOP" "developing country" "DAAD" sample',
            '"motivation letter" "commonwealth scholarship" pdf',
            '"statement of purpose" "third world" "scholarship"',
            '"research proposal" "DAAD" "Bangladesh" sample',
        ]

        try:
            agent = BaseAgent("doc-researcher", interactive=False)
            for query in searches:
                results = agent.search_web(query, num_results=3)
                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    if not url:
                        continue
                    field = self._detect_field(title + " " + snippet)
                    doc_type = self._detect_type(title, title)
                    sample = {
                        "id": self._gen_id("web", url),
                        "type": doc_type,
                        "title": title[:200],
                        "scholar_name": "Web Discovery",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "Global",
                        "field": field,
                        "url": url,
                        "source": "Web Search",
                        "description": (snippet or f"Application document found online: {title[:100]}")[:300],
                        "key_takeaways": [
                            "Learn from publicly shared successful applications",
                            "Note common patterns in strong applications"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
                time.sleep(1)
        except Exception as e:
            self._progress(f"  Web search error: {e}")

        return added

    def phase_5_university_scholarship_pages(self):
        """Scrape known scholarship program pages for document requirements and real examples."""
        self._progress("Phase 5/6: Collecting scholarship program details...")
        added = 0

        scholarship_pages = [
            ("DAAD Scholarship", "https://www.daad.de/en/study-and-research-in-germany/scholarships/"),
            ("Erasmus Mundus", "https://erasmus-plus.ec.europa.eu/opportunities"),
            ("Fulbright Program", "https://us.fulbrightonline.org/"),
            ("Knight-Hennessy", "https://knight-hennessy.stanford.edu/"),
            ("Chevening", "https://www.chevening.org/"),
            ("Gates Cambridge", "https://www.gatescambridge.org/"),
            ("Rhodes Scholarship", "https://www.rhodeshouse.ox.ac.uk/"),
            ("Commonwealth Scholarship", "http://cscuk.dfid.gov.uk/"),
        ]

        for name, url in scholarship_pages:
            try:
                text = self._fetch_text(url)
                if not text:
                    continue
                soup = BeautifulSoup(text, "html.parser")
                page_text = soup.get_text(separator=" ", strip=True)
                key_excerpts = []
                for sentence in re.split(r'(?<=[.!?])\s+', page_text[:5000]):
                    if any(kw in sentence.lower() for kw in ["document", "require", "apply", "eligibility", "deadline"]):
                        key_excerpts.append(sentence[:200])
                sample = {
                    "id": self._gen_id("scholarship-page", url),
                    "type": "document",
                    "title": f"{name} - Scholarship Program Details",
                    "scholar_name": name,
                    "scholarship_name": name,
                    "university": "",
                    "program": "Graduate Program",
                    "country": "Global",
                    "field": "General",
                    "url": url,
                    "source": "Official Scholarship Website",
                    "description": f"Official {name} scholarship page with application requirements",
                    "key_takeaways": key_excerpts[:3] or ["Visit the official website for detailed requirements"],
                    "collected_at": datetime.now().isoformat(),
                }
                if self._add_sample(sample):
                    added += 1
            except Exception:
                pass
            time.sleep(1)

        return added

    def phase_6_south_asian_documents(self):
        """Search for documents specifically from Bangladeshi, Indian, and Pakistani students."""
        self._progress("Phase 6/7: Collecting South Asian (Bangladesh/India/Pakistan) student documents...")
        added = 0

        south_asian_urls = [
            # Bangladeshi scholarship blogs and success stories
            ("Bangladeshi Student Guide to DAAD", "https://www.daad-bangladesh.org/"),
            ("Fulbright Bangladesh - Success Stories", "https://bd.usembassy.gov/education/fulbright/"),
            ("Bangladesh Scholarship Blog by Bangladeshi Students", "https://scholarshipbangladesh.blogspot.com/"),
            ("Study in Germany from Bangladesh Guide", "https://www.study-in.de/en/"),
            ("BUET Grad School Preparation Guide", "https://www.buet.ac.bd/"),
            # Indian student resources
            ("Indian Student Guide to US Graduate School", "https://www.usief.org.in/"),
            ("DAAD India - Scholarships for Indian Students", "https://www.daad-india.org/"),
            ("Indian Student Statement of Purpose Examples", "https://www.gradschoolhub.com/"),
            ("Chevening India - Application Guide", "https://www.chevening.org/scholarships/india/"),
            # Pakistani student resources
            ("HEC Pakistan Overseas Scholarship Guide", "https://www.hec.gov.pk/"),
            ("Study in Germany from Pakistan", "https://www.daad-pakistan.org/"),
            ("Fulbright Pakistan - Application Process", "https://pk.usembassy.gov/education/fulbright/"),
            ("Commonwealth Scholarships for Pakistan", "https://cscuk.fcdo.gov.uk/"),
        ]

        for name, url in south_asian_urls:
            try:
                sample = {
                    "id": self._gen_id("south-asian", url),
                    "type": "document",
                    "title": name,
                    "scholar_name": "South Asian Student Resource",
                    "scholarship_name": "",
                    "university": "",
                    "program": "Graduate Program",
                    "country": "Bangladesh/India/Pakistan",
                    "field": "General",
                    "url": url,
                    "source": "South Asian Student Resource",
                    "description": f"Resource for South Asian students: {name}",
                    "key_takeaways": [
                        "Learn from students from similar background",
                        "Understand country-specific application processes",
                        "Find country-specific scholarship opportunities"
                    ],
                    "collected_at": datetime.now().isoformat(),
                }
                if self._add_sample(sample):
                    added += 1
            except Exception:
                pass

        return added

    def phase_7_professor_outreach_templates(self):
        """Collect cold email templates and outreach examples."""
        self._progress("Phase 7/7: Collecting outreach and networking templates...")
        added = 0

        urls = [
            ("Cold Email Template for PhD", "https://www.cs.unc.edu/~azuma/hitch4.html"),
            ("How to Email a Professor", "https://m.wikihow.com/Email-a-Professor"),
            ("Graduate School Email Templates", "https://www.gradschoolhub.com/email-professor-template/"),
        ]

        for name, url in urls:
            try:
                sample = {
                    "id": self._gen_id("outreach", url),
                    "type": "document",
                    "title": name,
                    "scholar_name": "Academic Resource",
                    "scholarship_name": "",
                    "university": "",
                    "program": "Graduate Program",
                    "country": "Global",
                    "field": "General",
                    "url": url,
                    "source": "Academic Resource",
                    "description": f"Guide/template for academic outreach: {name}",
                    "key_takeaways": [
                        "Learn proper academic email etiquette",
                        "Customize templates to your specific situation",
                        "Be professional and concise in outreach"
                    ],
                    "collected_at": datetime.now().isoformat(),
                }
                if self._add_sample(sample):
                    added += 1
            except Exception:
                pass

        return added

    def run(self, force=False, quick=True):
        """Run all phases of deep document research."""
        if force:
            self.new_samples = []
            self.existing_docs = []
            self.existing_urls = set()
            self.existing_ids = set()

        total_added = 0

        total_added += self.phase_1_github_discovery()

        if not quick:
            total_added += self.phase_2_semantic_scholar()
            total_added += self.phase_3_arxiv()
            total_added += self.phase_4_web_search()
            total_added += self.phase_5_university_scholarship_pages()
            total_added += self.phase_6_south_asian_documents()
            total_added += self.phase_7_professor_outreach_templates()

        if total_added > 0:
            self._save()

        self._progress(f"Deep research complete: {total_added} new documents added")
        return total_added


if __name__ == "__main__":
    researcher = DeepDocumentResearcher(progress_callback=print)
    count = researcher.run(force=True, quick=False)
    print(f"Added {count} documents")
