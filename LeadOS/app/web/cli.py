import asyncio
import sys
import click
from pathlib import Path
from app.core.database import init_db

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def async_run(coro):
    async def _wrapped():
        try:
            return await coro
        finally:
            from app.core.database import engine
            await engine.dispose()
    return asyncio.run(_wrapped())


@click.group()
def cli():
    pass


@cli.command()
@click.argument("query", required=False)
@click.option("--category", "-c", type=click.Choice(
    ["general", "linkedin", "facebook", "twitter", "directories", "reddit", "social", "all"]
), default=None, help="Search a specific source category")
def search(query, category):
    """Search for companies to prospect"""
    init_db()
    async def _run():
        from app.discovery.web_search import WebSearchAgent, MultiScrapeAgent, SCRAPE_CATEGORIES
        if query:
            async with WebSearchAgent() as agent:
                await agent.run(custom_query=query)
        elif category and category != "all":
            async with WebSearchAgent() as agent:
                await agent.run_category(category)
        elif category == "all":
            async with MultiScrapeAgent() as agent:
                await agent.run()
        else:
            async with MultiScrapeAgent() as agent:
                await agent.run()
        click.echo("Search complete.")
    async_run(_run())


@cli.command()
def scrape_prospects():
    """Search all sources for potential client companies"""
    init_db()
    async def _run():
        from app.discovery.web_search import MultiScrapeAgent
        click.echo("  Searching for client companies...")
        async with MultiScrapeAgent() as agent:
            await agent.run()
        click.echo("Prospect discovery complete.")
    async_run(_run())


@cli.command()
def match():
    """Score, find contacts, and generate drafts"""
    init_db()
    async def _run():
        from app.matching.matcher import ProspectMatcherAgent
        async with ProspectMatcherAgent() as agent:
            await agent.run()
        click.echo("Finding decision-makers...")
        from app.discovery.contact_finder import ContactFinderAgent
        async with ContactFinderAgent() as agent:
            await agent.run()
        click.echo("Writing cold emails...")
        from app.outreach.outreach import OutreachAgent
        async with OutreachAgent() as agent:
            await agent.run()
        click.echo("Pipeline complete! Check 'ggh list drafts' or visit the dashboard.")
    async_run(_run())


@cli.command()
@click.option("--region", "-r", type=click.Choice(["bd", "global", "all"]), default="all", help="Region to focus on")
def research(region):
    """Find research collaborators (faculty, students, PhDs) for academic collaboration"""
    init_db()
    async def _run():
        from app.research.agent import ResearchDiscoveryAgent, ResearchMatcherAgent, ResearchOutreachAgent
        click.echo(f"  Searching for research collaborators ({region})...")
        bd_only = (region == "bd")
        async with ResearchDiscoveryAgent() as agent:
            await agent.run(bd_only=bd_only)
        click.echo("Scoring research leads...")
        async with ResearchMatcherAgent() as agent:
            await agent.run()
        click.echo("Generating outreach drafts...")
        async with ResearchOutreachAgent() as agent:
            await agent.run()
        click.echo("Research discovery complete! Visit /research/bd or /research/global on the dashboard.")
    async_run(_run())


@cli.command()
def serve():
    """Start the web dashboard"""
    from app.web.server import app
    click.echo("Starting dashboard at http://localhost:8000")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


@cli.command()
def stats():
    """Show database statistics"""
    init_db()
    async def _run():
        from app.core.database import async_session
        from app.core.models import Prospect, OutreachDraft
        from sqlalchemy import select, func
        async with async_session() as session:
            prospects = (await session.execute(select(func.count(Prospect.id)))).scalar()
            with_contacts = (await session.execute(
                select(func.count(Prospect.id)).where(Prospect.contact_name.isnot(None), Prospect.contact_name != "")
            )).scalar()
            drafts = (await session.execute(select(func.count(OutreachDraft.id)))).scalar()
        click.echo(f"Companies: {prospects}")
        click.echo(f"With Contacts: {with_contacts}")
        click.echo(f"Drafts: {drafts}")
    async_run(_run())


@cli.command()
@click.option("--name", prompt="Your name")
@click.option("--title", prompt="Your title")
@click.option("--summary", prompt="Brief summary")
@click.option("--skills", prompt="Skills (comma-separated)")
@click.option("--portfolio", prompt="Portfolio URLs (comma-separated)")
@click.option("--location", prompt="Your location", default="Remote")
@click.option("--experience", prompt="Years of experience", default=0, type=int)
def set_profile(name, title, summary, skills, portfolio, location, experience):
    """Set your freelancer profile"""
    init_db()
    async def _run():
        from app.core.database import async_session
        from app.core.models import UserProfile
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(select(UserProfile))
            profile = result.scalar_one_or_none()
            if not profile:
                profile = UserProfile()
                session.add(profile)
            profile.name = name
            profile.title = title
            profile.summary = summary
            profile.skills = [s.strip() for s in skills.split(",")]
            profile.portfolio_urls = [p.strip() for p in portfolio.split(",")]
            profile.location = location
            profile.experience_years = experience
            await session.commit()
        click.echo("Profile updated!")
    async_run(_run())


@cli.command()
@click.option("--format", "-f", type=click.Choice(["csv", "json"]), default="csv")
def export(format):
    """Export prospects as CSV (for Excel) or JSON"""
    init_db()
    async def _run():
        import csv, json as json_mod
        from app.core.database import async_session
        from app.core.models import Prospect, OutreachDraft
        from sqlalchemy import select
        from datetime import datetime
        output = Path("outputs")
        output.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        async with async_session() as session:
            prospects = (await session.execute(select(Prospect).order_by(Prospect.relevance_score.desc()))).scalars().all()

        if format == "csv":
            with open(output / f"prospects_{ts}.csv", "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Company", "Contact Name", "Contact Title", "Email", "LinkedIn", "Company URL", "Score", "Notes", "Source"])
                for p in prospects:
                    w.writerow([p.company_name, p.contact_name, p.contact_title, p.email,
                                p.linkedin_url, p.company_url, p.relevance_score,
                                (p.notes or "")[:200], p.source])
            click.echo(f"Exported {len(prospects)} prospects to outputs/prospects_{ts}.csv")
        else:
            with open(output / f"prospects_{ts}.json", "w") as f:
                json_mod.dump([{
                    "id": p.id, "company_name": p.company_name, "contact_name": p.contact_name,
                    "contact_title": p.contact_title, "email": p.email, "linkedin_url": p.linkedin_url,
                    "company_url": p.company_url, "source": p.source, "relevance_score": p.relevance_score,
                    "relevance_reason": p.relevance_reason, "status": p.status, "notes": (p.notes or "")[:500],
                    "contacts": p.contacts, "social_links": p.social_links
                } for p in prospects], f, indent=2, default=str)
            click.echo(f"Exported {len(prospects)} prospects to outputs/prospects_{ts}.json")
    async_run(_run())


@cli.command()
@click.argument("entity", type=click.Choice(["prospects", "drafts", "all"]))
def list(entity):
    """List prospects or drafts in a compact table format"""
    init_db()
    async def _run():
        from app.core.database import async_session
        from app.core.models import Prospect, OutreachDraft
        from sqlalchemy import select
        async with async_session() as session:
            if entity in ("prospects", "all"):
                result = await session.execute(select(Prospect).order_by(Prospect.relevance_score.desc()).limit(30))
                prospects = result.scalars().all()
                click.echo(f"\nProspects ({len(prospects)}):")
                click.echo("-" * 110)
                for p in prospects:
                    contact = p.contact_name or ""
                    email = p.email or ""
                    li = p.linkedin_url or ""
                    if contact or email:
                        click.echo(f"  [{p.relevance_score:>3}] {p.company_name[:35]:<35} {contact[:20]:<20} {email[:30]:<30} {li[:35]:<35}")
                    else:
                        click.echo(f"  [{p.relevance_score:>3}] {p.company_name[:60]:<60}")
            if entity in ("drafts", "all"):
                result = await session.execute(select(OutreachDraft).order_by(OutreachDraft.created_at.desc()).limit(20))
                drafts = result.scalars().all()
                click.echo(f"\nDrafts ({len(drafts)}):")
                click.echo("-" * 80)
                for d in drafts:
                    click.echo(f"  #{d.id:<4} {d.email_subject[:60]:<60} {d.status}")
    async_run(_run())


@cli.command()
def leads():
    """Show top prospects with full details for manual outreach"""
    init_db()
    async def _run():
        from app.core.database import async_session
        from app.core.models import Prospect
        from sqlalchemy import select
        async with async_session() as session:
            result = await session.execute(
                select(Prospect).where(Prospect.relevance_score >= 20)
                .order_by(Prospect.relevance_score.desc())
            )
            prospects = result.scalars().all()
        if not prospects:
            click.echo("No high-scoring prospects yet. Run: python -m app run-all")
            return
        for p in prospects:
            click.echo("=" * 70)
            click.echo(f"  Company:    {p.company_name}")
            click.echo(f"  Contact:    {p.contact_name or 'Hiring Manager'} ({p.contact_title or 'N/A'})")
            click.echo(f"  Email:      {p.email or 'N/A'}")
            click.echo(f"  LinkedIn:   {p.linkedin_url or 'N/A'}")
            click.echo(f"  Website:    {p.company_url or 'N/A'}")
            click.echo(f"  Score:      {p.relevance_score}/100")
            click.echo(f"  Reason:     {p.relevance_reason or 'N/A'}")
            notes = (p.notes or "")[:300]
            if notes:
                clean = notes.replace("\ufeff", "").encode("ascii", "replace").decode()
                click.echo(f"  Context:    {clean}")
            click.echo(f"  Source:     {p.source}")
        click.echo("=" * 70)
        click.echo(f"\nTotal hot leads: {len(prospects)}")
        click.echo("Export to CSV: ggh export")
    async_run(_run())
