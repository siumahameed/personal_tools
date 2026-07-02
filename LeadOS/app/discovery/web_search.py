import asyncio
from app.core.base import BaseAgent, logger
from app.core.models import Job, Prospect, ScrapeSession
from app.core.database import db_write_lock
from app.llm.client import llm
from app.llm.prompts import EXTRACT_OPPORTUNITY
from app.llm.parser import parse_llm_json
from app.core.config import settings
from app.discovery.search_client import SearchClient
from sqlalchemy import select
from bs4 import BeautifulSoup
import httpx
import yaml
import re
from pathlib import Path
from urllib.parse import urlparse


NON_COMPANY_DOMAINS = {
    "github.com", "github.io", "gitlab.com", "bitbucket.org",
    "youtube.com", "youtu.be", "vimeo.com",
    "instagram.com", "tiktok.com",
    "medium.com", "dev.to", "hashnode.dev", "substack.com",
    "stackoverflow.com", "stackexchange.com",
    "wikipedia.org", "wikidata.org", "wikihow.com",
    "geeksforgeeks.org", "tutorialspoint.com", "w3schools.com", "javatpoint.com",
    "towardsdatascience.com", "analyticsvidhya.com", "kdnuggets.com", "datasciencecentral.com",
    "machinelearningmastery.com", "datacamp.com", "kaggle.com", "projectpro.io",
    "fastlaunchapi.com", "algotrading101.com", "cubettech.com",
    "npmjs.com", "pypi.org", "pypi.python.org", "docs.python.org",
    "365datascience.com", "codebasics.io", "interviewquery.com", "guvi.in",
    "codesignal.com", "freelancermap.com", "pinterest.com",
    "ijraset.com", "ijettjournal.org", "ituonline.com", "wscubetech.com",
    "cabotsolutions.com", "investforesight.com", "keylabs.ai",
    "amanxai.com", "quantdare.com", "coderspacket.com",
    "deeplizard.com", "justmetrically.com", "autonmis.com",
    "ibm.com", "coursera.org", "udemy.com", "udacity.com",
    "nature.com", "bing.com",
    "blogspot.com", "wordpress.com",
    "socviz.co", "sellerscommerce.com", "wpnewsify.com",
    "bookkeeping-reviews.com", "qsstudy.com", "ejaet.com",
    "ofdigitalinterest.com", "sdata.com", "easychair.org",
    "do-download.com", "dynamicssquare.com", "xenonstack.com",
    "transporttmsandlogisticstms.com", "pmc.ncbi.nlm.nih.gov",
    "similarweb.com", "clicdata.com",
}

# Social and job platforms — NOT company domains, but we DO want to extract data from them
SOCIAL_SOURCE_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com",
    "upwork.com", "freelancer.com", "fiverr.com", "guru.com", "peopleperhour.com",
    "indeed.com", "monster.com", "glassdoor.com", "simplyhired.com",
    "crunchbase.com", "zoominfo.com", "clutch.co", "goodfirms.co", "g2.com",
    "reddit.com", "quora.com",
    "news.ycombinator.com", "indiehackers.com", "dribbble.com",
}

# Job board domains — extract from these as actual job postings
JOB_BOARD_DOMAINS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "monster.com",
    "simplyhired.com", "ziprecruiter.com", "angel.co", "wellfound.com",
    "ycombinator.com", "remoteok.com", "weworkremotely.com", "himalayas.app",
    "toptal.com", "upwork.com", "freelancer.com", "fiverr.com",
    "workatastartup.com",
}

# Generic platform names — NEVER use these as a company name for a prospect
GENERIC_COMPANY_NAMES = {
    "linkedin", "facebook", "twitter", "x", "youtube", "instagram", "tiktok",
    "reddit", "quora", "medium", "github", "gitlab", "bitbucket",
    "stackoverflow", "wikipedia", "indeed", "glassdoor", "monster",
    "crunchbase", "zoominfo", "clutch", "goodfirms", "g2",
    "ycombinator", "indiehackers", "dribbble", "pinterest",
    "substack", "dev.to", "hashnode", "hackernews", "news",
    "weworkremotely", "remoteok", "himalayas", "wellfound", "angel",
    "ziprecruiter", "simplyhired", "toptal", "fiverr", "upwork",
    "freelancer", "guru", "peopleperhour", "workatastartup",
}

# LinkedIn job URL pattern (e.g. linkedin.com/jobs/view/data-analyst-1234567890)
LINKEDIN_JOB_RE = re.compile(r'linkedin\.com/jobs/view/[^/?#]+-(\d+)', re.I)

# LinkedIn profile URL pattern (e.g. linkedin.com/in/john-doe)
LINKEDIN_PROFILE_RE = re.compile(r'linkedin\.com/in/([a-z0-9\-_.]+)', re.I)

# LinkedIn company URL pattern (e.g. linkedin.com/company/acme-software)
LINKEDIN_COMPANY_RE = re.compile(r'linkedin\.com/company/([a-z0-9\-_.]+)', re.I)


# ── Category names for multi-agent scraping ──────────────
SCRAPE_CATEGORIES = ["team_pages", "about_pages", "small_business", "business_owners", "regional", "linkedin", "facebook", "twitter", "directories", "reddit", "social", "hiring_posts"]

_search_client = SearchClient()


class WebSearchAgent(BaseAgent):
    async def run(self, custom_query: str | None = None):
        queries = self._load_queries()
        if custom_query:
            queries = [custom_query]
        await self._process_queries(queries, "web_search")

    async def run_category(self, category: str):
        queries = self._load_queries(category)
        if queries:
            await self._process_queries(queries, category)

    def _load_queries(self, category: str | None = None) -> list[str]:
        path = Path(__file__).parent / "queries.yml"
        if not path.exists():
            path = Path(settings.config_dir) / "queries.yml"
        if not path.exists():
            return []
        with open(path) as f:
            data = yaml.safe_load(f)
        cats = data.get("categories", {})
        if category:
            return cats.get(category, [])
        return [q for cat_list in cats.values() for q in cat_list]

    async def _process_queries(self, queries: list[str], source_tag: str):
        if not queries:
            return
        total = len(queries)

        async def _run_query(idx_query):
            idx, query = idx_query
            logger.info(f"  [{source_tag}] Search [{idx}/{total}]: {query}")

            # Phase 1: network I/O in parallel — no DB access
            try:
                urls = await _search_client.search(
                    query, settings.max_search_results, settings.search_recency,
                )
            except Exception as e:
                logger.error(f"  [{source_tag}] Search failed: {e}")
                return

            async def _process_url(url: str) -> tuple:
                domain = urlparse(url).netloc.replace("www.", "")
                if domain in NON_COMPANY_DOMAINS:
                    return None
                if not self._is_valid_social_url(url, domain):
                    return None
                content = await self._fetch_page(url)
                if not content:
                    return None
                result = await self._extract_opportunity(content, url)
                if result and result.get("is_opportunity"):
                    return (result, url)
                return None

            url_results = await asyncio.gather(*[_process_url(u) for u in urls])
            url_results = [r for r in url_results if r]

            jobs_found = sum(1 for r, _ in url_results if r.get("is_job"))
            prospects_found = sum(1 for r, _ in url_results if r.get("is_prospect"))

            # Phase 2: serialized DB writes under global lock
            async with db_write_lock:
                session_log = ScrapeSession(
                    source=source_tag,
                    query=query,
                    urls_found=len(urls),
                    jobs_found=jobs_found,
                    prospects_found=prospects_found,
                    status="completed",
                )
                self.session.add(session_log)
                await self.session.flush()

                for result, url in url_results:
                    await self._store_result(result, query, url)

                await self.session.commit()

        tasks = [_run_query((idx, q)) for idx, q in enumerate(queries, 1)]
        await asyncio.gather(*tasks)

    async def _fetch_page(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    return resp.text
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
        return None

    async def _extract_opportunity(self, content: str, url: str) -> dict | None:
        domain = urlparse(url).netloc.replace("www.", "")
        is_job_board = any(jb in domain for jb in JOB_BOARD_DOMAINS) or bool(LINKEDIN_JOB_RE.search(url))

        if settings.openai_api_key or settings.anthropic_api_key:
            try:
                result = await self._extract_with_llm(content, url, is_job_board)
                if result and result.get("is_opportunity"):
                    return result
            except Exception as e:
                logger.debug(f"LLM extraction failed for {url}: {e}")

        return self._extract_fallback(content, url)

    async def _extract_with_llm(self, content: str, url: str, is_job_board: bool) -> dict | None:
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)[:6000]
        if len(text) < 50:
            return None

        domain = urlparse(url).netloc.replace("www.", "")
        if is_job_board:
            prompt = JOB_POST_EXTRACT_PROMPT
        else:
            prompt = EXTRACT_OPPORTUNITY
        user = f"URL: {url}\nDomain: {domain}\n\nPage content:\n{text}"

        response = await llm.chat(system=prompt, user=user, temperature=0.1)
        data = parse_llm_json(response)
        if not data or not isinstance(data, dict):
            return None

        is_opp = data.get("is_opportunity", False)
        is_job = bool(data.get("is_job", False))
        is_prospect = bool(data.get("is_prospect", False))
        if not is_opp and (is_job or is_prospect):
            is_opp = True

        return {
            "is_opportunity": is_opp,
            "is_job": is_job,
            "is_prospect": is_prospect,
            "title": (data.get("title") or "").strip()[:200],
            "description": (data.get("description") or "").strip()[:800],
            "company": (data.get("company") or "").strip()[:200],
            "contact_name": (data.get("contact_name") or "").strip()[:200],
            "contact_email": (data.get("contact_email") or "").strip()[:200],
            "contact_title": (data.get("contact_title") or "").strip()[:200],
            "linkedin_url": (data.get("linkedin_url") or "").strip()[:500],
            "required_skills": (data.get("required_skills") or "").strip()[:500],
            "budget": (data.get("budget") or "").strip()[:100],
        }

    @staticmethod
    def _is_valid_social_url(url: str, domain: str) -> bool:
        """Reject social URLs that don't represent a company, job, or person profile."""
        parsed = urlparse(url)
        path = parsed.path.lower()
        path_parts = [p for p in path.split("/") if p]

        if "linkedin.com" in domain:
            if path.startswith("/jobs/view/") and len(path_parts) >= 3:
                return True
            if path.startswith("/company/") and len(path_parts) >= 2:
                return True
            if path.startswith("/in/") and len(path_parts) >= 2:
                return True
            return False

        if "twitter.com" in domain or "x.com" in domain:
            if not path_parts:
                return False
            blocked = {
                "hashtag", "search", "explore", "settings", "notifications",
                "messages", "compose", "i", "home", "login", "signup",
                "share", "intent", "status",
            }
            if path_parts[0] in blocked:
                return False
            if not re.match(r"^[A-Za-z0-9_]{2,30}$", path_parts[0]):
                return False
            return True

        if "facebook.com" in domain:
            if not path_parts:
                return False
            blocked = {
                "groups", "events", "watch", "marketplace", "pages", "pg",
                "profile.php", "people", "photo", "photo.php", "story.php",
                "permalink.php", "login", "signup", "home.php", "sharer",
                "sharer.php", "dialog", "plugins", "tr", "help", "policies",
            }
            if path_parts[0] in blocked:
                return False
            return True

        return True

    def _extract_fallback(self, content: str, url: str) -> dict | None:
        soup = BeautifulSoup(content, "html.parser")
        title_tag = soup.find("title")
        page_title = title_tag.get_text(strip=True) if title_tag else ""
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        description = meta.get("content", "")[:500] if meta else ""
        text = soup.get_text(separator=" ", strip=True)[:2000].lower()

        domain = urlparse(url).netloc.replace("www.", "")
        if domain in NON_COMPANY_DOMAINS:
            return None

        company = self._extract_company_from_url(url) or self._domain_to_company(domain)
        is_social_source = domain in SOCIAL_SOURCE_DOMAINS

        # Job detection
        strong_job_keywords = ["we are hiring", "job description", "job posting", "apply now",
                               "open position", "we are looking for", "join our team", "careers"]
        weak_job_keywords = ["job", "hiring", "freelance", "position", "opening", "contract",
                             "opportunity", "full-time", "part-time", "salary"]
        strong_job_matches = sum(1 for kw in strong_job_keywords if kw in text)
        weak_job_matches = sum(1 for kw in weak_job_keywords if kw in text)
        title_is_job = any(kw in page_title.lower() for kw in ["hiring", "job", "position", "career", "opening", "freelance"])
        is_job = strong_job_matches >= 1 or (title_is_job and weak_job_matches >= 1)

        # Individual client signals — people directly seeking freelancers
        client_keywords = [
            "i need", "i am looking for", "looking for a freelancer", "looking for freelancer",
            "need someone to", "need help with", "need a freelancer", "need freelancer",
            "hire someone", "hire a freelancer", "hire freelancer",
            "help me with", "anyone who can", "looking for someone",
            "i want to hire", "in need of a", "looking to hire",
            "any freelancer", "looking for an expert",
        ]
        client_matches = sum(1 for kw in client_keywords if kw in text)
        title_is_client_request = any(kw in page_title.lower() for kw in ["looking for", "need", "hire", "help", "wanted"])
        is_individual_client = client_matches >= 1 or (title_is_client_request and client_matches >= 1)

        # Small business signals
        small_biz_keywords = [
            "small business", "startup", "entrepreneur", "small company",
            "sme", "small team", "my business", "my startup",
            "growing company", "local business", "small shop",
            "ecommerce store", "online store", "small retail",
        ]
        small_biz_matches = sum(1 for kw in small_biz_keywords if kw in text)
        is_small_business = small_biz_matches >= 1

        # Prospect detection: company site signals + individual client + small biz
        company_signals = ["about us", "about", "our team", "contact us", "services",
                           "solutions", "portfolio", "clients", "what we do"]
        has_company_signal = any(s in text for s in company_signals) or any(s in page_title.lower() for s in company_signals[:4])
        has_about_page = "about" in url.lower()
        is_prospect = (
            (has_company_signal or has_about_page or is_social_source) and bool(company)
        ) or is_individual_client or is_small_business

        skills = []
        skill_keywords = ["python", "sklearn", "scikit-learn", "pandas", "numpy", "tensorflow",
                          "pytorch", "machine learning", "data science", "data analysis", "sql",
                          "fastapi", "nlp", "deep learning", "ai", "statistics", "regression",
                          "classification", "clustering", "visualization", "django", "flask"]
        for sk in skill_keywords:
            if sk in text:
                skills.append(sk)

        emails = set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', content))
        valid_emails = self._filter_emails(emails)

        if not is_job and not is_prospect:
            return None

        result = {
            "is_opportunity": True,
            "title": page_title[:200] or description[:200] or company or domain,
            "description": description[:500] or text[:500],
            "company": company or domain,
            "contact_name": "",
            "contact_email": valid_emails[0] if valid_emails else "",
            "contact_title": "",
            "linkedin_url": "",
            "required_skills": ", ".join(skills[:8]),
            "budget": "",
            "is_job": is_job,
            "is_prospect": is_prospect,
        }
        return result

    @staticmethod
    def _domain_to_company(domain: str) -> str | None:
        parts = domain.replace("www.", "").split(".")
        if not parts or parts[0] in ("com", "org", "net", "io", "co", "uk", "de", "fr"):
            return None
        name = parts[0].title()
        if len(name) < 2:
            return None
        return name

    @staticmethod
    def _extract_company_from_url(url: str) -> str | None:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        path = parsed.path.strip("/")
        if "linkedin.com" in domain:
            parts = path.split("/")
            for i, p in enumerate(parts):
                if p == "company" and i + 1 < len(parts):
                    return parts[i + 1].replace("-", " ").replace("_", " ").title()
        if "facebook.com" in domain:
            parts = path.split("/")
            if parts and parts[0] not in ("", "pages", "pg", "profile.php", "people", "groups", "events", "watch", "marketplace"):
                return parts[0].replace("-", " ").replace("_", " ").title()
        if "twitter.com" in domain or "x.com" in domain:
            parts = path.split("/")
            if parts and parts[0] not in ("hashtag", "search", "explore", "settings", "notifications", "messages", "compose", "i", "home", "login", "signup"):
                return parts[0]
        if "crunchbase.com" in domain:
            parts = path.split("/")
            if parts and parts[0] not in ("", "organization", "person", "company", "discover", "search"):
                return parts[0].replace("-", " ").replace("_", " ").title()
            if len(parts) >= 2 and parts[0] in ("organization", "company"):
                return parts[1].replace("-", " ").replace("_", " ").title()
        if "zoominfo.com" in domain:
            parts = path.split("/")
            if len(parts) >= 2 and parts[0] in ("c", "p"):
                return parts[1].replace("-", " ").replace("_", " ").title()
        return None

    @staticmethod
    def _filter_emails(emails: set) -> list:
        valid = []
        for e in emails:
            e = e.strip().strip(".'\",;:()[]")
            if not e:
                continue
            if "example" in e.lower():
                continue
            if any(e.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot")):
                continue
            local, at, domain_part = e.rpartition("@")
            # Skip version-like domains (e.g. @4.2.1, @300..900)
            if re.match(r'^\d+([.,]\d+)*$', domain_part):
                continue
            if ".." in domain_part:
                continue
            # Skip hex-only domains
            if re.match(r'^[0-9a-f]{6,}$', domain_part.replace(".", "")):
                continue
            if "." not in domain_part:
                continue
            valid.append(e)
        return list(dict.fromkeys(valid))[:5]

    async def _store_result(self, result: dict, query: str, url: str):
        company = (result.get("company") or "").strip()
        title = (result.get("title") or "").strip()
        description = (result.get("description") or "").strip()
        is_job = bool(result.get("is_job"))
        is_prospect = bool(result.get("is_prospect"))

        if not is_job and not is_prospect:
            return

        if not company:
            return
        if company.lower() in GENERIC_COMPANY_NAMES:
            return
        if not self._is_real_company_name(company):
            return
        if not self._is_meaningful_title(title, description, company):
            return

        domain = urlparse(url).netloc.replace("www.", "")
        source_map = {
            "linkedin.com": "linkedin",
            "facebook.com": "facebook",
            "twitter.com": "twitter",
            "x.com": "twitter",
            "crunchbase.com": "crunchbase",
            "zoominfo.com": "zoominfo",
            "clutch.co": "clutch",
            "goodfirms.co": "goodfirms",
            "g2.com": "g2",
            "reddit.com": "reddit",
            "quora.com": "quora",
            "news.ycombinator.com": "hackernews",
            "indiehackers.com": "indiehackers",
            "indeed.com": "indeed",
            "glassdoor.com": "glassdoor",
        }
        source = "web_search"
        for d, s in source_map.items():
            if d in domain:
                source = s
                break

        email = (result.get("contact_email") or "").strip()
        linkedin_url = (result.get("linkedin_url") or "").strip()
        required_skills = (result.get("required_skills") or "").strip()
        budget = (result.get("budget") or "").strip()
        contact_name = (result.get("contact_name") or "").strip()
        contact_title = (result.get("contact_title") or "").strip()

        is_job_post = bool(LINKEDIN_JOB_RE.search(url)) or source in {"indeed", "glassdoor"}
        if is_job_post and not linkedin_url:
            if LINKEDIN_COMPANY_RE.search(url):
                linkedin_url = url

        if source == "linkedin" and not linkedin_url and not is_job_post:
            if LINKEDIN_COMPANY_RE.search(url) or LINKEDIN_PROFILE_RE.search(url):
                linkedin_url = url

        notes_parts = []
        if is_job:
            notes_parts.append(f"[JOB POST] {title or 'Open Role'}")
            if budget:
                notes_parts.append(f"Budget: {budget}")
        if description:
            notes_parts.append(description[:600])
        if required_skills:
            notes_parts.append(f"Skills: {required_skills}")
        if query:
            notes_parts.append(f"Search: {query}")
        notes = "\n".join(notes_parts)[:800]

        r = await self.session.execute(
            select(Prospect).where(
                (Prospect.company_url == url) |
                ((Prospect.company_name == company) & (Prospect.email == email) & (Prospect.contact_name == contact_name))
            )
        )
        if r.scalar_one_or_none():
            return

        contact_entry = {}
        if contact_name:
            contact_entry["name"] = contact_name
            contact_entry["title"] = contact_title
            contact_entry["email"] = email
            contact_entry["linkedin"] = linkedin_url
        elif email:
            contact_entry = {"name": "", "title": "", "email": email, "linkedin": linkedin_url, "phone": ""}

        prospect = Prospect(
            company_name=company,
            contact_name=contact_name,
            contact_title=contact_title,
            email=email,
            linkedin_url=linkedin_url,
            company_url=url,
            source=source,
            source_query=query,
            notes=notes,
            contacts=[contact_entry] if contact_entry else [],
        )
        self.session.add(prospect)

    @staticmethod
    def _is_real_company_name(name: str) -> bool:
        if not name or len(name) < 2 or len(name) > 80:
            return False
        if name.lower() in GENERIC_COMPANY_NAMES:
            return False
        blocked_starts = {"login", "sign", "signup", "home", "feed", "search", "explore",
                          "about", "contact", "help", "privacy", "terms", "404", "error",
                          "page not found", "not found", "coming soon", "page", "view",
                          "post", "article", "blog", "news"}
        if name.lower().startswith(tuple(blocked_starts)):
            return False
        if not re.search(r"[a-zA-Z]{2,}", name):
            return False
        if re.fullmatch(r"[\d\s\-_./]+", name):
            return False
        return True

    @staticmethod
    def _is_meaningful_title(title: str, description: str, company: str) -> bool:
        combined = (title + " " + description + " " + company).strip().lower()
        if len(combined) < 6:
            return False
        if title and title.lower() in {"linkedin", "facebook", "twitter", "x", "reddit", "indeed", "glassdoor"}:
            return False
        if not description and len(title) < 4 and not company:
            return False
        return True


class MultiScrapeAgent(BaseAgent):
    """Runs multiple WebSearchAgents concurrently — one per platform category."""

    async def run(self, categories: list[str] | None = None):
        if categories is None:
            categories = SCRAPE_CATEGORIES
        logger.info(f"MultiScrape: spawning {len(categories)} agents in parallel: {categories}")
        tasks = [self._run_single(cat) for cat in categories]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for cat, res in zip(categories, results):
            if isinstance(res, Exception):
                logger.error(f"  MultiScrape agent '{cat}' failed: {res}")

    async def _run_single(self, category: str):
        try:
            async with WebSearchAgent() as agent:
                await agent.run_category(category)
            logger.info(f"  MultiScrape agent '{category}' complete")
        except Exception as e:
            logger.error(f"  MultiScrape agent '{category}' failed: {e}")
