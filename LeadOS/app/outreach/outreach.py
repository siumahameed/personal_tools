from app.core.base import BaseAgent, logger
from app.core.models import Prospect, OutreachDraft, UserProfile
from app.core.config import settings
from app.llm.client import llm
from app.llm.prompts import OUTREACH_EMAIL
from app.llm.parser import parse_llm_json
from sqlalchemy import select


LINKEDIN_PROMPT = """You are a LinkedIn outreach specialist. Write a concise, professional LinkedIn message.

The freelancer:
- Name: {name}
- Title: {title}
- Skills: {skills}

Tone: Professional, concise, respectful. Max 300 characters.
Suggest a brief call or reply.

Return as JSON: {{"message": "..."}}"""


class OutreachAgent(BaseAgent):
    async def run(self):
        profile = await self._get_profile()
        if not profile:
            logger.warning("No user profile found — run 'ggh set-profile' first")
            return

        existing = await self.session.execute(select(OutreachDraft))
        for d in existing.scalars().all():
            await self.session.delete(d)
        await self.session.commit()

        await self._generate_for_prospects(profile)

    async def _get_profile(self):
        result = await self.session.execute(select(UserProfile))
        return result.scalar_one_or_none()

    async def _generate_for_prospects(self, profile):
        result = await self.session.execute(
            select(Prospect).where(Prospect.relevance_score >= settings.match_threshold)
        )
        prospects = result.scalars().all()
        total = 0

        for prospect in prospects:
            drafts = await self._generate_drafts(profile, prospect)
            for d in drafts:
                self.session.add(d)
                total += 1

        await self.session.commit()
        logger.info(f"Generated {total} draft(s) for {len(prospects)} prospects")

    async def _generate_drafts(self, profile, prospect) -> list:
        drafts = []
        try:
            skills_str = ", ".join(profile.skills or [])
            portfolio_str = ", ".join(profile.portfolio_urls or [])

            contacts = list(prospect.contacts or [])
            if not contacts:
                contacts = [{"name": prospect.contact_name or "", "title": prospect.contact_title or "", "email": prospect.email or ""}]

            seen_emails = set()
            for c in contacts:
                contact_name = c.get("name") or prospect.contact_name or ""
                contact_email = c.get("email") or prospect.email or ""

                if not contact_name and not contact_email:
                    continue
                if not contact_name and contact_email:
                    continue
                if contact_email in seen_emails:
                    continue
                if contact_email:
                    seen_emails.add(contact_email)

                contact_title = c.get("title") or prospect.contact_title or ""
                contact_linkedin = c.get("linkedin") or prospect.linkedin_url or ""
                display_name = contact_name or "Hiring Manager"

                if contact_name and (settings.openai_api_key or settings.anthropic_api_key):
                    email_data = await self._generate_email_llm(profile, prospect, display_name, contact_title, contact_email, contact_linkedin, skills_str, portfolio_str)
                else:
                    email_data = None
                if not email_data:
                    email_data = self._generate_email_fallback(profile, prospect, display_name, contact_title, skills_str, portfolio_str)

                if contact_name and (settings.openai_api_key or settings.anthropic_api_key):
                    li_data = await self._generate_linkedin_llm(profile, display_name, contact_title, skills_str)
                else:
                    li_data = None
                if not li_data:
                    li_data = {"message": self._generate_linkedin_fallback(profile, display_name, prospect.company_name)}

                drafts.append(OutreachDraft(
                    prospect_id=prospect.id,
                    email_subject=email_data.get("subject", ""),
                    email_body=email_data.get("email_body", ""),
                    linkedin_message=li_data.get("message", ""),
                ))
        except Exception as e:
            logger.error(f"Draft generation failed for {prospect.company_name}: {e}")
        return drafts

    async def _generate_email_llm(self, profile, prospect, contact_name, contact_title, contact_email, contact_linkedin, skills_str, portfolio_str):
        if not (settings.openai_api_key or settings.anthropic_api_key):
            return None
        try:
            result = await llm.chat(
                system=OUTREACH_EMAIL.format(
                    name=profile.name or "Freelancer",
                    title=profile.title or "Freelancer",
                    location=profile.location or "Remote",
                    skills=skills_str,
                    portfolio_urls=portfolio_str,
                ),
                user=f"Company: {prospect.company_name}\nContact Person: {contact_name}\nContact Title: {contact_title}\nContact Email: {contact_email}\nContact LinkedIn: {contact_linkedin}\nNotes: {(prospect.notes or '')[:500]}",
            )
            return parse_llm_json(result)
        except Exception:
            return None

    async def _generate_linkedin_llm(self, profile, contact_name, contact_title, skills_str):
        if not (settings.openai_api_key or settings.anthropic_api_key):
            return None
        try:
            result = await llm.chat(
                system=LINKEDIN_PROMPT.format(
                    name=profile.name or "Freelancer",
                    title=profile.title or "Freelancer",
                    skills=skills_str,
                ),
                user=f"Contact: {contact_name} ({contact_title})",
            )
            return parse_llm_json(result)
        except Exception:
            return None

    @staticmethod
    def _generate_email_fallback(profile, prospect, contact_name, contact_title, skills_str, portfolio_str):
        name = profile.name or "Freelancer"
        location = profile.location or "Remote"
        skills_list = skills_str[:120]
        portfolio_list = portfolio_str[:200]

        subject = f"Data analysis & ML support for {prospect.company_name}"

        body = f"""Hi {contact_name},

I'm {name}, a {profile.title or 'Data Analyst'} based in {location}.

I help businesses like {prospect.company_name} turn data into actionable insights — from building ML models with Scikit-learn to creating interactive dashboards and automating reporting workflows.

Some relevant skills: {skills_list}

I'd love to discuss how I can support your team. Are you available for a quick call this week?

Best,
{name}
{portfolio_list}"""

        return {"subject": subject, "email_body": body}

    @staticmethod
    def _generate_linkedin_fallback(profile, contact_name, company):
        name = profile.name or "Freelancer"
        return f"Hi {contact_name}, I'm {name} — a data analyst/ML engineer. I help companies like {company} with data analysis, ML models, and reporting. Would love to connect and explore how I can help your team."
