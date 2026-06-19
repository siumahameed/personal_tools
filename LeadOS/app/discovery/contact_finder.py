import asyncio
from app.core.base import BaseAgent, logger
from app.core.models import Job, Prospect
from app.core.database import db_write_lock
from app.core.config import settings
from app.llm.client import llm
from app.llm.prompts import FIND_CONTACTS
from app.llm.parser import parse_llm_json
from app.discovery.search_client import SearchClient
from sqlalchemy import select
import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import json

_search_client = SearchClient()

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com",
    "throwawaymail.com", "yopmail.com", "sharklasers.com", "trashmail.com",
    "mailnator.com", "temp-mail.org", "fakeinbox.com", "maildrop.cc",
    "getairmail.com", "emailforsale.com", "spamgourmet.com",
}


CONTACT_EXTRACT_PROMPT = """You are a contact extraction specialist. Given page content from a company or professional page, extract ALL information you can find.

Extract:
- Company name
- Every person mentioned with their full name, job title, email, LinkedIn URL
- Any email addresses (even without names)
- Phone numbers
- Social media links (LinkedIn, Twitter, Facebook, GitHub)
- Industry/description of what the company does

Return JSON:
{"company": "Company Name", "industry": "", "contacts": [{"name": "", "title": "", "email": "", "linkedin": "", "phone": ""}], "emails": ["email@company.com"], "social": {"linkedin": "", "twitter": "", "facebook": ""}, "description": ""}

If you find ANY people or emails, include them. Empty fields should be empty string or empty list."""  # noqa: E501


class ContactFinderAgent(BaseAgent):
    async def run(self):
        await self._find_contacts_for_jobs()
        await self._find_contacts_for_prospects()

    async def _find_contacts_for_jobs(self):
        result = await self.session.execute(
            select(Job).where(Job.match_score >= settings.match_threshold)
        )
        jobs = result.scalars().all()
        if not jobs:
            return
        sem = asyncio.Semaphore(5)
        found = [0]

        async def _process_job(job):
            async with sem:
                company_name = job.client_name or self._derive_company_name(job.url)
                async with db_write_lock:
                    prospect = await self._ensure_prospect(job, company_name)
                if prospect and not prospect.contact_name:
                    info = await self._quick_scrape(company_name, job.url)
                    if not info:
                        info = await self._deep_scrape_company(company_name, job.url)
                    if info:
                        async with db_write_lock:
                            self._merge_contact_info(prospect, info)
                        found[0] += 1
                        if info.get("contacts"):
                            c = info["contacts"][0]
                            logger.info(f"  Contact: {c.get('name','?')} <{c.get('email','?')}>")
                        elif info.get("emails"):
                            logger.info(f"  Email: {info['emails'][0]}")

        await asyncio.gather(*[_process_job(j) for j in jobs])
        async with db_write_lock:
            await self.session.commit()
        logger.info(f"Found contacts for {found[0]} jobs")

    async def _find_contacts_for_prospects(self):
        result = await self.session.execute(
            select(Prospect)
            .where(Prospect.relevance_score >= 20)
            .where(Prospect.company_name != "")
            .order_by(Prospect.relevance_score.desc())
            .limit(60)
        )
        prospects = result.scalars().all()
        if not prospects:
            return
        sem = asyncio.Semaphore(5)
        found = [0]

        async def _process_prospect(prospect):
            async with sem:
                if prospect.contact_name and prospect.email:
                    return
                info = await self._quick_scrape(prospect.company_name, prospect.company_url or "")
                if not info:
                    info = await self._deep_scrape_company(prospect.company_name, prospect.company_url or "")
                if info:
                    async with db_write_lock:
                        self._merge_contact_info(prospect, info)
                    found[0] += 1

        await asyncio.gather(*[_process_prospect(p) for p in prospects])
        async with db_write_lock:
            await self.session.commit()
        logger.info(f"Found contacts for {found[0]} prospects")

    def _merge_contact_info(self, prospect: Prospect, info: dict):
        contacts = info.get("contacts", [])
        emails = info.get("emails", [])
        social = info.get("social", {})

        # Store all contacts in the contacts JSON field
        existing = list(prospect.contacts or [])
        for c in contacts:
            if c.get("name") or c.get("email"):
                if not any(ex.get("email") == c.get("email") for ex in existing if c.get("email")):
                    existing.append(c)

        # Merge extracted emails as contact-less entries
        for e in emails:
            if e and not any(ex.get("email") == e for ex in existing):
                existing.append({"name": "", "title": "", "email": e, "linkedin": "", "phone": ""})

        prospect.contacts = existing

        # Set the primary contact from the first person found
        if contacts:
            c = contacts[0]
            if c.get("name") and not prospect.contact_name:
                prospect.contact_name = c["name"]
            if c.get("title") and not prospect.contact_title:
                prospect.contact_title = c["title"]
            if c.get("email") and not prospect.email:
                prospect.email = c["email"]
            if c.get("linkedin") and not prospect.linkedin_url:
                prospect.linkedin_url = c["linkedin"]
        elif emails and not prospect.email:
            prospect.email = emails[0]

        # Merge social links
        existing_social = dict(prospect.social_links or {})
        for k, v in social.items():
            if v and not existing_social.get(k):
                existing_social[k] = v
        if social.get("linkedin") and not prospect.linkedin_url:
            prospect.linkedin_url = social["linkedin"]
        prospect.social_links = existing_social

        # Merge industry
        if info.get("industry") and not prospect.industry:
            prospect.industry = info["industry"]

        # Append to notes
        if info.get("description"):
            extra = f"[{info.get('_source','web')}] {info['description'][:200]}"
            if extra not in (prospect.notes or ""):
                prospect.notes = (prospect.notes or "") + "\n" + extra

    async def _ensure_prospect(self, job, company_name: str | None = None):
        name = company_name or job.client_name
        r = await self.session.execute(
            select(Prospect).where(Prospect.company_name == (name or "")).limit(1)
        )
        prospect = r.scalar_one_or_none()
        if not prospect:
            prospect = Prospect(
                company_name=name or "Unknown Company",
                source="web_search",
                notes=job.description[:500] if job.description else "",
                company_url=job.url,
                relevance_score=job.match_score or 0,
                relevance_reason=job.match_reason or "",
                contacts=[],
                social_links={},
            )
            self.session.add(prospect)
            await self.session.flush()
        return prospect

    @staticmethod
    def _derive_company_name(url: str) -> str | None:
        try:
            domain = urlparse(url).netloc.lower()
            for tld in [".com", ".io", ".org", ".net", ".edu", ".co", ".uk", ".ca", ".de", ".fr", ".au"]:
                domain = domain.replace(tld, "")
            domain = domain.replace("www.", "")
            parts = domain.split(".")
            return parts[0].title() if parts[0] else None
        except Exception:
            return None

    @staticmethod
    def _get_root_url(url: str) -> str:
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return url

    # ── Phase 1: Company Website Deep Scrape ──────────────────────

    def _validate_emails(self, emails: list[str]) -> list[str]:
        if not emails:
            return []
        valid = []
        for e in emails:
            e = e.strip().lower()
            domain = e.split("@")[-1] if "@" in e else ""
            if domain in DISPOSABLE_DOMAINS:
                continue
            if not domain or "." not in domain:
                continue
            if len(domain) < 4:
                continue
            valid.append(e)
        return valid

    async def _deep_scrape_company(self, company_name: str, known_url: str = "") -> dict | None:
        slug = company_name.lower().replace(" ", "").replace(".", "").replace(",", "").replace("-", "").replace("'", "")
        found = {}

        # Phase 1a: scrape company website pages
        page_urls = self._build_page_urls(slug, known_url)
        for url in page_urls:
            result = await self._extract_page(url, company_name)
            if result:
                found.update(result)
                found["_source"] = "company_website"
            # Always regex-scan for emails
            emails = await self._scan_page_emails(url, slug)
            if emails:
                found.setdefault("emails", [])
                for e in emails:
                    if e not in found["emails"]:
                        found["emails"].append(e)
            if found.get("emails") or (found.get("contacts") and found["contacts"][0].get("email")):
                return found

        # Phase 1b: if we have the company URL domain, try LLM on homepage
        if known_url:
            result = await self._extract_page(known_url.rstrip("/"), company_name)
            if result:
                found.update(result)
                found["_source"] = "homepage"
            if found.get("emails"):
                return found

        # Phase 2: business directories + multi-platform search ──
        dir_queries = [
            f"site:crunchbase.com \"{company_name}\"",
            f"site:glassdoor.com \"{company_name}\"",
            f"site:yelp.com \"{company_name}\"",
            f"site:indeed.com \"{company_name}\"",
        ]
        for query in dir_queries:
            result = await self._search_and_extract(query, company_name, slug)
            if result:
                found.update(result)
                found["_source"] = "directory"
                if result.get("emails"):
                    found.setdefault("emails", [])
                    for e in result["emails"]:
                        if e not in found["emails"]:
                            found["emails"].append(e)
            if found.get("emails"):
                break

        # Phase 3: social platform discovery ──
        social_queries = [
            f"site:linkedin.com/in \"{company_name}\"",
            f"site:linkedin.com/company \"{company_name}\"",
            f"site:facebook.com \"{company_name}\" about",
            f"site:twitter.com \"{company_name}\" bio",
        ]
        for query in social_queries:
            urls = await _search_client.search(query, 5)
            for url in urls:
                emails = await self._scan_page_emails(url, slug)
                if emails:
                    found.setdefault("emails", [])
                    for e in emails:
                        if e not in found["emails"]:
                            found["emails"].append(e)
                if "linkedin.com" in url and "linkedin" not in found.setdefault("social", {}):
                    found["social"]["linkedin"] = url.split("?")[0]
            if found.get("emails"):
                break

        # Phase 4: google dork queries for contact info ──
        dork_queries = [
            f"\"{company_name}\" email OR contact",
            f"\"{company_name}\" \"@\" \"CEO\" OR \"CTO\" OR \"Founder\"",
            f"\"{company_name}\" \"@\" -jobs -recruiting",
        ]
        for query in dork_queries:
            urls = await _search_client.search(query, 5)
            for url in urls:
                emails = await self._scan_page_emails(url, slug)
                if emails:
                    found.setdefault("emails", [])
                    for e in emails:
                        if e not in found["emails"]:
                            found["emails"].append(e)
                result = await self._extract_page(url, company_name)
                if result:
                    found.update(result)
            if found.get("emails"):
                break

        # Phase 5: fallback
        if found.get("emails"):
            found["emails"] = self._validate_emails(found["emails"])
            if found["emails"] and not found.get("contacts"):
                found["contacts"] = [{"name": "Hiring Manager", "title": "", "email": found["emails"][0], "linkedin": "", "phone": ""}]

        return found if (found.get("emails") or (found.get("contacts") and found["contacts"][0].get("name"))) else None

    async def _quick_scrape(self, company_name: str, known_url: str) -> dict | None:
        root = self._get_root_url(known_url)
        if not root:
            return None
        found = {}
        urls = [root]
        for path in ["/team", "/about", "/contact"]:
            urls.append(f"{root}{path}")
        for url in urls[:4]:
            result = await self._extract_page(url, company_name)
            if result:
                found.update(result)
            if found.get("contacts") or found.get("emails"):
                break
        if found.get("contacts") and any(c.get("name") for c in found["contacts"]):
            found["emails"] = self._validate_emails(found.get("emails", []))
            return found
        if found.get("emails"):
            found["emails"] = self._validate_emails(found["emails"])
            return found
        return None

    def _build_page_urls(self, slug: str, known_url: str) -> list[str]:
        root = self._get_root_url(known_url)
        if root:
            result = [root]
            for path in ["/team", "/about", "/contact", "/company", "/about-us"]:
                result.append(f"{root}{path}")
            return result[:6]
        return [f"https://{slug}.com", f"https://www.{slug}.com"]

    async def _extract_page(self, url: str, company: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    return None
                soup = BeautifulSoup(resp.text, "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                if len(text) < 100:
                    return None
                if settings.openai_api_key or settings.anthropic_api_key:
                    try:
                        result = await llm.chat(
                            system=CONTACT_EXTRACT_PROMPT,
                            user=f"Company: {company}\nURL: {url}\n\nPage content:\n{text[:8000]}",
                        )
                        data = parse_llm_json(result)
                        if data and (data.get("contacts") or data.get("emails")):
                            logger.debug(f"LLM extracted data from {url}: {len(data.get('contacts',[]))} contacts, {len(data.get('emails',[]))} emails")
                            return data
                    except Exception as e:
                        logger.debug(f"LLM extraction failed for {url}: {e}")
                return self._extract_page_fallback(soup, text, company, url)
        except Exception:
            pass
        return None

    @staticmethod
    def _is_valid_name(name: str) -> bool:
        name = name.strip()
        if not name or len(name) < 5 or len(name) > 40:
            return False
        if not re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+", name):
            return False
        junk_names = {
            "Learn More", "Read More", "Get Started", "Contact Us", "Sign Up", "Subscribe",
            "View Details", "See More", "Click Here", "Watch Now", "Start Now",
            "Home", "About Us", "Services", "Search", "Login", "Register",
            "Banking Services", "Medical Assistant", "Software Engineer",
            "Full Name", "First Name", "Your Name", "Enter Name",
            "Our Team", "Our People", "Meet Our Team", "Meet The Team", "View All", "See All",
            "How It Works", "Get In Touch", "Our Services", "Our Company", "Careers At",
            "Join Us", "Work With Us", "Apply Now", "Book Demo", "Schedule Call",
            "Talk To Us", "Send Us", "Request Demo", "Our Partners", "Recent Posts",
            "Our Clients", "Case Studies", "Our Products", "Our Solutions", "Our Platform",
            "Our Technology", "White Papers", "Privacy Policy", "Terms Of Service",
            "All Rights Reserved", "Featured Posts", "Related Posts", "Popular Posts",
            "Related Articles", "Featured Articles", "Follow Us", "Stay Connected",
            "Company Overview", "Our Mission", "Our Vision", "Core Values",
            "Why Choose Us", "What We Do", "Who We Are", "Our Story",
            "Press Releases", "News Events", "Media Kit", "Contact Sales",
            "Customer Stories", "Success Stories",             "Data Science", "Machine Learning",
            "Artificial Intelligence", "Deep Learning", "Natural Language",
            "Computer Vision", "Predictive Analytics", "Business Intelligence",
            "Big Data", "Data Analytics", "Data Engineering", "Data Mining",
            "Statistical Analysis", "We Work",
            "Building Initiatives", "Gamification App", "Technology Report",
            "Data Science Team", "Analytics Team", "Data Team", "Engineering Team",
        }
        if name in junk_names:
            return False
        first_word = name.split()[0]
        if first_word in {"Learn", "Read", "Get", "View", "See", "Click", "Watch", "Start", "Enter",
                          "Our", "How", "Why", "What", "Who", "Where", "When", "Meet", "Join",
                          "Book", "Schedule", "Talk", "Send", "Request", "Apply", "Work",
                          "Follow", "Stay", "Press", "Media", "Customer", "Success", "Data",
                          "Machine", "Artificial", "Deep", "Natural", "Computer", "Predictive",
                          "Business", "Big", "Statistical", "Core", "Company", "Recent",
                          "Featured", "Related", "Popular", "Privacy", "Terms", "All"}:
            return False
        return True

    @staticmethod
    def _extract_page_fallback(soup, text: str, company: str, url: str) -> dict | None:
        contacts = []
        raw_emails = set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text))
        emails_found = set()
        for e in raw_emails:
            e = e.strip().strip(".'\",;:()[]")
            if not e or "example" in e.lower():
                continue
            if any(e.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".svg", ".ico", ".woff", ".ttf", ".eot")):
                continue
            local, at, domain_part = e.rpartition("@")
            if re.match(r'^\d+([.,]\d+)*$', domain_part) or ".." in domain_part:
                continue
            if re.match(r'^[0-9a-f]{6,}$', domain_part.replace(".", "")):
                continue
            if len(domain_part.split(".")) < 2 or len(domain_part) < 4:
                continue
            emails_found.add(e)

        role_keywords = r'CEO|CTO|CFO|COO|CMO|CAO|CRO|CIO|Founder|Co-Founder|Director|Manager|Engineer|Lead|Head|President|VP|SVP|EVP|Chief|Officer|Executive|Architect|Coordinator|Specialist|Consultant|Advisor|Partner|Owner|Principal|Developer|Designer|Analyst'
        name_patterns = [
            rf'([A-Z][a-z]+ [A-Z][a-z]+)\s*[–\-—|]\s*({role_keywords}[A-Za-z /,&]*)',
            rf'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n\s*({role_keywords}[A-Za-z /,&]*)',
            rf'({role_keywords})\s*[:\-–]\s*([A-Z][a-z]+ [A-Z][a-z]+)',
            rf'([A-Z][a-z]+ [A-Z][a-z]+),\s*({role_keywords}[A-Za-z /,&]*)',
        ]
        for pattern in name_patterns:
            try:
                for match in re.finditer(pattern, text):
                    g = match.groups()
                    is_role_first = g[0] in ("CEO","CTO","CFO","COO","CMO","CRO","Founder","Co-Founder","Director","Manager","President","VP","SVP","EVP","Chief","Head","Lead")
                    name = g[1] if is_role_first else g[0]
                    title = g[0] if is_role_first else g[1]
                    email = next((e for e in emails_found if name.split()[0].lower() in e.lower()), "")
                    name_stripped = name.strip()
                    if name_stripped and ContactFinderAgent._is_valid_name(name_stripped) and not any(c["name"] == name_stripped for c in contacts):
                        contacts.append({"name": name_stripped, "title": title.strip(), "email": email, "linkedin": "", "phone": ""})
            except Exception:
                pass

        # Pattern B: Extract names from HTML structure — look for name in headings near "team"
        team_sections = soup.find_all(["section", "div", "ul"], class_=re.compile(r"team|member|people|staff", re.I))
        if not team_sections:
            team_sections = soup.find_all("div", id=re.compile(r"team|member|people|staff", re.I))
        if not team_sections:
            headings = soup.find_all(["h1", "h2", "h3", "h4"])
            for h in headings:
                if re.search(r"team|our people|meet the|our team", h.get_text(strip=True), re.I):
                    team_sections = [h.parent] if h.parent else []
                    break

        for section in team_sections:
            names_in_section = section.find_all(["h3", "h4", "strong", "span"], class_=re.compile(r"name|member-name|person-name|title", re.I))
            if not names_in_section:
                names_in_section = section.find_all(["h3", "h4", "strong", "span"])
            for el in names_in_section:
                name_text = el.get_text(strip=True)
                if not name_text or len(name_text.split()) < 2:
                    continue
                if not re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', name_text):
                    continue
                if any(c["name"] == name_text for c in contacts):
                    continue
                # Look for nearby title
                title_text = ""
                siblings = list(el.find_next_siblings()) + list(el.parent.find_all(["p", "span", "small"])) if el.parent else []
                for sib in siblings:
                    st = sib.get_text(strip=True)
                    if re.match(role_keywords, st, re.I) and len(st) < 60:
                        title_text = st
                        break
                email = next((e for e in emails_found if name_text.split()[0].lower() in e.lower()), "")
                name_clean = name_text.strip()
                if ContactFinderAgent._is_valid_name(name_clean):
                    contacts.append({"name": name_clean, "title": title_text.strip(), "email": email, "linkedin": "", "phone": ""})

        for e in list(emails_found):
            if not any(c["email"] == e for c in contacts):
                contacts.append({"name": "", "title": "", "email": e, "linkedin": "", "phone": ""})

        social = {}
        li_match = re.search(r'(https?://(?:www\.)?linkedin\.com/[^\s"\'<>)]+)', text)
        if li_match:
            social["linkedin"] = li_match.group(1).split("?")[0]

        page_title = soup.find("title")
        desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})

        result = {
            "company": company,
            "industry": "",
            "contacts": contacts,
            "emails": list(emails_found),
            "social": social,
            "description": (desc.get("content","")[:300] if desc else page_title.get_text(strip=True)[:300] if page_title else ""),
        }
        return result if (contacts or emails_found) else None

    async def _scan_page_emails(self, url: str, slug: str) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    return []
                raw = set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', resp.text))
                valid = []
                for e in raw:
                    e = e.strip().strip(".'\",;:()[]")
                    if not e:
                        continue
                    if any(e.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot")):
                        continue
                    if any(x in e.lower() for x in ("example.com", "example.org", "domain.com", "wordpress", "noreply", "donotreply")):
                        continue
                    local, at, domain_part = e.rpartition("@")
                    if re.match(r'^\d+([.,]\d+)*$', domain_part):
                        continue
                    if ".." in domain_part:
                        continue
                    if re.match(r'^[0-9a-f]{6,}$', domain_part.replace(".", "")):
                        continue
                    if len(domain_part.split(".")) < 2 or len(domain_part) < 4:
                        continue
                    if slug and slug in e.lower().replace("-", "").replace(".", ""):
                        valid.append(e)
                    else:
                        valid.append(e)
                return list(dict.fromkeys(valid))[:10]
        except Exception:
            return []

    async def _search_and_extract(self, query: str, company: str, slug: str) -> dict | None:
        urls = await _search_client.search(query, 5)
        for url in urls:
            if any(skip in url for skip in ("facebook.com", "twitter.com", "instagram.com", "youtube.com", "reddit.com")):
                continue
            result = await self._extract_page(url, company)
            if result:
                return result
            emails = await self._scan_page_emails(url, slug)
            if emails:
                return {"emails": emails, "_source": f"search:{query[:30]}"}
        return None