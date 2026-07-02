import os, re, json, time, hashlib
from datetime import datetime
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from agents.base import BaseAgent

DOCUMENTS_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), '..', '..'),
    "data", "scholar_documents.json"
)

DEEP_RESEARCH_LOG = os.path.join(
    os.path.join(os.path.dirname(__file__), '..', '..'),
    "data", "deep_research_log.json"
)

FIELD_KEYWORDS = [
    "machine learning", "deep learning", "artificial intelligence",
    "data science", "statistics", "computer science", "computer vision",
    "nlp", "software engineering", "electrical engineering",
    "computer engineering", "robotics", "renewable energy",
    "power engineering", "biomedical", "signal processing",
    "civil engineering", "mechanical engineering", "material science",
    "mathematics", "physics", "chemistry", "biology", "biochemistry",
    "economics", "finance", "business", "psychology", "neuroscience",
    "environmental science", "public health", "development studies",
    "education", "law", "international relations", "climate",
    "water resources", "sustainability", "corporate sustainability",
    "public policy", "governance",
]

TYPE_KEYWORDS = {
    "sop": ["sop", "statement of purpose", "personal statement",
            "statement-of-purpose", "personal-statement"],
    "motivation_letter": ["motivation letter", "motivation-letter", "scholarship essay",
                          "cover letter", "motivational letter", "scholarship-essay",
                          "letter of motivation"],
    "study_plan": ["study plan", "study-plan", "study_plan", "academic plan", "studyplan"],
    "research_proposal": ["research proposal", "research-proposal", "research plan",
                          "research-plan", "study objective", "study-objective"],
    "resume": ["cv", "resume", "curriculum vitae", "curriculum-vitae"],
    "recommendation": ["lor", "recommendation", "reference letter",
                       "letter of recommendation", "recommendation-letter"],
    "certificate": ["certificate", "volunteer", "achievement", "award",
                    "participation", "extra-curricular", "co-curricular"],
}


class DeepDocumentResearcher:
    """
    Cross-platform researcher that finds real scholarship application documents
    shared by South Asian winners on Reddit, LinkedIn, Medium, Facebook, blogs,
    and personal websites.
    
    NO generic GitHub scanning. ONLY targeted searches for verified winners.
    """

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
        default_headers = {"User-Agent": "ScholarAI/2.0", "Accept": "application/json"}
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
            req = Request(url, headers={"User-Agent": "ScholarAI/2.0"})
            with urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None

    # ==================================================================
    # PHASE 1: Reddit – search scholarship subreddits for document posts
    # ==================================================================
    def phase_1_reddit_search(self):
        self._progress("Phase 1/7: Searching Reddit for shared scholarship documents...")
        added = 0

        subreddits = [
            "DAAD", "fulbright", "chevening", "Erasmus",
            "gradadmissions", "scholarships", "StatementOfPurpose",
            "Indians_StudyAbroad", "masters_germany", "studying_in_germany",
            "PakistaniTech", "studyAbroad",
        ]

        queries = []
        for sub in subreddits:
            queries.append(f'site:reddit.com/r/{sub} "SOP" OR "statement of purpose" scholarship')
            queries.append(f'site:reddit.com/r/{sub} "motivation letter"')
        queries.append('site:reddit.com "DAAD" "Bangladesh" "scholarship"')
        queries.append('site:reddit.com "Fulbright" "Pakistan" "personal statement"')
        queries.append('site:reddit.com "Chevening" "India" "essay"')
        queries.append('site:reddit.com "Erasmus Mundus" "Bangladesh" "motivation"')
        queries.append('site:reddit.com "Commonwealth" "Pakistan" "scholarship"')
        queries.append('site:reddit.com "GKS" "Bangladesh" "study plan"')
        queries.append('site:reddit.com "MEXT" "Bangladesh" "research"')

        try:
            agent = BaseAgent("deep-reddit", interactive=False)
            for query in queries:
                results = agent.search_web(query, num_results=5)
                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    if not url or url.lower().strip() in self.existing_urls:
                        continue
                    doc_type = self._detect_type(title, title)
                    field = self._detect_field(title + " " + (snippet or ""))
                    sample = {
                        "id": self._gen_id("reddit", url),
                        "type": doc_type,
                        "title": title[:200],
                        "scholar_name": "Reddit User (South Asia)",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "South Asia",
                        "field": field,
                        "url": url,
                        "source": "Reddit",
                        "description": (snippet or f"Scholarship document shared on Reddit: {title[:100]}")[:300],
                        "key_takeaways": [
                            "Real document shared by a scholarship applicant on Reddit",
                            "See what real applicants post for feedback",
                            "Understand common structures and approaches"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
                time.sleep(1)
        except Exception as e:
            self._progress(f"  Reddit search error: {e}")

        self.research_log["reddit_found"] = added
        return added

    # ==================================================================
    # PHASE 2: LinkedIn – search for scholar posts and articles
    # ==================================================================
    def phase_2_linkedin_search(self):
        self._progress("Phase 2/7: Searching LinkedIn for scholar-shared documents...")
        added = 0

        queries = [
            'site:linkedin.com/pulse "Fulbright" "scholarship" "essay"',
            'site:linkedin.com/pulse "Chevening" "scholarship" "application"',
            'site:linkedin.com/pulse "DAAD" "scholarship" "experience"',
            'site:linkedin.com/pulse "Commonwealth" "scholarship" "guide"',
            'site:linkedin.com "Fulbright" "Pakistan" "scholar" "personal statement"',
            'site:linkedin.com "Chevening" "India" "scholar" "essay"',
            'site:linkedin.com "DAAD" "Bangladesh" "scholar"',
            'site:linkedin.com "Erasmus Mundus" "Bangladesh" "alumni"',
            'site:linkedin.com "Fulbright" "Nepal" "scholar"',
            '"Fulbright scholar" "Pakistan" LinkedIn',
            '"Chevening scholar" "India" LinkedIn essay',
        ]

        try:
            agent = BaseAgent("deep-linkedin", interactive=False)
            for query in queries:
                results = agent.search_web(query, num_results=5)
                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    if not url or url.lower().strip() in self.existing_urls:
                        continue
                    doc_type = self._detect_type(title, title)
                    field = self._detect_field(title + " " + (snippet or ""))
                    sample = {
                        "id": self._gen_id("linkedin", url),
                        "type": doc_type,
                        "title": title[:200],
                        "scholar_name": "LinkedIn Scholar (South Asia)",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "South Asia",
                        "field": field,
                        "url": url,
                        "source": "LinkedIn",
                        "description": (snippet or f"Scholarship document shared on LinkedIn: {title[:100]}")[:300],
                        "key_takeaways": [
                            "Learn from scholars who share their journey on LinkedIn",
                            "Understand how professionals present their scholarship journey",
                            "Network with successful scholars from your region"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
                time.sleep(1)
        except Exception as e:
            self._progress(f"  LinkedIn search error: {e}")

        self.research_log["linkedin_found"] = added
        return added

    # ==================================================================
    # PHASE 3: Medium – search for scholarship winner stories
    # ==================================================================
    def phase_3_medium_search(self):
        self._progress("Phase 3/7: Searching Medium for scholarship winner stories...")
        added = 0

        queries = [
            'site:medium.com "Erasmus Mundus" "Bangladesh" "motivation letter"',
            'site:medium.com "Fulbright" "Pakistan" "personal statement"',
            'site:medium.com "DAAD" "India" "motivation letter"',
            'site:medium.com "Chevening" "Bangladesh" "essay"',
            'site:medium.com "Commonwealth" "Pakistan" "scholarship"',
            'site:medium.com "GKS" "Bangladesh" "study plan"',
            'site:medium.com "how I won" "Fulbright" "scholarship"',
            'site:medium.com "how I got" "DAAD" "scholarship" Bangladesh',
            'site:medium.com "my journey" "Chevening" India',
            'site:medium.com "SOP" "scholarship" Bangladesh',
            'site:medium.com "study in Germany" "Bangladesh" "SOP"',
            'site:medium.com "Fulbright" "Nepal" "experience"',
            '"Erasmus Mundus" "Bangladeshi" "SOP" site:medium.com',
            '"DAAD" "Bangladeshi" "motivation letter" site:medium.com',
            '"Fulbright" "Indian" "personal statement" site:medium.com',
        ]

        try:
            agent = BaseAgent("deep-medium", interactive=False)
            for query in queries:
                results = agent.search_web(query, num_results=5)
                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    if not url or url.lower().strip() in self.existing_urls:
                        continue
                    doc_type = self._detect_type(title, title)
                    field = self._detect_field(title + " " + (snippet or ""))
                    sample = {
                        "id": self._gen_id("medium", url),
                        "type": doc_type,
                        "title": title[:200],
                        "scholar_name": "Medium Author (South Asia)",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "South Asia",
                        "field": field,
                        "url": url,
                        "source": "Medium",
                        "description": (snippet or f"Scholarship winner story on Medium: {title[:100]}")[:300],
                        "key_takeaways": [
                            "Real scholarship winner's personal story and document approach",
                            "Learn from detailed walkthroughs of successful applications",
                            "Understand region-specific strategies and tips"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
                time.sleep(1)
        except Exception as e:
            self._progress(f"  Medium search error: {e}")

        self.research_log["medium_found"] = added
        return added

    # ==================================================================
    # PHASE 4: Facebook public groups
    # ==================================================================
    def phase_4_facebook_search(self):
        self._progress("Phase 4/7: Searching Facebook for scholarship group posts...")
        added = 0

        queries = [
            'site:facebook.com "DAAD" "Bangladesh" "scholarship" "motivation letter"',
            'site:facebook.com "Fulbright" "Pakistan" "program" "essay"',
            'site:facebook.com "Erasmus Mundus" "Bangladesh" "SOP"',
            'site:facebook.com "Chevening" "India" "scholarship" "tips"',
            'site:facebook.com "Commonwealth" "Pakistan" "scholarship" "essay"',
            'site:facebook.com "GKS" "Bangladesh" "study plan"',
            'site:facebook.com "MEXT" "Bangladesh" "research"',
            'site:facebook.com/notes "scholarship" "Bangladesh" "SOP"',
            'site:facebook.com/notes "Fulbright" "Pakistan"',
        ]

        try:
            agent = BaseAgent("deep-facebook", interactive=False)
            for query in queries:
                results = agent.search_web(query, num_results=5)
                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    if not url or url.lower().strip() in self.existing_urls:
                        continue
                    doc_type = self._detect_type(title, title)
                    field = self._detect_field(title + " " + (snippet or ""))
                    sample = {
                        "id": self._gen_id("facebook", url),
                        "type": doc_type,
                        "title": title[:200],
                        "scholar_name": "Facebook Group Member (South Asia)",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "South Asia",
                        "field": field,
                        "url": url,
                        "source": "Facebook",
                        "description": (snippet or f"Scholarship post from Facebook group: {title[:100]}")[:300],
                        "key_takeaways": [
                            "Scholarship information shared in Facebook community groups",
                            "Tips and guidance from peers in your region"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
                time.sleep(1)
        except Exception as e:
            self._progress(f"  Facebook search error: {e}")

        self.research_log["facebook_found"] = added
        return added

    # ==================================================================
    # PHASE 5: Personal blogs and Blogspot
    # ==================================================================
    def phase_5_blog_search(self):
        self._progress("Phase 5/7: Searching personal blogs for shared documents...")
        added = 0

        queries = [
            'site:blogspot.com "scholarship" "Bangladesh" "SOP" "DAAD"',
            'site:blogspot.com "Fulbright" "India" "personal statement"',
            'site:blogspot.com "study in Germany" "Pakistan" "SOP"',
            'site:blogspot.com "Erasmus" "Bangladesh" "motivation letter"',
            'site:blogspot.com "Chevening" "Pakistan" "essay"',
            'site:wordpress.com "scholarship" "Bangladesh" "essay"',
            'site:wordpress.com "Fulbright" "India" "SOP"',
            'site:wixsite.com "scholarship" "Bangladesh" "application"',
            'site:netlify.app "scholarship" "Bangladesh" "SOP"',
            'site:github.io "scholarship" "SOP" Bangladesh',
            '"scholarship" "Bangladesh" "SOP" "blog"',
            '"Fulbright" "Pakistan" "essay" "blogspot"',
        ]

        try:
            agent = BaseAgent("deep-blogs", interactive=False)
            for query in queries:
                results = agent.search_web(query, num_results=5)
                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    if not url or url.lower().strip() in self.existing_urls:
                        continue
                    doc_type = self._detect_type(title, title)
                    field = self._detect_field(title + " " + (snippet or ""))
                    sample = {
                        "id": self._gen_id("blog", url),
                        "type": doc_type,
                        "title": title[:200],
                        "scholar_name": "Blog Author (South Asia)",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "South Asia",
                        "field": field,
                        "url": url,
                        "source": "Personal Blog",
                        "description": (snippet or f"Scholarship document shared on personal blog: {title[:100]}")[:300],
                        "key_takeaways": [
                            "Personal scholarship journey with detailed document insights",
                            "Learn from individual experiences and approaches"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
                time.sleep(1)
        except Exception as e:
            self._progress(f"  Blog search error: {e}")

        self.research_log["blogs_found"] = added
        return added

    # ==================================================================
    # PHASE 6: Google Drive / Docs – public links
    # ==================================================================
    def phase_6_google_drive_search(self):
        self._progress("Phase 6/7: Searching Google Drive/docs for shared documents...")
        added = 0

        queries = [
            'site:docs.google.com "DAAD" "motivation letter"',
            'site:docs.google.com "Fulbright" "personal statement"',
            'site:docs.google.com "Chevening" "essay"',
            'site:docs.google.com "study plan" "scholarship"',
            'site:docs.google.com "SOP" "Bangladesh"',
            'site:docs.google.com "research proposal" "scholarship"',
            'site:drive.google.com "DAAD" "scholarship" documents',
            'site:docs.google.com/document "scholarship" "SOP"',
            'inurl:docs.google.com "statement of purpose" Bangladesh',
        ]

        try:
            agent = BaseAgent("deep-gdrive", interactive=False)
            for query in queries:
                results = agent.search_web(query, num_results=5)
                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    if not url or url.lower().strip() in self.existing_urls:
                        continue
                    doc_type = self._detect_type(title, title)
                    field = self._detect_field(title + " " + (snippet or ""))
                    sample = {
                        "id": self._gen_id("gdrive", url),
                        "type": doc_type,
                        "title": title[:200],
                        "scholar_name": "Google Drive (Public Share)",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "South Asia",
                        "field": field,
                        "url": url,
                        "source": "Google Drive",
                        "description": (snippet or f"Scholarship document shared on Google Drive: {title[:100]}")[:300],
                        "key_takeaways": [
                            "Real document shared publicly by a scholarship applicant",
                            "Direct access to actual application documents"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
                time.sleep(1)
        except Exception as e:
            self._progress(f"  Google Drive search error: {e}")

        self.research_log["gdrive_found"] = added
        return added

    # ==================================================================
    # PHASE 7: University / scholarship alumni pages
    # ==================================================================
    def phase_7_university_alumni_pages(self):
        self._progress("Phase 7/7: Searching university alumni success pages...")
        added = 0

        queries = [
            '"Fulbright" "alumni" "Bangladesh" "success story"',
            '"DAAD" "alumni" "Bangladesh" "experience"',
            '"Chevening" "alumni" "India" "story"',
            '"Erasmus Mundus" "alumni" "Bangladesh" "interview"',
            '"Commonwealth" "alumni" "Pakistan" "journey"',
            '"Fulbright" "Nepal" "alumni" "story"',
            '"Fulbright" "India" "success story" university',
            '"DAAD" "Pakistan" "alumni" "experience"',
            '"BUET" "Fulbright" "scholar"',
            '"IIT" "Fulbright" "scholar" "essay"',
            '"NUST" "Fulbright" "scholar" Pakistan',
            '"scholarship" "Bangladesh" "alumni" "SOP" "tips"',
        ]

        try:
            agent = BaseAgent("deep-alumni", interactive=False)
            for query in queries:
                results = agent.search_web(query, num_results=5)
                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    if not url or url.lower().strip() in self.existing_urls:
                        continue
                    doc_type = self._detect_type(title, title)
                    field = self._detect_field(title + " " + (snippet or ""))
                    sample = {
                        "id": self._gen_id("alumni", url),
                        "type": doc_type,
                        "title": title[:200],
                        "scholar_name": "Scholarship Alumni (South Asia)",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "South Asia",
                        "field": field,
                        "url": url,
                        "source": "University/Alumni Page",
                        "description": (snippet or f"Scholarship alumni success story: {title[:100]}")[:300],
                        "key_takeaways": [
                            "Real scholarship winner profile from university alumni pages",
                            "Understand what successful candidates looked like"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
                time.sleep(1)
        except Exception as e:
            self._progress(f"  Alumni search error: {e}")

        self.research_log["alumni_found"] = added
        return added

    # ==================================================================
    # RUN ALL PHASES
    # ==================================================================
    def run(self, force=False, quick=True):
        if force:
            self.new_samples = []
            self.existing_docs = []
            self.existing_urls = set()
            self.existing_ids = set()

        total_added = 0

        total_added += self.phase_1_reddit_search()

        if not quick:
            total_added += self.phase_2_linkedin_search()
            total_added += self.phase_3_medium_search()
            total_added += self.phase_4_facebook_search()
            total_added += self.phase_5_blog_search()
            total_added += self.phase_6_google_drive_search()
            total_added += self.phase_7_university_alumni_pages()

        if total_added > 0:
            self._save()

        self._progress(f"Deep research complete: {total_added} new documents added from Reddit/LinkedIn/Medium/Facebook/Blogs/GDrive")
        return total_added


if __name__ == "__main__":
    researcher = DeepDocumentResearcher(progress_callback=print)
    count = researcher.run(force=True, quick=False)
    print(f"Added {count} documents from cross-platform search")
