import re
from app.core.base import BaseAgent, logger
from app.core.models import Prospect, UserProfile
from app.core.config import settings
from app.llm.client import llm
from app.llm.prompts import SKILL_MATCH
from app.llm.parser import parse_llm_json
from sqlalchemy import select


INDUSTRY_KEYWORDS = {
    "healthcare": ["health", "medical", "hospital", "clinic", "pharma", "biotech", "patient", "clinical"],
    "fintech": ["fintech", "finance", "banking", "insurance", "investment", "payments", "financial"],
    "ecommerce": ["ecommerce", "retail", "shop", "store", "product", "inventory", "customer"],
    "saas": ["saas", "software", "platform", "cloud", "api", "app", "subscription"],
    "real_estate": ["real estate", "property", "rental", "housing", "mortgage"],
    "logistics": ["logistics", "supply chain", "shipping", "transport", "delivery", "warehouse"],
    "marketing": ["marketing", "advertising", "seo", "social media", "content", "brand"],
    "education": ["education", "learning", "training", "course", "school", "university", "student"],
    "manufacturing": ["manufacturing", "factory", "production", "industrial", "supplier"],
}


class ProspectMatcherAgent(BaseAgent):
    async def run(self):
        profile = await self._get_profile()
        if not profile:
            logger.warning("No profile set — run 'ggh set-profile' first")
            return
        await self._score_prospects(profile)

    async def _get_profile(self):
        result = await self.session.execute(select(UserProfile))
        return result.scalar_one_or_none()

    async def _score_prospects(self, profile):
        result = await self.session.execute(
            select(Prospect).where(Prospect.relevance_score == 0)
        )
        prospects = result.scalars().all()
        kept = 0
        for prospect in prospects:
            score, reason = self._score_company(prospect, profile)
            if score < settings.match_threshold:
                await self.session.delete(prospect)
                continue
            prospect.relevance_score = score
            prospect.relevance_reason = reason
            kept += 1
        await self.session.commit()
        deleted = len(prospects) - kept
        logger.info(f"Matched {kept} companies, deleted {deleted} low-fit prospects")

    def _score_company(self, prospect: Prospect, profile) -> tuple:
        text = (
            f"{prospect.company_name} {prospect.industry or ''} "
            f"{prospect.notes or ''} {prospect.source_query or ''}"
        ).lower()

        profile_skills = [s.lower() for s in (profile.skills or [])]
        score = 30  # baseline for any real company

        # Industry fit — companies in analytics-heavy industries score higher
        detected_industry = None
        for industry, keywords in INDUSTRY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                detected_industry = industry
                score += 15
                break

        # Skill relevance — company mentions technologies you know
        for skill in profile_skills:
            if skill in text:
                score += 5

        # Company has contact info — real lead signal
        if prospect.contact_name:
            score += 20
        if prospect.email and "@" in prospect.email:
            score += 15
        if prospect.linkedin_url:
            score += 10

        # Company name length signals real business
        if len(prospect.company_name) > 5:
            score += 5

        # Known source gives credibility
        known_sources = {"crunchbase", "clutch", "linkedin", "goodfirms", "g2"}
        if prospect.source in known_sources:
            score += 10

        score = min(score, 100)

        # Build reason
        parts = []
        if prospect.company_name:
            parts.append(f"{prospect.company_name}")
        if detected_industry:
            parts.append(f"{detected_industry} industry")
        if prospect.contact_name:
            parts.append(f"contact: {prospect.contact_name}")
        if prospect.email:
            parts.append("has email")
        if prospect.linkedin_url:
            parts.append("has LinkedIn")

        reason = " — ".join(parts) if parts else "Potential client company"
        return score, reason
