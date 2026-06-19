import os, json, re, time, hashlib
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.parse import quote_plus

from agents.base import BaseAgent

DOCUMENTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "scholar_documents.json"
)

CURATED_REPOS = [
    # Original repos
    "MujtabaFarrukh/Scholarship-Application-Documents",
    "amankumarpcs/Scholarship-Documents",
    "ahmed-tarek-salem/Scholarship-Application-Documents",
    "tahsin-t/Scholarship-Documents",
    "MahmoudAbdelazim/scholarship-documents",
    "Mosaab-Mohamed/Scholarship-Documents",
    "Scholarship-Application-Documents/scholarship-documents",
    "pulkitpathak99/SOP-Examples",
    "karthikbhandary2/Statement-of-Purpose",
    "kushalbose92/Statement-of-Purpose-Examples",
    "vineeths96/Statement-of-Purpose-Samples",
    "khanhnamle1994/statement-of-purpose",
    "kriml/sop",
    "jayedhossain/Statement-of-Purpose-Samples",
    "shihabmuhtorum/Statement-of-Purpose-for-MS",
    "sakibsarker/Statement-of-Purpose",
    "rabbi08/Statement-of-Purpose",
    # Bangladeshi student repos
    "rahatzamancse/Statement-of-Purpose",
    "musfiqshohan/SOP-for-MS-in-CS",
    "tanveer007/Statement-of-Purpose",
    "shakiliitju/Statement-of-Purpose-for-MS",
    "kazi-alishan/SOP-Samples",
    "shahriar100/Statement-of-Purpose",
    "fahadiislam/Statement-of-Purpose-Masters",
    "sajidhasan/SOP-Collection",
    "nayeem119/Statement-of-Purpose",
    "toufiqhasan/Statement-of-Purpose-Samples",
    # Indian student repos
    "iiti-sop/Statement-of-Purpose-IITI",
    "manasdk/Statement-of-Purpose",
    "saurabhmathur96/Statement-of-Purpose",
    "rajat503/Statement-of-Purpose",
    "peeyushsinghal/SOP_GradSchool",
    "ashwinipraveen/SOPs",
    "DhruvJawalkar/Statement-of-Purpose-Collection",
    "avikj/Statement-of-Purpose",
    "rohansingh/Statement-of-Purpose",
    "pranavmishra/Statement-of-Purpose-Graduate-School",
    "shubhankarsharma/SOP-Collection",
    "dsc-iem/SOP-Template",
    "rishavbhowmik/Statement-of-Purpose",
    "adityashrm21/Statement-of-Purpose-Samples",
    "meta-kothari/Statement-of-Purpose",
    "manastahir/SOP-for-Graduate-School",
    "rounakbanik/statement-of-purpose",
    # Pakistani student repos
    "shehriyar/Statement-of-Purpose",
    "zainshahid/Statement-of-Purpose",
    "hfazal/Statement-of-Purpose",
    "mhassanist/Statement-of-Purpose-Samples",
    "shoaibkhan/Statement-of-Purpose-Masters",
    # More global repos
    "yangshun/statement-of-purpose",
    "jonathanventura/statement-of-purpose",
    "jennyzhang/SOP",
    "davidhuang/Statement-of-Purpose",
    "azhuang/Statement-of-Purpose-Samples",
    "chriskhan/Statement-of-Purpose",
    "MSC-OS/statement-of-purpose",
    "phd-application-tools/statement-of-purpose-examples",
    "grad-school-bible/statement-of-purpose-samples",
]

FIELD_KEYWORDS = [
    "machine learning", "deep learning", "artificial intelligence",
    "data science", "statistics", "computer science", "computer vision",
    "nlp", "data engineering", "ml", "ai", "software engineering",
    "electrical engineering", "computer engineering", "robotics",
    "renewable energy", "power engineering", "bioengineering",
    "signal processing", "embedded systems", "civil engineering",
    "mechanical engineering", "chemical engineering", "material science",
    "mathematics", "physics", "biology", "chemistry", "biochemistry",
    "economics", "finance", "business", "psychology", "neuroscience",
    "environmental science", "geology", "astronomy", "astrophysics",
]

GITHUB_FOLDERS = {
    "sop": ["SOP", "Statement-of-Purpose", "sop", "Statements", "Personal-Statement",
            "Essays", "Motivation", "Motivation-Letter", "documents",
            "SOPs", "SoP", "statement_of_purpose"],
    "resume": ["CV", "Resume", "cv", "resume", "Curriculum-Vitae", "resumes"],
    "recommendation": ["Recommendation-Letters", "LOR", "lor", "Recommendations",
                       "Reference-Letters", "LoR"],
}

FILE_EXTENSIONS = (".pdf", ".md", ".txt", ".docx", ".doc", ".rtf", ".odt")


class DocumentCollector:
    def __init__(self, interactive=False):
        self.interactive = interactive
        self.existing = self._load_existing()
        self.existing_urls = {(d.get("url", "") or "").lower().strip() for d in self.existing}
        self.existing_ids = {d.get("id", "") for d in self.existing}
        self.new_samples = []
        self._check_github_token()

    def _check_github_token(self):
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            print("  [WARNING] GITHUB_TOKEN not set. GitHub API rate limit is 60 req/hr. Set GITHUB_TOKEN in .env for unlimited access.")
            print("  [HINT] Create a token at https://github.com/settings/tokens")

    def _load_existing(self):
        if os.path.exists(DOCUMENTS_FILE):
            try:
                with open(DOCUMENTS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("samples", [])
            except Exception:
                return []
        return []

    def _save(self):
        all_samples = self.existing + self.new_samples
        with open(DOCUMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"samples": all_samples}, f, indent=2, ensure_ascii=False)

    def _detect_field(self, text):
        text_lower = text.lower()
        matched = []
        for kw in FIELD_KEYWORDS:
            if kw in text_lower:
                matched.append(kw.title())
        return ", ".join(matched[:3]) if matched else "Engineering"

    def _fetch_json(self, url, headers=None):
        default_headers = {"User-Agent": "ScholarAI/1.0", "Accept": "application/json"}
        if headers:
            default_headers.update(headers)
        try:
            req = Request(url, headers=default_headers)
            with urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
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

    def _gen_id(self, prefix, url):
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"{prefix}-{url_hash}"

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

    def scrape_github_repo(self, repo_slug, doc_type, folder, folders_map):
        api_url = f"https://api.github.com/repos/{repo_slug}/contents/{folder}"
        items = self._fetch_json(api_url, headers=self._github_headers())
        if not items:
            return 0
        added = 0
        raw_base = f"https://github.com/{repo_slug}/raw/main/{folder}"
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "file" or item.get("name") in (".gitkeep", "README.md", "LICENSE", "license"):
                continue
            name = item.get("name", "")
            if not name.lower().endswith(FILE_EXTENSIONS):
                continue
            doc_url = item.get("download_url") or f"{raw_base}/{name}"
            field = self._detect_field(name)
            title = name.rsplit(".", 1)[0].replace(" - ", " \u2014 ").replace("_", " ").strip()
            sample = {
                "id": self._gen_id(f"{doc_type}-gh", doc_url),
                "type": doc_type,
                "title": title,
                "scholar_name": "Anonymous (GitHub Repository)",
                "scholarship_name": "Multiple Scholarships",
                "university": "Various Universities",
                "program": "Graduate Program",
                "country": "Global",
                "field": field,
                "url": doc_url,
                "source": f"GitHub: {repo_slug}",
                "description": f"Real {doc_type.upper()} uploaded to {repo_slug}. Contributed by a successful scholarship applicant.",
                "key_takeaways": [
                    "Learn from real successful application structures",
                    "Study formatting and content organization",
                    "Adapt the narrative style to your own background"
                ],
                "collected_at": datetime.now().isoformat(),
            }
            if self._add_sample(sample):
                added += 1
        return added

    def scrape_multiple_github_repos(self, progress_callback=None):
        total_added = 0
        for repo in CURATED_REPOS:
            if progress_callback:
                progress_callback(f"Scanning GitHub: {repo}")
            for doc_type, folders in GITHUB_FOLDERS.items():
                for folder in folders:
                    try:
                        added = self.scrape_github_repo(repo, doc_type, folder, GITHUB_FOLDERS)
                        total_added += added
                    except Exception:
                        pass
                    time.sleep(0.05)
        return total_added

    def search_semantic_scholar(self, progress_callback=None):
        """Search Semantic Scholar for open-access papers related to the user's target fields."""
        if progress_callback:
            progress_callback("Searching Semantic Scholar for relevant papers...")
        added = 0
        queries = [
            "scholarship application machine learning",
            "statement of purpose data science",
            "motivation letter artificial intelligence",
            "academic CV statistics",
            "graduate school personal statement",
        ]
        for query in queries:
            try:
                url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote_plus(query)}&limit=10&fields=title,url,openAccessPdf,year,authors"
                data = self._fetch_json(url)
                if not data or "data" not in data:
                    continue
                for paper in data["data"]:
                    title = paper.get("title", "")
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
                        "id": self._gen_id("paper-ss", pdf_url),
                        "type": "paper",
                        "title": title,
                        "scholar_name": "Research Paper (Semantic Scholar)",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "Global",
                        "field": self._detect_field(title),
                        "url": pdf_url,
                        "source": "Semantic Scholar",
                        "description": f"Academic paper related to your field: {title[:100]}",
                        "key_takeaways": [
                            "Review recent research in your target field",
                            "Cite relevant papers in your statement of purpose",
                            "Demonstrate knowledge of current research directions"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
            except Exception:
                pass
            time.sleep(1)
        return added

    def search_arxiv(self, progress_callback=None):
        """Search arXiv for recent papers in target fields."""
        if progress_callback:
            progress_callback("Searching arXiv for recent publications...")
        added = 0
        categories = ["cs.AI", "cs.LG", "stat.ML", "cs.CV", "cs.CL"]
        for cat in categories:
            try:
                url = f"http://export.arxiv.org/api/query?search_query=cat:{cat}&sortBy=submittedDate&sortOrder=descending&max_results=5"
                text = self._fetch_text(url)
                if not text:
                    continue
                import xml.etree.ElementTree as ET
                root = ET.fromstring(text)
                ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
                for entry in root.findall("atom:entry", ns):
                    title_el = entry.find("atom:title", ns)
                    title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""
                    id_el = entry.find("atom:id", ns)
                    paper_url = id_el.text.strip() if id_el is not None and id_el.text else ""
                    pdf_url = paper_url.replace("abs", "pdf") if paper_url else ""
                    if not title or not pdf_url:
                        continue
                    sample = {
                        "id": self._gen_id("paper-arxiv", pdf_url),
                        "type": "paper",
                        "title": title[:200],
                        "scholar_name": "Research Paper (arXiv)",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "Global",
                        "field": self._detect_field(title),
                        "url": pdf_url,
                        "source": "arXiv",
                        "description": f"Recent arXiv paper in {cat}: {title[:100]}",
                        "key_takeaways": [
                            "Stay updated with latest research in your field",
                            "Reference cutting-edge work in your applications",
                            "Demonstrate awareness of current research trends"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
            except Exception:
                pass
            time.sleep(0.5)
        return added

    def search_google_docs_sops(self, progress_callback=None):
        """Search the web via DuckDuckGo for publicly shared SOPs/CVs on Google Docs, Dropbox, etc."""
        if progress_callback:
            progress_callback("Searching web for shared application documents...")
        added = 0
        searches = [
            'site:docs.google.com "statement of purpose" "machine learning"',
            'site:docs.google.com "statement of purpose" "data science"',
            'site:docs.google.com "personal statement" "graduate school" cs',
            'site:dropbox.com "statement of purpose" "phd"',
            'site:medium.com "statement of purpose" "graduate school"',
        ]
        try:
            from agents.base import BaseAgent
            agent = BaseAgent("doc-finder", interactive=False)
            for search_query in searches:
                results = agent.search_web(search_query, num_results=3)
                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    if not url or url.lower().strip() in self.existing_urls:
                        continue
                    sample = {
                        "id": self._gen_id("web-doc", url),
                        "type": "sop" if "sop" in url.lower() or "statement" in title.lower() else "document",
                        "title": title[:200],
                        "scholar_name": "Web Discovery",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "Global",
                        "field": self._detect_field(title + " " + snippet),
                        "url": url,
                        "source": "Web Search",
                        "description": (snippet or f"Application document found online: {title[:100]}")[:300],
                        "key_takeaways": [
                            "Study real application examples from successful candidates",
                            "Note common patterns in strong applications"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
                time.sleep(1)
        except Exception as e:
            if progress_callback:
                progress_callback(f"Web search error: {e}")
        return added

    def run(self, progress_callback=None, force=False, quick=True):
        """Run all document collection phases."""
        if force:
            self.new_samples = []
            self.existing = []
            self.existing_urls = set()
            self.existing_ids = set()

        count = 0
        count += self.scrape_multiple_github_repos(progress_callback)

        if not quick:
            count += self.search_semantic_scholar(progress_callback)
            count += self.search_arxiv(progress_callback)
            count += self.search_google_docs_sops(progress_callback)

        if count > 0:
            self._save()

        if progress_callback:
            progress_callback(f"Document collection complete: {count} new documents added")

        return count


if __name__ == "__main__":
    collector = DocumentCollector(interactive=False)
    count = collector.run(force=True, quick=False, progress_callback=lambda msg: print(msg))
    print(f"Collected {count} new documents")
