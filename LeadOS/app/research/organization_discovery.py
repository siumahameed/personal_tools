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
from app.core.models import ResearchOrganization, ScrapeSession, UserProfile
from app.discovery.search_client import SearchClient
from app.llm.client import llm
from app.llm.parser import parse_llm_json
from app.llm.prompts import RESEARCH_ORG_EXTRACT


_search_client = SearchClient()


ORG_SCRAPE_CATEGORIES = [
    "bd_agriculture", "bd_health_medical", "bd_economics_policy",
    "bd_engineering_tech", "bd_funding_opportunities", "bd_innovation_incubation",
]


class ResearchOrgDiscoveryAgent(BaseAgent):
    """Discover Bangladeshi research organizations and institutes
    that offer opportunities for external collaborators.

    Searches queries from organization_queries.yml, fetches pages,
    extracts org info via LLM, and stores good leads.
    """

    async def run(self):
        queries = self._load_queries()
        if not queries:
            logger.warning("  [research-org] No organization queries found")
            return
        await self._process_queries(queries)

    def _load_queries(self) -> list[str]:
        path = Path(__file__).parent / "organization_queries.yml"
        if not path.exists():
            return []
        with open(path) as f:
            data = yaml.safe_load(f)
        cats = data.get("categories", {})
        return [q for cat_list in cats.values() for q in cat_list]

    async def _process_queries(self, queries: list[str]):
        if not queries:
            return
        total = len(queries)
        for idx, query in enumerate(queries, 1):
            logger.info(f"  [research-org] Search [{idx}/{total}]: {query}")
            try:
                await self._run_query(query)
            except Exception as e:
                logger.error(f"  [research-org] Query failed ({query[:60]}): {e}")

    async def _run_query(self, query: str):
        urls = await _search_client.search(
            query, settings.max_search_results, "",
        )
        if not urls:
            logger.info(f"  [research-org] 0 URLs for: {query[:50]}")
            return

        sem = asyncio.Semaphore(6)
        async def _fetch(u: str) -> tuple[str, str | None]:
            async with sem:
                return u, await self._fetch_page(u)

        fetch_results = await asyncio.gather(*[_fetch(u) for u in urls])
        fetched = [(u, html) for u, html in fetch_results if html]

        accepted = 0
        for url, html in fetched:
            try:
                info = await self._extract_organization(html, url, query)
            except Exception as e:
                logger.debug(f"  [research-org] extract failed for {url[:80]}: {e}")
                continue
            if not info:
                continue
            if not info.get("is_organization"):
                continue
            name = info.get("name", "").strip()
            if not name or len(name) < 5:
                continue
            async with db_write_lock:
                async with async_session() as session:
                    await self._store_organization(session, info, query, url)
                    await session.commit()
            accepted += 1
            logger.info(f"  [research-org]   + {name}")

        async with db_write_lock:
            async with async_session() as session:
                session.add(ScrapeSession(
                    source="research_org_discovery",
                    query=query,
                    urls_found=len(urls),
                    prospects_found=accepted,
                    status="completed",
                ))
                await session.commit()
        logger.info(f"  [research-org] {accepted} org(s) from: {query[:50]}")

    async def _fetch_page(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ResearchOrgDiscovery/1.0)",
                    "Accept": "text/html,application/xhtml+xml",
                })
                if resp.status_code == 200 and "text/html" in (resp.headers.get("content-type", "").lower()):
                    return resp.text[:150_000]
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
        return None

    async def _extract_organization(self, content: str, url: str, query: str) -> dict | None:
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        if len(text) < 80:
            return None

        domain = urlparse(url).netloc.replace("www.", "")

        if settings.openai_api_key or settings.anthropic_api_key:
            try:
                response = await llm.chat(
                    system=RESEARCH_ORG_EXTRACT,
                    user=(
                        f"URL: {url}\nDomain: {domain}\nQuery: {query}\n\n"
                        f"Page content:\n{text[:8000]}"
                    ),
                    temperature=0.1,
                )
                data = parse_llm_json(response)
            except Exception as e:
                logger.debug(f"  [research-org] LLM extraction failed: {e}")
                return None
        else:
            return None

        if not isinstance(data, dict):
            return None
        return data

    async def _store_organization(self, session, info: dict, query: str, url: str):
        name = info.get("name", "").strip()
        if not name:
            return

        website = info.get("website", "").strip() or url
        existing = await session.execute(
            select(ResearchOrganization).where(
                (ResearchOrganization.website == website) |
                ((ResearchOrganization.name == name) & (ResearchOrganization.country == info.get("country", "Bangladesh")))
            )
        )
        if existing.scalar_one_or_none():
            logger.debug(f"  [research-org]   duplicate: {name}")
            return

        org = ResearchOrganization(
            name=name,
            acronym=(info.get("acronym") or "").strip(),
            description=(info.get("description") or "")[:1000],
            website=website,
            country=info.get("country", "Bangladesh"),
            research_areas=info.get("research_areas", []),
            opportunity_types=info.get("opportunity_types", []),
            application_url=(info.get("application_url") or "").strip(),
            contact_email=(info.get("contact_email") or "").strip(),
            contact_phone=(info.get("contact_phone") or "").strip(),
            social_links=info.get("social_links", {}),
            source="research_org_discovery",
            source_query=query,
            relevance_score=80 if info.get("has_opportunities_for_outsiders") else 50,
            status="new",
        )
        session.add(org)


class ResearchOrgMatcherAgent(BaseAgent):
    """Score research organizations for fit with the user's skills."""

    async def run(self):
        async with async_session() as session:
            result = await session.execute(
                select(ResearchOrganization).where(ResearchOrganization.relevance_score == 0)
            )
            orgs = result.scalars().all()

        if not orgs:
            logger.info("  [research-org] No un-scored organizations found")
            return

        profile = await self._get_profile()

        for org in orgs:
            score = self._score_org(org, profile)
            async with db_write_lock:
                async with async_session() as session:
                    db_org = await session.get(ResearchOrganization, org.id)
                    if db_org:
                        db_org.relevance_score = score["score"]
                        db_org.relevance_reason = score["reason"]
                        db_org.why_good_fit = score["why_good_fit"]
                        await session.commit()
            logger.info(f"  [research-org] scored {org.name}: {score['score']}/100")

    async def _get_profile(self) -> UserProfile | None:
        async with async_session() as session:
            result = await session.execute(select(UserProfile))
            return result.scalar_one_or_none()

    def _score_org(self, org: ResearchOrganization, profile: UserProfile | None) -> dict:
        score = 30
        reasons = []
        skills = [s.lower() for s in (profile.skills if profile and profile.skills else [])]
        areas = [a.lower() for a in (org.research_areas or [])]
        opp_types = [o.lower() for o in (org.opportunity_types or [])]

        if org.contact_email:
            score += 15
            reasons.append("Has contact email")

        if org.application_url:
            score += 10
            reasons.append("Has application portal")

        skill_overlap = [s for s in skills if any(s in a for a in areas)]
        if skill_overlap:
            score += min(len(skill_overlap) * 8, 25)
            reasons.append(f"Skill overlap: {', '.join(skill_overlap[:3])}")

        if any("fellowship" in o or "internship" in o or "assistant" in o for o in opp_types):
            score += 10
            reasons.append("Has fellowship/internship/RA opportunities")

        if any("data" in a or "statist" in a or "machine learning" in a for a in areas):
            score += 10
            reasons.append("Aligns with data/ML/statistics")

        score = min(score, 100)
        why = f"This organization's work in {', '.join(areas[:3])} aligns with your skills in {', '.join(skill_overlap[:3])}." if skill_overlap else f"The organization works in {', '.join(areas[:3])}."
        if org.application_url:
            why += f" Opportunities can be found at: {org.application_url}"

        return {
            "score": score,
            "reason": " | ".join(reasons[:5]) if reasons else "Basic match",
            "why_good_fit": why,
        }
