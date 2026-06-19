import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.core.base import BaseAgent, logger
from app.core.config import settings
from app.core.database import async_session, db_write_lock
from app.core.models import ResearchLead, ScrapeSession, UserProfile
from app.discovery.search_client import SearchClient
from app.llm.client import llm
from app.llm.parser import parse_llm_json
from app.llm.prompts import RESEARCH_EXTRACT, RESEARCH_FIT_PROMPT, RESEARCH_OUTREACH


# ─────────────────────────────────────────────────────────────────────
# URL VALIDATION — STRICT PERSONAL-PROFILE WHITELIST
# Only accept URLs whose path uniquely identifies ONE researcher's profile.
# Drops all generic .edu/.ac.* — those were the source of all the fakes.
# ─────────────────────────────────────────────────────────────────────
def _is_valid_research_url(url: str) -> tuple[bool, str]:
    """Return (ok, reason). Strict whitelist with per-host path rules."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "unparseable"
    host = (parsed.netloc or "").lower().replace("www.", "")
    path = (parsed.path or "").lower()
    if not host:
        return False, "no host"

    # arXiv — /a/<name> or /auth/<name> author pages  OR  /abs/<id> paper pages
    if host == "arxiv.org":
        if re.search(r"^/(a|auth)/[A-Za-z0-9._\-]+/?$", path):
            return True, "arxiv_author"
        if re.search(r"^/abs/\d{4}\.\d+", path):
            return True, "arxiv_paper"
        return False, "arxiv: not /a/<name> or /abs/<id>"

    # ResearchGate — only /profile/ pages
    if host == "researchgate.net":
        if re.search(r"^/profile/[A-Za-z0-9._\-]+/?$", path):
            return True, "researchgate_profile"
        return False, "researchgate: not /profile/<name>"

    # Academia.edu — /people/<name> (single-name slug)
    if host == "academia.edu":
        if re.search(r"^/people/[A-Za-z0-9._\-]+/?$", path):
            return True, "academia_profile"
        return False, "academia: not /people/<name>"

    # ORCID — only the numeric 0000-0000-0000-0000 path
    if host == "orcid.org":
        if re.search(r"^/\d{4}-\d{4}-\d{4}-\d{3}[\dX]/?$", path):
            return True, "orcid"
        return False, "orcid: not a numeric profile path"

    # Google Scholar — /citations?user=<id>
    if host == "scholar.google.com":
        if "/citations" in path:
            return True, "scholar"
        return False, "scholar: not /citations"

    # Semantic Scholar — /author/<id>  or  /author/<name>/<id>
    if host == "semanticscholar.org":
        if re.search(r"^/author/\d+", path) or re.search(r"^/author/[A-Za-z0-9._\-]+/\d+", path):
            return True, "semantic_scholar"
        return False, "semantic_scholar: not /author/<id>"

    # DBLP — /pid/<initial>/<name>  or  /pid/<digits>/<digits>
    if host == "dblp.org":
        if re.search(r"^/pid/[A-Za-z]+/[A-Za-z0-9._\-]+/?$", path) \
                or re.search(r"^/pid/\d+/\d+", path):
            return True, "dblp"
        return False, "dblp: not /pid/<slug>"

    # IEEE — author profile
    if host == "ieee.org":
        if re.search(r"^/author/\d+", path) or re.search(r"^/researcher/", path):
            return True, "ieee"
        return False, "ieee: not an author page"

    # ACM — author profile or DOI paper
    if host in ("acm.org", "dl.acm.org"):
        if re.search(r"^/profile/\d+", path) or re.search(r"^/authors/\d+", path):
            return True, "acm"
        return False, "acm: not an author page"

    # LinkedIn — ONLY /in/<slug> (person profile).
    # Reject /company/, /posts/, /pulse/, /jobs/, /groups/, /school/, /showcase/
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        if re.search(r"^/in/[A-Za-z0-9\-]+/?$", path):
            return True, "linkedin_in"
        return False, "linkedin: not /in/<slug>"

    # Frontiers / Publons / Scopus
    if host == "loop.frontiersin.org":
        if re.search(r"^/people/\d+", path):
            return True, "frontiers"
        return False, "frontiers: not /people/<id>"
    if host == "publons.com":
        if re.search(r"^/researcher/\d+", path):
            return True, "publons"
        return False, "publons: not /researcher/<id>"
    if "scopus.com" in host:
        if re.search(r"^/authid/detail\.uri", path) or "/authid/" in path:
            return True, "scopus"
        return False, "scopus: not /authid/"

    # Reddit — user profiles AND post/comments pages
    if host in ("reddit.com", "www.reddit.com", "old.reddit.com"):
        if re.search(r"^/(user|u)/[A-Za-z0-9_.\-]+/?$", path):
            return True, "reddit_user"
        if re.search(r"^/r/[A-Za-z0-9_]+/comments/[A-Za-z0-9]+", path):
            return True, "reddit_post"
        return False, "reddit: not /user/<name> or /r/.../comments/..."

    # Academic institution personal pages — only accept profile-like paths
    if host.endswith(".ac.bd") or host.endswith(".ac.in") or host.endswith(".ac.uk") \
            or host.endswith(".ac.nz") or host.endswith(".ac.jp") \
            or host.endswith(".edu") or host.endswith(".edu.au") \
            or host.endswith(".edu.cn") or host.endswith(".edu.pk"):
        if re.search(r"^/~[A-Za-z]", path) \
                or re.search(r"^/(people|faculty|staff|profile|directory|researcher|member|user|author)/[A-Za-z]", path):
            return True, "academic_profile"
        return False, "academic: not a personal profile path"

    return False, f"host not in whitelist ({host})"


# Generic terms / phrases that should NEVER be stored as a researcher's name
NON_PERSON_NAME_PHRASES = {
    # Page / section titles
    "home page", "homepage", "about us", "about me", "contact us", "contact me",
    "current faculty", "former faculty", "faculty members", "faculty members details",
    "faculty list", "faculty directory", "faculty page", "faculty staff",
    "research staff", "research student", "research students", "research scholars",
    "research areas", "research group", "research team", "research interests",
    "research output", "research projects", "research profile", "research overview",
    "office staff", "office of", "our team", "our services", "our research",
    "our faculty", "our people", "our staff", "our mission", "our story",
    "our work", "publication list", "publications list", "recent publications",
    "selected publications", "all publications", "all papers", "all notices",
    "department of", "school of", "faculty of", "college of", "institute of",
    "centre for", "center for", "laboratory of", "lab members", "lab alumni",
    "graduate students", "graduate school", "postdoctoral researchers", "postdocs",
    "people directory", "people page", "people list", "directory page",
    "thesis archive", "thesis title", "thesis student", "thesis supervision",
    "education background", "work experience", "academic background",
    "find statistics", "find people", "find expert", "search results",
    "sign in", "log in", "sign up", "create account", "forgot password",
    "privacy policy", "terms of service", "terms of use", "cookie policy",
    "design studio", "web design", "graphic design", "our design",
    "machine learning approaches", "machine learning models", "machine learning algorithms",
    "exploratory data analysis", "classification models", "regression models",
    "clustering algorithms", "one hot encoding", "one-hot encoding",
    "comprehensive guide", "getting started", "complete guide", "step by step",
    "tutorial", "tutorials list", "blog post", "blog posts", "latest news",
    "read more", "learn more", "view all", "view profile", "view project",
    "see all", "show all", "load more", "next page", "previous page",
    "404", "404 not found", "page not found", "not found", "access denied",
    "home", "main", "index", "welcome", "hello world",
    "statistical research consultants", "statistical research consultants bangladesh",
    "consulting services", "consultancy services", "our consultants",
}

GENERIC_NAME_TERMS = {
    "home", "login", "sign", "signup", "search", "explore", "about",
    "contact", "help", "privacy", "terms", "404", "error",
    "research", "publications", "profile", "people", "faculty",
    "staff", "department", "news", "events", "blog", "post",
    "article", "feed", "index", "main", "page", "view", "all",
    "current", "former", "office", "thesis", "list", "directory",
    "services", "team", "members", "design", "studio",
    "comprehensive", "guide", "getting", "started", "machine",
    "learning", "approaches", "models", "algorithms", "data",
    "analysis", "classification", "regression", "clustering",
    "encoding", "tutorial", "blog", "latest", "consulting",
    "consultants", "consultant", "title", "notice", "notices",
    "find", "tutors", "tutor",
}


# Person-signal scoring — must reach threshold before we accept
PERSON_SIGNAL_KEYWORDS = (
    # email shape: name@<academic-domain>
    "name@",  # placeholder; real check is regex
)

PERSON_SIGNAL_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.(?:edu|ac\.[a-z]{2,}|research\.[a-z]{2,})\b", re.I),
    re.compile(r"\borcid\.org/\d{4}-\d{4}-\d{4}-\d{3}[\dX]", re.I),
    re.compile(r"\bresearchgate\.net/profile/", re.I),
    re.compile(r"\bscholar\.google\.com/citations", re.I),
    re.compile(r"\bsemanticscholar\.org/author/", re.I),
    re.compile(r"\barxiv\.org/abs/", re.I),
    re.compile(r"\bdblp\.org/pid/", re.I),
]

# Generic email domains that DON'T count as institutional contact
GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.in", "hotmail.com", "outlook.com",
    "live.com", "icloud.com", "aol.com", "protonmail.com", "proton.me",
    "gmx.com", "mail.com", "zoho.com", "yandex.com", "qq.com", "163.com",
    "rediffmail.com", "yahoo.co.uk", "ymail.com", "rocketmail.com",
    "duck.com", "pm.me", "fastmail.com", "tutanota.com",
}


def _count_person_signals(html: str, text: str) -> tuple[int, list[str]]:
    """Count real-person signals in the page. Higher score = more likely a person."""
    found: list[str] = []
    n = 0
    for pat in PERSON_SIGNAL_PATTERNS:
        m = pat.search(html)
        if m:
            n += 1
            found.append(m.group(0))
    # Institutional email (separate from patterns)
    for m in re.finditer(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", html):
        dom = m.group(0).split("@", 1)[1].lower()
        if dom not in GENERIC_EMAIL_DOMAINS:
            n += 1
            found.append(m.group(0))
            break
    # Bio first-person pronouns
    if re.search(r"\b(I am|I'm|my research|my work|My name is|PhD student|M\.?Sc|MSc student|PhD candidate)\b", text, re.I):
        n += 1
        found.append("bio-first-person")
    # Paper-shape "Title." + year pattern
    if re.search(r"\b20\d{2}\b", text) and re.search(r"\b(journal|conference|proceedings|published|preprint)\b", text, re.I):
        n += 1
        found.append("publication-words")
    return n, found


_search_client = SearchClient()


SCRAPE_CATEGORIES = [
    "bd_faculty", "bd_students",
    "global_ml_research", "global_students",
    "reddit", "global_open_projects",
]


class ResearchDiscoveryAgent(BaseAgent):
    """Discover real researchers via profile-domain whitelisted scraping.

    Strict mode (default):
    - Only fetches URLs whose host+path pass `_is_valid_research_url`
    - For each page, requires >=2 person signals (institutional email,
      ORCID, /profile/, /citations/, /author/, /pid/, arXiv, first-person bio, publication)
    - Name must pass `_is_real_name` (rejects section titles, "Current Faculty", etc.)
    - Queries are run SEQUENTIALLY (one session per query) to avoid SQLite
      "database is locked" caused by parallel writes through one shared session.
    URL fetches within a single query are still parallel.
    """

    # require at least this many person signals to accept a page
    MIN_PERSON_SIGNALS = 2

    async def run(self, custom_query: str | None = None, bd_only: bool = False):
        queries = self._load_queries(custom_query, bd_only=bd_only)
        if not queries:
            return
        await self._process_queries(queries, "research_discovery_bd" if bd_only else "research_discovery")

    def _load_queries(self, custom_query: str | None = None, bd_only: bool = False) -> list[str]:
        path = Path(__file__).parent / "queries.yml"
        if not path.exists():
            return []
        with open(path) as f:
            data = yaml.safe_load(f)
        cats = data.get("categories", {})
        if custom_query:
            return [custom_query]
        if bd_only:
            return [q for cat in ("bd_faculty", "bd_students") for q in cats.get(cat, [])]
        return [q for cat_list in cats.values() for q in cat_list]

    async def _process_queries(self, queries: list[str], source_tag: str):
        if not queries:
            return
        total = len(queries)
        for idx, query in enumerate(queries, 1):
            logger.info(f"  [research] Search [{idx}/{total}]: {query}")
            try:
                await self._run_query(query, source_tag)
            except Exception as e:
                logger.error(f"  [research] Query failed ({query[:60]}): {e}")

    async def _run_query(self, query: str, source_tag: str):
        """Run ONE query, sequentially (no shared session)."""
        urls = await _search_client.search(
            query, settings.max_search_results, "",
        )
        if not urls:
            logger.info(f"  [research] 0 URLs for: {query[:50]}")
            return

        # Filter URLs through strict whitelist FIRST — no point fetching junk
        accepted_urls: list[str] = []
        for u in urls:
            ok, reason = _is_valid_research_url(u)
            if ok:
                accepted_urls.append(u)
            else:
                logger.debug(f"  [research]   reject URL ({reason}): {u[:80]}")
        if not accepted_urls:
            logger.info(f"  [research] 0 whitelisted URLs for: {query[:50]}")
            return

        # Fetch pages in parallel (httpx, no DB writes) — bounded semaphore
        sem = asyncio.Semaphore(6)
        async def _fetch(u: str) -> tuple[str, str | None]:
            async with sem:
                return u, await self._fetch_page(u)
        fetch_results = await asyncio.gather(*[_fetch(u) for u in accepted_urls])
        fetched = [(u, html) for u, html in fetch_results if html]
        failed = [u for u, html in fetch_results if not html]
        if failed:
            logger.debug(f"  [research]   {len(failed)} page(s) failed, trying fallbacks")

        # For URLs whose pages failed (captcha / rate-limit / JS shell), call
        # the platform-specific API / URL-slug fallback directly.
        fallback_infos: dict[str, dict] = {}
        for url in failed:
            try:
                info = await self._fallback_extract_from_url(url, query)
            except Exception as e:
                logger.debug(f"  [research]   fallback failed for {url[:80]}: {e}")
                continue
            if info and self._is_real_name(info.get("name", "")):
                fallback_infos[url] = info

        # Process each fetched page with a FRESH session (so writes don't conflict)
        accepted = 0
        for url, html in fetched:
            try:
                info = await self._extract_researcher(html, url, query)
            except Exception as e:
                logger.debug(f"  [research]   extract failed for {url[:80]}: {e}")
                continue
            if not info:
                continue
            if not info.get("is_researcher"):
                logger.debug(f"  [research]   not a real researcher: {url[:80]}")
                continue
            name = info.get("name", "").strip()
            if not self._is_real_name(name):
                logger.debug(f"  [research]   bad name '{name[:40]}': {url[:80]}")
                continue
            async with db_write_lock:
                async with async_session() as session:
                    await self._store_researcher(session, info, query, url)
                    await session.commit()
            accepted += 1
            logger.info(
                f"  [research]   + {name} ({info.get('institution', '?')[:30]}) "
                f"score={info.get('_score', '?')}"
            )

        # Now persist the fallback-extracted leads
        for url, info in fallback_infos.items():
            async with db_write_lock:
                async with async_session() as session:
                    await self._store_researcher(session, info, query, url)
                    await session.commit()
            accepted += 1
            logger.info(
                f"  [research]   + {info['name']} ({info.get('institution', '?')[:30]}) "
                f"[from fallback] score={info.get('_score', '?')}"
            )

        async with db_write_lock:
            async with async_session() as session:
                session.add(ScrapeSession(
                    source=source_tag,
                    query=query,
                    urls_found=len(urls),
                    jobs_found=0,
                    prospects_found=accepted,
                    status="completed",
                ))
                await session.commit()
        logger.info(f"  [research] {accepted} real researcher(s) from: {query[:50]}")

    async def _fetch_page(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ResearchDiscovery/1.0)",
                    "Accept": "text/html,application/xhtml+xml",
                })
                if resp.status_code == 200 and "text/html" in (resp.headers.get("content-type", "").lower()):
                    return resp.text[:200_000]
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
        return None

    # ──────────────────────────────────────────────────────────────────
    # Name validation — ULTRA STRICT
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _is_real_name(name: str) -> bool:
        if not name:
            return False
        cleaned = name.strip()
        if len(cleaned) < 6 or len(cleaned) > 80:
            return False
        # Reject if any punctuation that's unusual for a personal name
        if any(c in cleaned for c in (",", ";", ":", "/", "(", ")", "—", "–", "•", "·")):
            return False
        # Reject ALL-CAPS
        if cleaned == cleaned.upper() and any(c.isalpha() for c in cleaned):
            return False
        # Title case check
        lower = cleaned.lower()
        if lower in GENERIC_NAME_TERMS or lower in NON_PERSON_NAME_PHRASES:
            return False
        for phrase in NON_PERSON_NAME_PHRASES:
            if phrase in lower:
                return False
        # Stopwords / organization words that should NEVER appear in a personal name
        STOPWORDS_IN_NAME = {
            "of", "the", "and", "in", "for", "at", "on", "by", "with", "to", "from",
            "university", "college", "department", "faculty", "institute", "school",
            "centre", "center", "lab", "laboratory", "research", "group", "team",
            "office", "staff", "member", "members", "people", "society", "association",
            "foundation", "bureau", "inc", "llc", "ltd", "corp", "co", "company",
            "international", "global", "national", "bangladesh", "pakistan", "india",
            "americans", "asian", "european", "african",
            "advisor", "advisors", "admission", "admissions", "tutor", "tutors",
            "booking", "facility", "facilities", "service", "services",
            "design", "studio", "blog", "post", "article", "tutorial",
            "guide", "guides", "approach", "approaches", "model", "models",
            "algorithm", "algorithms", "analysis", "classification", "regression",
            "clustering", "encoding", "consulting", "consultants", "consultant",
            "machine", "learning", "data", "science", "sciences", "statistical",
            "statistics", "programming", "engineering", "technology", "management",
            "current", "former", "all", "every", "view", "list", "directory",
            "thesis", "notices", "notice", "title", "home", "about", "contact",
            "search", "results", "login", "signin", "signup",
            "student", "students", "scholar", "scholars", "fellow", "fellows",
            "publications", "publication", "papers", "projects", "project",
            "comprehensive", "complete", "started", "getting", "step", "guide-to",
            "find", "wanted", "looking", "needed", "seeking", "volunteer",
            "free", "remote", "beginner", "open", "honest",
            "banani", "dhanmondi", "mirpur", "uttara", "gulshan", "mohammadpur",
        }
        words = cleaned.split()
        if len(words) < 2 or len(words) > 5:
            return False
        for w in words:
            wl = w.lower()
            if wl in STOPWORDS_IN_NAME:
                return False
            if wl in GENERIC_NAME_TERMS:
                return False
            # Allow a normal capitalized word (John, Md), a single-letter
            # initial (A.), or an abbreviation with a trailing period (Md.).
            if not re.match(r"^([A-Z][a-zA-Z'\-]+\.?|[A-Z]\.?)$", w):
                return False
            if len(w) < 1 or len(w) > 30:
                return False
            # Reject multi-letter ALL-CAPS words (e.g. "UNIVERSITY") but allow
            # "A." / "Md." since the trailing period makes them "ALL CAPS".
            alpha = w.rstrip(".")
            if len(alpha) > 1 and alpha.isupper():
                return False
        return True

    @staticmethod
    def _guess_country_from_text(text: str) -> str:
        text_lower = text.lower()
        country_map = {
            "bangladesh": "Bangladesh", "dhaka": "Bangladesh",
            "india": "India", "delhi": "India", "mumbai": "India",
            "pakistan": "Pakistan", "karachi": "Pakistan",
            "usa": "USA", "united states": "USA", "new york": "USA",
            "uk": "UK", "united kingdom": "UK", "london": "UK",
            "germany": "Germany", "berlin": "Germany",
            "france": "France", "paris": "France",
            "canada": "Canada", "toronto": "Canada",
            "australia": "Australia", "sydney": "Australia",
            "japan": "Japan", "tokyo": "Japan",
            "china": "China", "beijing": "China",
            "singapore": "Singapore",
            "netherlands": "Netherlands",
        }
        for keyword, country in country_map.items():
            if keyword in text_lower:
                return country
        return ""

    @staticmethod
    def _classify_region(country: str, url: str) -> str:
        if country.lower() == "bangladesh":
            return "bangladesh"
        url_lower = url.lower()
        if "bangladesh" in url_lower or ".bd" in url_lower or "dhaka" in url_lower:
            return "bangladesh"
        south_asia = {"india", "pakistan", "sri lanka", "nepal", "bhutan", "maldives"}
        if country.lower() in south_asia:
            return "south_asia"
        return "global"

    # ──────────────────────────────────────────────────────────────────
    # Extraction — LLM with HARD person-signal requirement
    # ──────────────────────────────────────────────────────────────────
    async def _extract_researcher(self, content: str, url: str, query: str) -> dict | None:
        # ORCID: page is JS-only, hit the public API instead.
        if "orcid.org/" in url and re.search(r"/\d{4}-\d{4}-\d{4}-\d{3}[\dX]", url):
            return await self._extract_orcid(url, query)

        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        if len(text) < 60:
            return None

        domain = urlparse(url).netloc.replace("www.", "")

        # ── PRE-VALIDATION #1: The page's main heading (h1, og:title, or <title>)
        # must look like a personal name. If it's a section title like "Current
        # Faculty" or "Home Page" the LLM will invent a fake — refuse up front.
        h1_name = self._extract_candidate_name_from_heading(soup)
        if not self._is_real_name(h1_name):
            logger.debug(f"  [research]   skip {url[:60]} — h1 not a personal name: {h1_name[:40]!r}")
            return None

        # ── PRE-VALIDATION #2: person-signal gate
        signal_count, signals = _count_person_signals(content, text)
        if signal_count < self.MIN_PERSON_SIGNALS:
            logger.debug(
                f"  [research]   skip {url[:60]} — only {signal_count} person signal(s) "
                f"({signals[:3]})"
            )
            return None

        info: dict | None = None
        if settings.openai_api_key or settings.anthropic_api_key:
            try:
                response = await llm.chat(
                    system=RESEARCH_EXTRACT,
                    user=(
                        f"URL: {url}\nDomain: {domain}\nQuery: {query}\n"
                        f"Page heading detected as a real person: {h1_name!r}\n\n"
                        f"Page content:\n{text[:6000]}"
                    ),
                    temperature=0.1,
                )
                data = parse_llm_json(response)
                if data and isinstance(data, dict) and data.get("is_researcher"):
                    info = self._normalize_extraction(data, url)
            except Exception as e:
                logger.debug(f"LLM extraction failed for {url}: {e}")

        # If the LLM didn't return one, build a minimal record FROM the heading
        if info is None:
            country = self._guess_country_from_text(text)
            info = {
                "is_researcher": True,
                "is_collaboration_friendly": True,
                "name": h1_name,
                "title": "",
                "institution": domain,
                "department": "",
                "country": country,
                "region": self._classify_region(country, url),
                "office_address": "",
                "current_fields": [],
                "past_fields": [],
                "research_fields": [],
                "recent_papers": [],
                "bio": text[:400],
                "contact_email": "",
                "all_emails": [],
                "contact_phone": "",
                "personal_website": "",
                "linkedin_url": "",
                "twitter_url": "",
                "github_url": "",
                "google_scholar_url": "",
                "orcid_url": "",
                "researchgate_url": "",
                "profile_url": url,
            }

        # Cross-check: the LLM-extracted name must match the h1/og:title candidate
        # within a Levenshtein-style overlap, or the LLM invented something.
        llm_name = info.get("name", "").strip()
        if not self._names_match(llm_name, h1_name):
            logger.debug(
                f"  [research]   skip {url[:60]} — LLM name '{llm_name[:40]}' "
                f"disagrees with heading '{h1_name[:40]}'"
            )
            return None

        # Enrich with raw-HTML regex
        self._enrich_contacts_from_html(info, content, soup)
        info["_person_signals"] = signal_count
        return info

    @staticmethod
    async def _extract_orcid(url: str, query: str) -> dict | None:
        """Use ORCID's public API to get the person record (page is JS-only)."""
        m = re.search(r"/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])", url)
        if not m:
            return None
        orcid_id = m.group(1)
        api_url = f"https://pub.orcid.org/v3.0/{orcid_id}/record"
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
                resp = await c.get(
                    api_url,
                    headers={"Accept": "application/json"},
                )
            if resp.status_code != 200:
                return None
            data = resp.json()
        except Exception as e:
            logger.debug(f"ORCID API failed for {orcid_id}: {e}")
            return None

        person = (data.get("person") or {})
        name_obj = (person.get("name") or {})
        given = ((name_obj.get("given-names") or {}).get("value") or "").strip()
        family = ((name_obj.get("family-name") or {}).get("value") or "").strip()
        if not given and not family:
            return None
        full_name = f"{given} {family}".strip()
        if not ResearchDiscoveryAgent._is_real_name(full_name):
            return None

        # Emails
        emails: list[str] = []
        primary_email = ""
        for e in (person.get("emails") or {}).get("email", []) or []:
            ev = (e.get("email") or "").strip()
            if ev:
                emails.append(ev)
                if not primary_email and e.get("primary") in (True, "true", "TRUE"):
                    primary_email = ev
        if not primary_email and emails:
            primary_email = emails[0]

        # Affiliations (most recent employment / education / qualification)
        activities = data.get("activities-summary") or {}
        affs: list[dict] = []
        for group in ("employments", "educations", "qualifications"):
            for a in (activities.get(group) or []):
                org = (a.get("organization") or {}).get("name") or ""
                dept = (a.get("department-name") or "") or ""
                role = (a.get("role-title") or "") or ""
                if org:
                    affs.append({"org": org, "dept": dept, "role": role, "group": group})
        # Take the first employment as primary
        primary = next((a for a in affs if a["group"] == "employments"), affs[0] if affs else None)
        institution = primary["org"] if primary else ""
        department = primary["dept"] if primary else ""
        title = primary["role"] if primary else ""

        # Keywords / research areas
        keywords: list[str] = []
        for kw in (person.get("keywords") or {}).get("keyword", []) or []:
            v = (kw.get("content") or "").strip()
            if v:
                keywords.append(v[:100])

        # Country from affiliations
        country = ""
        for a in affs:
            addr = (a.get("address") or {}) if False else {}
            # address is nested under organization -> address
            org_data = next((x for x in (data.get("activities-summary") or {}).get(a["group"], []) if x == a), None)
        # Easier: derive country from institution text
        all_text = " ".join([institution, department] + keywords).lower()
        country = ResearchDiscoveryAgent._guess_country_from_text(all_text)
        if not country and institution:
            # Default unknown
            country = ""

        return {
            "is_researcher": True,
            "is_collaboration_friendly": True,
            "name": full_name,
            "title": title[:200],
            "institution": institution[:200],
            "department": department[:200],
            "country": country[:100],
            "region": ResearchDiscoveryAgent._classify_region(country, url),
            "office_address": "",
            "current_fields": keywords[:10],
            "past_fields": [],
            "research_fields": keywords[:15],
            "recent_papers": [],
            "bio": "",
            "contact_email": primary_email[:200],
            "all_emails": [e[:200] for e in emails[:10]],
            "contact_phone": "",
            "personal_website": "",
            "linkedin_url": "",
            "twitter_url": "",
            "github_url": "",
            "google_scholar_url": "",
            "orcid_url": url,
            "researchgate_url": "",
            "profile_url": url,
        }

    async def _fallback_extract_from_url(self, url: str, query: str) -> dict | None:
        """When the page fetch fails (captcha / 999 / JS shell), try the
        platform's public API or parse the URL slug itself. Returns a
        fully-populated info dict (no LLM needed) or None."""
        host = urlparse(url).netloc.lower().replace("www.", "")
        path = urlparse(url).path

        if host == "dblp.org":
            return await self._fallback_dblp(url, query)
        if host == "linkedin.com" or host.endswith(".linkedin.com"):
            return self._fallback_linkedin(url, query)
        if host == "semanticscholar.org":
            return await self._fallback_semantic_scholar(url, query)
        if host == "scholar.google.com":
            return self._fallback_google_scholar(url, query)
        if host == "orcid.org":
            return await self._extract_orcid(url, query)
        if host in ("reddit.com", "www.reddit.com", "old.reddit.com"):
            return await self._fallback_reddit(url, query)
        return None

    @staticmethod
    async def _fallback_dblp(url: str, query: str) -> dict | None:
        """DBLP: page is server-rendered, but if it 404s, query the search API
        to find the canonical person entry."""
        parsed = urlparse(url)
        m = re.search(r"/pid/([^/]+)/([^/]+)", parsed.path)
        if not m:
            return None
        slug_initial, slug_name = m.group(1), m.group(2)
        # Try the public search API to confirm / enrich the name
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as c:
                api = f"https://dblp.org/search/author/api?q={slug_name}&format=json"
                r = await c.get(api)
                if r.status_code == 200:
                    d = r.json()
                    for hit in d.get("result", {}).get("hits", {}).get("hit", []):
                        info = hit.get("info", {})
                        api_url = (info.get("url") or "").lower()
                        if slug_name.lower() in api_url:
                            name = (info.get("author") or "").strip()
                            if name and ResearchDiscoveryAgent._is_real_name(name):
                                return {
                                    "is_researcher": True,
                                    "is_collaboration_friendly": True,
                                    "name": name,
                                    "title": "",
                                    "institution": "",
                                    "department": "",
                                    "country": "",
                                    "region": "global",
                                    "office_address": "",
                                    "current_fields": [],
                                    "past_fields": [],
                                    "research_fields": [],
                                    "recent_papers": [],
                                    "bio": "",
                                    "contact_email": "",
                                    "all_emails": [],
                                    "contact_phone": "",
                                    "personal_website": "",
                                    "linkedin_url": "",
                                    "twitter_url": "",
                                    "github_url": "",
                                    "google_scholar_url": "",
                                    "orcid_url": "",
                                    "researchgate_url": "",
                                    "profile_url": url,
                                }
        except Exception:
            pass
        # Fall back: parse the slug itself ("YannLeCun" -> "Yann Le Cun")
        camel_parts = re.findall(r"[A-Z][a-z]*|[a-z]+", slug_name)
        if len(camel_parts) >= 2:
            name = " ".join(camel_parts)
            if ResearchDiscoveryAgent._is_real_name(name):
                return {
                    "is_researcher": True,
                    "is_collaboration_friendly": True,
                    "name": name,
                    "title": "",
                    "institution": "",
                    "department": "",
                    "country": "",
                    "region": "global",
                    "office_address": "",
                    "current_fields": [],
                    "past_fields": [],
                    "research_fields": [],
                    "recent_papers": [],
                    "bio": "",
                    "contact_email": "",
                    "all_emails": [],
                    "contact_phone": "",
                    "personal_website": "",
                    "linkedin_url": "",
                    "twitter_url": "",
                    "github_url": "",
                    "google_scholar_url": "",
                    "orcid_url": "",
                    "researchgate_url": "",
                    "profile_url": url,
                }
        return None

    @staticmethod
    def _fallback_linkedin(url: str, query: str) -> dict | None:
        """LinkedIn: page is gated. The URL slug is the only signal we have.
        'dr-md-shafiqul-islam-1bb86842' -> 'Md Shafiqul Islam' (drop 'dr' prefix and trailing ID)"""
        m = re.search(r"/in/([^/]+)/?", url)
        if not m:
            return None
        slug = m.group(1)
        # Strip trailing LinkedIn numeric ID. LinkedIn IDs are 4-30 chars of [A-Za-z0-9]
        # at the end. Detect by being alphanumeric (not just digits) — vanity slugs
        # like "anwarstat" end with letters; LinkedIn-added IDs are typically mixed.
        # Heuristic: if the last segment after the last dash is >= 5 chars AND is
        # alphanumeric (not all letters), treat it as an ID and strip it.
        parts = slug.split("-")
        if len(parts) >= 3 and re.match(r"^[A-Za-z0-9]{5,}$", parts[-1]) and any(c.isdigit() for c in parts[-1]):
            parts = parts[:-1]
        cleaned = "-".join(parts)
        # Drop common title prefixes
        prefixes = {"dr", "prof", "mr", "mrs", "ms", "md", "engr", "eng"}
        words = [p for p in cleaned.split("-") if p.lower() not in prefixes]
        if len(words) < 2:
            return None
        name = " ".join(w.capitalize() for w in words)
        if not ResearchDiscoveryAgent._is_real_name(name):
            return None
        return {
            "is_researcher": True,
            "is_collaboration_friendly": True,
            "name": name,
            "title": "",
            "institution": "",
            "department": "",
            "country": "",
            "region": "global",
            "office_address": "",
            "current_fields": [],
            "past_fields": [],
            "research_fields": [],
            "recent_papers": [],
            "bio": "",
            "contact_email": "",
            "all_emails": [],
            "contact_phone": "",
            "personal_website": "",
            "linkedin_url": url,
            "twitter_url": "",
            "github_url": "",
            "google_scholar_url": "",
            "orcid_url": "",
            "researchgate_url": "",
            "profile_url": url,
        }

    @staticmethod
    async def _fallback_semantic_scholar(url: str, query: str) -> dict | None:
        """Semantic Scholar: the page is JS-only. Use the public API to get author info."""
        m = re.search(r"/author/([A-Za-z0-9\-]+)/?(\d+)?", url)
        if not m:
            return None
        author_id = m.group(2) or m.group(1)
        if not author_id or not author_id.isdigit():
            return None
        try:
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(
                    f"https://api.semanticscholar.org/graph/v1/author/{author_id}",
                    params={"fields": "name,affiliations,homepage,externalIds"},
                )
                if r.status_code == 200:
                    d = r.json()
                    name = (d.get("name") or "").strip()
                    if not ResearchDiscoveryAgent._is_real_name(name):
                        return None
                    affs = d.get("affiliations") or []
                    institution = (affs[0] if affs else "") or ""
                    homepage = d.get("homepage") or ""
                    ext = d.get("externalIds") or {}
                    return {
                        "is_researcher": True,
                        "is_collaboration_friendly": True,
                        "name": name,
                        "title": "",
                        "institution": institution[:200],
                        "department": "",
                        "country": ResearchDiscoveryAgent._guess_country_from_text(institution)[:100],
                        "region": "global",
                        "office_address": "",
                        "current_fields": [],
                        "past_fields": [],
                        "research_fields": [],
                        "recent_papers": [],
                        "bio": "",
                        "contact_email": "",
                        "all_emails": [],
                        "contact_phone": "",
                        "personal_website": homepage[:500],
                        "linkedin_url": "",
                        "twitter_url": "",
                        "github_url": "",
                        "google_scholar_url": "",
                        "orcid_url": (f"https://orcid.org/{ext['ORCID']}" if ext.get("ORCID") else ""),
                        "researchgate_url": "",
                        "profile_url": url,
                    }
        except Exception:
            pass
        return None

    @staticmethod
    def _fallback_google_scholar(url: str, query: str) -> dict | None:
        """Scholar: page is captcha-gated. We have only the ?user=ID and the
        search query — query the search API for a matching name. If SerpAPI
        is configured we could call its scholar_author endpoint; for now we
        skip — too unreliable."""
        return None

    @staticmethod
    async def _fallback_reddit(url: str, query: str) -> dict | None:
        """Reddit: use the public JSON API to extract post author info."""
        parsed = urlparse(url)
        path = parsed.path.lower()
        username = None

        # Try to extract username from a post URL: /r/{sub}/comments/{id}/{slug}/
        post_id = None
        m = re.search(r"/r/[A-Za-z0-9_]+/comments/([A-Za-z0-9]+)", path)
        if m:
            post_id = m.group(1)
            try:
                json_url = f"https://www.reddit.com{parsed.path}.json"
                async with httpx.AsyncClient(timeout=10) as c:
                    headers = {"User-Agent": "ResearchDiscovery/1.0 (research collaborator finder)"}
                    resp = await c.get(json_url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list) and len(data) > 0:
                            post_data = data[0].get("data", {}).get("children", [{}])[0].get("data", {})
                            username = post_data.get("author")
                            if not username or username in ("[deleted]", "AutoModerator"):
                                username = None
            except Exception:
                pass

        # If we have a user profile URL, extract username directly
        if not username:
            m = re.search(r"^/(?:user|u)/([A-Za-z0-9_.\-]+)", path)
            if m:
                username = m.group(1)

        if not username or username in ("[deleted]", "AutoModerator"):
            return None

        # Fetch user info from Reddit JSON API
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                headers = {"User-Agent": "ResearchDiscovery/1.0 (research collaborator finder)"}
                resp = await c.get(f"https://www.reddit.com/user/{username}/about.json", headers=headers)
                if resp.status_code != 200:
                    return None
                user_data = resp.json().get("data", {})

            display_name = (user_data.get("subreddit") or {}).get("title", "") or ""
            total_karma = user_data.get("total_karma", 0)
            created_utc = user_data.get("created_utc", 0)

            if not ResearchDiscoveryAgent._is_real_name(display_name):
                display_name = username

            # Try to extract recent post/comment subreddits as research fields
            async with httpx.AsyncClient(timeout=10) as c:
                headers = {"User-Agent": "ResearchDiscovery/1.0 (research collaborator finder)"}
                resp = await c.get(
                    f"https://www.reddit.com/user/{username}/submitted.json?limit=25",
                    headers=headers,
                )
                fields: list[str] = []
                bio_parts: list[str] = []
                if resp.status_code == 200:
                    posts = resp.json().get("data", {}).get("children", [])
                    subreddits_seen: set[str] = set()
                    for post in posts:
                        pdata = post.get("data", {})
                        sub = pdata.get("subreddit", "")
                        title = pdata.get("title", "")
                        if sub and sub not in subreddits_seen:
                            subreddits_seen.add(sub)
                            fields.append(sub)
                        if title and len(bio_parts) < 3:
                            bio_parts.append(title[:150])

            bio = "; ".join(bio_parts[:3]) if bio_parts else f"Reddit user active in research communities"

            return {
                "is_researcher": True,
                "is_collaboration_friendly": True,
                "name": display_name[:200],
                "title": f"Reddit user (r/{', r/'.join(fields[:3])})" if fields else "Reddit user",
                "institution": "",
                "department": "",
                "country": "",
                "region": "global",
                "office_address": "",
                "current_fields": fields[:10],
                "past_fields": [],
                "research_fields": fields[:15],
                "recent_papers": [],
                "bio": bio[:600],
                "contact_email": "",
                "all_emails": [],
                "contact_phone": "",
                "personal_website": f"https://www.reddit.com/user/{username}",
                "linkedin_url": "",
                "twitter_url": "",
                "github_url": "",
                "google_scholar_url": "",
                "orcid_url": "",
                "researchgate_url": "",
                "profile_url": f"https://www.reddit.com/user/{username}",
            }
        except Exception as e:
            logger.debug(f"Reddit API fallback failed for {username}: {e}")
            return None

    @staticmethod
    def _extract_candidate_name_from_heading(soup) -> str:
        """Pick the most-likely-personal-name string from h1 / og:title / <title>."""
        candidates: list[str] = []
        h1 = soup.find("h1")
        if h1:
            candidates.append(h1.get_text(" ", strip=True))
        og = soup.find("meta", attrs={"property": "og:title"})
        if og and og.get("content"):
            candidates.append(og["content"].strip())
        if soup.title and soup.title.string:
            candidates.append(soup.title.string.strip())
        # Take the first candidate that is a real name
        for c in candidates:
            c = c.strip()
            # Strip common platform prefixes like "John Doe | ResearchGate"
            for sep in (" | ", " - ", " — ", " – "):
                if sep in c:
                    c = c.split(sep)[0].strip()
            # If the candidate has multiple " | " separated names (e.g. "John Doe | Anna Lee"),
            # we want just the first. If there are commas like "Doe, John", flip to "John Doe".
            if "," in c and len(c.split(",")) == 2:
                left, right = [p.strip() for p in c.split(",", 1)]
                # "Doe, John" -> "John Doe"
                if len(left) <= 25 and len(right) <= 25 and re.match(r"^[A-Z]", right):
                    c = f"{right} {left}"
            if ResearchDiscoveryAgent._is_real_name(c):
                return c
        return ""

    @staticmethod
    def _names_match(a: str, b: str) -> bool:
        """Loose check: do the LLM-extracted name and the page heading refer to
        the same person? Allow one word to differ in case / order, require the
        overlapping tokens to cover the shorter name."""
        if not a or not b:
            return False
        ta = {t.lower() for t in re.findall(r"[A-Za-z]+", a) if len(t) > 1}
        tb = {t.lower() for t in re.findall(r"[A-Za-z]+", b) if len(t) > 1}
        if not ta or not tb:
            return False
        common = ta & tb
        if not common:
            return False
        shorter = min(len(ta), len(tb))
        return len(common) >= max(1, shorter - 1)

    def _normalize_extraction(self, data: dict, url: str) -> dict:
        name = (data.get("name") or "").strip()
        if not self._is_real_name(name):
            return {"is_researcher": False}

        def _as_list(v) -> list[str]:
            if isinstance(v, str):
                return [s.strip() for s in re.split(r"[,;\n]", v) if s.strip()]
            if isinstance(v, list):
                return [str(s).strip() for s in v if str(s).strip()]
            return []

        current_fields = _as_list(data.get("current_fields"))
        past_fields = _as_list(data.get("past_fields"))
        fields = _as_list(data.get("research_fields"))
        if not fields:
            fields = list(dict.fromkeys(current_fields + past_fields))

        papers = data.get("recent_papers") or []
        if isinstance(papers, str):
            papers = [p.strip() for p in papers.split("\n") if p.strip()]

        all_emails = _as_list(data.get("all_emails"))
        primary_email = (data.get("contact_email") or "").strip()
        if primary_email and primary_email not in all_emails:
            all_emails.insert(0, primary_email)
        elif not primary_email and all_emails:
            primary_email = all_emails[0]

        country = (data.get("country") or "").strip()

        return {
            "is_researcher": True,
            "is_collaboration_friendly": bool(data.get("is_collaboration_friendly", True)),
            "name": name[:200],
            "title": (data.get("title") or "").strip()[:200],
            "institution": (data.get("institution") or "").strip()[:200],
            "department": (data.get("department") or "").strip()[:200],
            "country": country[:100],
            "region": self._classify_region(country, url),
            "office_address": (data.get("office_address") or "").strip()[:300],
            "current_fields": [f[:100] for f in current_fields[:10]],
            "past_fields": [f[:100] for f in past_fields[:10]],
            "research_fields": [f[:100] for f in fields[:15]],
            "recent_papers": [p[:200] for p in papers[:5]],
            "bio": (data.get("bio") or "").strip()[:600],
            "contact_email": primary_email[:200],
            "all_emails": [e[:200] for e in all_emails[:10]],
            "contact_phone": (data.get("contact_phone") or "").strip()[:50],
            "personal_website": (data.get("personal_website") or "").strip()[:500],
            "linkedin_url": (data.get("linkedin_url") or "").strip()[:500],
            "twitter_url": (data.get("twitter_url") or "").strip()[:500],
            "github_url": (data.get("github_url") or "").strip()[:500],
            "google_scholar_url": (data.get("google_scholar_url") or "").strip()[:500],
            "orcid_url": (data.get("orcid_url") or "").strip()[:500],
            "researchgate_url": (data.get("researchgate_url") or "").strip()[:500],
            "profile_url": (data.get("profile_url") or url).strip()[:500],
        }

    @staticmethod
    def _enrich_contacts_from_html(info: dict, html: str, soup) -> None:
        """Regex-scrape the raw HTML for emails, phones, and social URLs the LLM may have missed."""
        email_re = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
        found_emails: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().startswith("mailto:"):
                addr = href.split(":", 1)[1].split("?", 1)[0].strip()
                if addr and addr not in found_emails:
                    found_emails.append(addr)
            elif href.lower().startswith("tel:"):
                phone = href.split(":", 1)[1].strip()
                if phone and not info.get("contact_phone"):
                    info["contact_phone"] = phone[:50]
        for m in email_re.findall(html):
            m = m.strip().lower()
            if any(bad in m for bad in ("example.com", "sentry.io", "wixpress", ".png", ".jpg", ".gif")):
                continue
            if m not in found_emails:
                found_emails.append(m)

        existing = [e.lower() for e in (info.get("all_emails") or [])]
        for e in found_emails:
            if e.lower() not in existing:
                info.setdefault("all_emails", []).append(e[:200])
                existing.append(e.lower())
        info["all_emails"] = (info.get("all_emails") or [])[:10]
        if not info.get("contact_email") and info["all_emails"]:
            info["contact_email"] = info["all_emails"][0]

        if not info.get("contact_phone"):
            phone_re = re.compile(r"\+?\d[\d\s().\-]{7,}\d")
            for txt in soup.find_all(string=True):
                s = txt.strip()
                if 8 <= len(s) <= 40 and phone_re.search(s):
                    cand = phone_re.search(s).group(0).strip()
                    if sum(c.isdigit() for c in cand) >= 8:
                        info["contact_phone"] = cand[:50]
                        break

        social_map = {
            "linkedin_url":        ("linkedin.com/in", "linkedin.com/pub"),
            "twitter_url":         ("twitter.com/", "x.com/"),
            "github_url":          ("github.com/",),
            "google_scholar_url":  ("scholar.google.",),
            "orcid_url":           ("orcid.org/",),
            "researchgate_url":    ("researchgate.net/profile",),
        }
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            low = href.lower()
            for field, patterns in social_map.items():
                if info.get(field):
                    continue
                if any(p in low for p in patterns):
                    info[field] = href[:500]

        if not info.get("personal_website"):
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                low = href.lower()
                if not low.startswith(("http://", "https://")):
                    continue
                if any(s in low for s in ("linkedin", "twitter", "x.com/", "facebook", "instagram",
                                          "github", "scholar.google", "orcid", "researchgate",
                                          "youtube", "academia.edu", "mailto:", "tel:")):
                    continue
                anchor = (a.get_text(strip=True) or "").lower()
                if any(k in anchor for k in ("website", "homepage", "personal", "blog")):
                    info["personal_website"] = href[:500]
                    break

    async def _store_researcher(self, session, info: dict, query: str, url: str):
        name = info.get("name", "").strip()
        if not name:
            return
        profile_url = info.get("profile_url") or url

        # Dedup on profile_url OR (name + institution) tuple
        existing_q = select(ResearchLead).where(ResearchLead.profile_url == profile_url)
        existing = (await session.execute(existing_q)).scalar_one_or_none()
        if existing:
            return
        if info.get("institution"):
            dup_q = select(ResearchLead).where(
                ResearchLead.name == name,
                ResearchLead.institution == info["institution"],
            )
            if (await session.execute(dup_q)).scalar_one_or_none():
                return

        fit_info = await self._score_fit_and_explain(info)
        info["_score"] = fit_info.get("score", 30)

        lead = ResearchLead(
            name=name,
            title=info.get("title", ""),
            institution=info.get("institution", ""),
            department=info.get("department", ""),
            country=info.get("country", ""),
            region=info.get("region", "global"),
            office_address=info.get("office_address", ""),
            current_fields=info.get("current_fields", []),
            past_fields=info.get("past_fields", []),
            research_fields=info.get("research_fields", []),
            recent_papers=info.get("recent_papers", []),
            bio=info.get("bio", ""),
            contact_email=info.get("contact_email", ""),
            all_emails=info.get("all_emails", []),
            contact_phone=info.get("contact_phone", ""),
            personal_website=info.get("personal_website", ""),
            linkedin_url=info.get("linkedin_url", ""),
            twitter_url=info.get("twitter_url", ""),
            github_url=info.get("github_url", ""),
            google_scholar_url=info.get("google_scholar_url", ""),
            orcid_url=info.get("orcid_url", ""),
            researchgate_url=info.get("researchgate_url", ""),
            profile_url=profile_url,
            source=self._classify_source(url),
            source_query=query,
            relevance_score=fit_info.get("score", 30),
            relevance_reason=fit_info.get("reason", ""),
            why_good_fit=fit_info.get("why_good_fit", ""),
        )
        session.add(lead)
        contact_summary = []
        if lead.contact_email: contact_summary.append("email")
        if lead.contact_phone: contact_summary.append("phone")
        if lead.linkedin_url: contact_summary.append("linkedin")
        if lead.github_url: contact_summary.append("github")
        if lead.google_scholar_url: contact_summary.append("scholar")
        if lead.orcid_url: contact_summary.append("orcid")
        contact_str = ",".join(contact_summary) or "none"

    @staticmethod
    def _classify_source(url: str) -> str:
        domain = urlparse(url).netloc.replace("www.", "").lower()
        if "researchgate" in domain: return "researchgate"
        if "academia.edu" in domain: return "academia"
        if "scholar.google" in domain or "google" in domain: return "google_scholar"
        if "arxiv" in domain: return "arxiv"
        if "linkedin" in domain: return "linkedin"
        if "orcid" in domain: return "orcid"
        if "semanticscholar" in domain: return "semantic_scholar"
        if "dblp" in domain: return "dblp"
        if "ieee" in domain: return "ieee"
        if "acm" in domain: return "acm"
        if "reddit" in domain: return "reddit"
        if domain.endswith(".edu") or ".edu." in domain: return "university_site"
        if domain.endswith(".ac.bd") or domain.endswith(".ac.in"): return "university_site"
        return "academic_profile"

    async def _score_fit_and_explain(self, info: dict) -> dict:
        score = 30
        reason_parts = []
        text = f"{info.get('title', '')} {info.get('department', '')} {info.get('bio', '')} {' '.join(info.get('research_fields', []))}".lower()

        skill_keywords = [
            ("python", 5), ("scikit-learn", 8), ("sklearn", 8), ("pandas", 5),
            ("numpy", 5), ("matplotlib", 5), ("seaborn", 5), ("plotly", 4),
            ("sql", 4), ("statistics", 8), ("statistical", 8), ("nltk", 4),
            ("data analysis", 8), ("data visualization", 7), ("eda", 6),
            ("classification", 6), ("regression", 6), ("clustering", 5),
            ("machine learning", 8), ("ml", 5),
            ("deep learning", 8), ("dl", 5), ("neural network", 8),
            ("artificial intelligence", 8), ("ai", 5),
            ("natural language processing", 8), ("nlp", 5),
            ("computer vision", 8), ("cv", 4), ("image processing", 6),
            ("transformer", 6), ("bert", 6), ("gpt", 6),
            ("llm", 6), ("large language model", 8),
            ("reinforcement learning", 6), ("rl", 4),
            ("generative ai", 6), ("genai", 4),
            ("tensorflow", 6), ("pytorch", 6), ("keras", 5),
            ("hugging face", 5), ("transformers", 5),
            ("data science", 8), ("big data", 5),
        ]
        for kw, pts in skill_keywords:
            if kw in text:
                score += pts
                if pts >= 6:
                    reason_parts.append(f"works in {kw}")

        title_lower = info.get("title", "").lower()
        friendly_titles = {
            "phd student", "msc student", "ms student", "research assistant",
            "research associate", "junior researcher", "postdoc", "lecturer",
            "assistant professor", "undergraduate", "research scholar",
            "research student", "graduate student", "doctoral student",
        }
        if any(ft in title_lower for ft in friendly_titles):
            score += 15
            reason_parts.append(f"peer-level ({title_lower})")

        country = info.get("country", "").lower()
        if country == "bangladesh":
            score += 10
            reason_parts.append("Bangladesh-based")
        elif country in {"india", "pakistan", "sri lanka", "nepal"}:
            score += 5
            reason_parts.append("South Asia-based")

        if info.get("contact_email"):
            score += 10
        if info.get("contact_phone"):
            score += 3
        if info.get("linkedin_url"):
            score += 5
        if info.get("google_scholar_url") or info.get("orcid_url"):
            score += 3
        if info.get("github_url"):
            score += 2
        if info.get("recent_papers"):
            score += min(10, len(info.get("recent_papers", [])) * 2)
            reason_parts.append(f"{len(info.get('recent_papers', []))} papers found")
        if info.get("current_fields"):
            reason_parts.append(f"currently in {', '.join(info['current_fields'][:2])}")

        if info.get("is_collaboration_friendly"):
            score += 5

        score = min(100, max(0, score))
        reason = " — ".join(reason_parts) if reason_parts else "Potential research fit"

        why_good_fit = ""
        if settings.openai_api_key or settings.anthropic_api_key:
            try:
                user = (
                    f"Name: {info.get('name', '')}\n"
                    f"Title: {info.get('title', '')}\n"
                    f"Institution: {info.get('institution', '')}\n"
                    f"Country: {info.get('country', '')}\n"
                    f"Fields: {', '.join(info.get('research_fields', []))}\n"
                    f"Papers: {'; '.join(info.get('recent_papers', []))[:300]}\n"
                    f"Bio: {info.get('bio', '')[:300]}"
                )
                response = await llm.chat(
                    system=RESEARCH_FIT_PROMPT,
                    user=user,
                    temperature=0.3,
                )
                data = parse_llm_json(response)
                if data:
                    return {
                        "score": int(data.get("score", score)),
                        "reason": (data.get("reason") or reason)[:300],
                        "why_good_fit": (data.get("why_good_fit") or "")[:500],
                    }
            except Exception as e:
                logger.debug(f"LLM fit scoring failed: {e}")

        return {"score": score, "reason": reason, "why_good_fit": why_good_fit or self._default_why_fit(info)}

    @staticmethod
    def _default_why_fit(info: dict) -> str:
        fields = ", ".join(info.get("research_fields", [])[:3]) or "research"
        country = info.get("country") or "their region"
        return (
            f"Works in {fields}. Based in {country}. "
            f"You can offer data analysis, statistical modeling, and scikit-learn implementation support."
        )


class ResearchMatcherAgent(BaseAgent):
    async def run(self):
        result = await self.session.execute(
            select(ResearchLead).where(ResearchLead.relevance_score == 0)
        )
        leads = result.scalars().all()
        profile = (await self.session.execute(select(UserProfile))).scalar_one_or_none()
        profile_text = (
            f"{profile.title or ''} {profile.summary or ''} "
            f"{' '.join(profile.skills or [])}" if profile else ""
        ).lower()
        for lead in leads:
            score = 20
            fields_text = " ".join(lead.research_fields or []).lower()
            for skill in (profile.skills or []) if profile else []:
                if skill.lower() in fields_text or skill.lower() in (lead.bio or "").lower():
                    score += 10
            if "bangladesh" in (lead.country or "").lower() or lead.region == "bangladesh":
                score += 10
            if "student" in (lead.title or "").lower() or "phd" in (lead.title or "").lower():
                score += 5
            lead.relevance_score = min(100, score)
        await self.session.commit()
        logger.info(f"Scored {len(leads)} research leads")


class ResearchOutreachAgent(BaseAgent):
    async def run(self, min_score: int = 30):
        result = await self.session.execute(
            select(ResearchLead)
            .where(ResearchLead.relevance_score >= min_score)
            .where(ResearchLead.outreach_draft == "")
            .order_by(ResearchLead.relevance_score.desc())
            .limit(30)
        )
        leads = result.scalars().all()
        if not leads:
            return
        for lead in leads:
            draft = await self._generate_outreach(lead)
            if draft:
                lead.outreach_draft = draft
        await self.session.commit()
        logger.info(f"Generated outreach drafts for {len(leads)} research leads")

    async def _generate_outreach(self, lead: ResearchLead) -> str:
        if not (settings.openai_api_key or settings.anthropic_api_key):
            return self._fallback_outreach(lead)
        try:
            user = (
                f"Name: {lead.name}\n"
                f"Title: {lead.title}\n"
                f"Institution: {lead.institution}\n"
                f"Fields: {', '.join(lead.research_fields or [])}\n"
                f"Papers: {'; '.join(lead.recent_papers or [])[:300]}"
            )
            response = await llm.chat(
                system=RESEARCH_OUTREACH,
                user=user,
                temperature=0.5,
            )
            data = parse_llm_json(response)
            if data and data.get("subject") and data.get("email_body"):
                return f"Subject: {data['subject']}\n\n{data['email_body']}"
        except Exception as e:
            logger.debug(f"LLM outreach failed for {lead.name}: {e}")
        return self._fallback_outreach(lead)

    @staticmethod
    def _fallback_outreach(lead: ResearchLead) -> str:
        first_paper = (lead.recent_papers or ["your work"])[0]
        return (
            f"Subject: Collaboration offer — data analysis & ML implementation\n\n"
            f"Hi {lead.name.split()[0] if lead.name else 'there'},\n\n"
            f"I'm Sium, a final-year Statistics undergrad at Dhaka College. I came across your work on "
            f"{first_paper[:80]} and was impressed.\n\n"
            f"I can help with data analysis, statistical modeling, EDA, and ML implementation (scikit-learn, "
            f"Pandas, Matplotlib). I'm available ~10-15 hrs/week and would love to contribute to your research.\n\n"
            f"Would you be open to a 15-minute call to discuss? My portfolio: siumahameed.github.io/portfolio/\n\n"
            f"Best,\nSium"
        )
