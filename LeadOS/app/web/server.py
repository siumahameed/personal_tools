import asyncio
import sys
import time
from datetime import datetime
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from app.core.database import init_db, get_session
from app.core.models import Prospect, OutreachDraft, ResearchLead, UserProfile

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI(title="leadOS — Client Prospecting")

templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(templates_dir))

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

task_status: dict = {"current": None, "history": []}

def _set_task(name: str, status: str, message: str = ""):
    task_status["current"] = {
        "name": name, "status": status, "message": message,
        "started_at": datetime.utcnow().isoformat() if status == "running" else task_status.get("current", {}).get("started_at"),
        "finished_at": datetime.utcnow().isoformat() if status in ("completed", "failed") else None,
    }
    if status in ("completed", "failed"):
        task_status["history"].insert(0, dict(task_status["current"]))
        task_status["history"] = task_status["history"][:10]


@app.on_event("startup")
async def startup():
    init_db()
    from app.core.database import async_session
    async with async_session() as session:
        await _seed_user_profile(session)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    total_prospects = (await session.execute(select(func.count(Prospect.id)))).scalar() or 0
    total_drafts = (await session.execute(select(func.count(OutreachDraft.id)))).scalar() or 0
    total_research = (await session.execute(select(func.count(ResearchLead.id)))).scalar() or 0
    manual_research = (await session.execute(
        select(func.count(ResearchLead.id)).where(ResearchLead.source == "manual_import")
    )).scalar() or 0
    bd_research = (await session.execute(
        select(func.count(ResearchLead.id)).where(ResearchLead.region == "bangladesh")
    )).scalar() or 0
    global_research = total_research - bd_research
    profile = (await session.execute(select(UserProfile))).scalar_one_or_none()

    recent_prospects = (await session.execute(
        select(Prospect).order_by(Prospect.created_at.desc()).limit(5)
    )).scalars().all()
    with_contacts = (await session.execute(
        select(func.count(Prospect.id)).where(Prospect.contact_name.isnot(None)).where(Prospect.contact_name != "")
    )).scalar() or 0

    source_rows = (await session.execute(
        select(Prospect.source, func.count(Prospect.id))
        .group_by(Prospect.source)
        .order_by(func.count(Prospect.id).desc())
    )).all()
    source_total = sum(r[1] for r in source_rows) or 1
    source_colors = {
        "linkedin": ("bg-blue-500", "bg-blue-500"),
        "crunchbase": ("bg-purple-500", "bg-purple-500"),
        "clutch": ("bg-emerald-500", "bg-emerald-500"),
        "goodfirms": ("bg-amber-500", "bg-amber-500"),
        "g2": ("bg-cyan-500", "bg-cyan-500"),
        "reddit": ("bg-orange-500", "bg-orange-500"),
        "facebook": ("bg-indigo-500", "bg-indigo-500"),
        "twitter": ("bg-sky-500", "bg-sky-500"),
        "web_search": ("bg-surface-500", "bg-surface-500"),
    }
    source_stats = []
    for source, count in source_rows:
        c = source_colors.get(source, ("bg-surface-500", "bg-surface-500"))
        source_stats.append({
            "name": source.replace("_", " ").title(),
            "count": count,
            "pct": round(count / source_total * 100),
            "color": c[0],
            "bar": c[1],
        })

    return templates.TemplateResponse(request, "dashboard.html", {
        "stats": {
            "total_prospects": total_prospects,
            "total_drafts": total_drafts,
            "with_contacts": with_contacts,
            "total_research": total_research,
            "bd_research": bd_research,
            "global_research": global_research,
            "manual_research": manual_research,
        },
        "source_stats": source_stats,
        "recent_prospects": recent_prospects,
        "profile": profile,
        "task_status": task_status["current"],
        "task_history": task_status["history"],
    })


@app.get("/prospects", response_class=HTMLResponse)
async def prospects_page(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Prospect).order_by(Prospect.relevance_score.desc()))
    prospects = result.scalars().all()
    return templates.TemplateResponse(request, "prospects.html", {
        "prospects": prospects,
    })


@app.get("/drafts", response_class=HTMLResponse)
async def drafts_page(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(OutreachDraft).order_by(OutreachDraft.created_at.desc()))
    drafts = result.scalars().all()
    return templates.TemplateResponse(request, "drafts.html", {"drafts": drafts})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, session: AsyncSession = Depends(get_session)):
    profile = (await session.execute(select(UserProfile))).scalar_one_or_none()
    return templates.TemplateResponse(request, "settings.html", {"profile": profile})


@app.get("/api/stats")
async def api_stats(session: AsyncSession = Depends(get_session)):
    total_prospects = (await session.execute(select(func.count(Prospect.id)))).scalar() or 0
    return {"total_prospects": total_prospects}


@app.get("/api/task-status")
async def api_task_status():
    return task_status


@app.get("/api/drafts")
async def api_drafts(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(OutreachDraft).order_by(OutreachDraft.created_at.desc()).limit(50))
    return [{
        "id": d.id, "prospect_id": d.prospect_id,
        "email_subject": d.email_subject, "email_body": d.email_body,
        "linkedin_message": d.linkedin_message, "channel": d.channel,
        "status": d.status, "created_at": str(d.created_at or ""),
    } for d in result.scalars().all()]


@app.get("/api/prospects")
async def api_prospects(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Prospect).order_by(Prospect.relevance_score.desc()).limit(100))
    return [{
        "id": p.id, "company_name": p.company_name, "contact_name": p.contact_name,
        "email": p.email, "linkedin_url": p.linkedin_url, "company_url": p.company_url,
        "source": p.source, "relevance_score": p.relevance_score,
        "relevance_reason": p.relevance_reason, "status": p.status,
        "notes": p.notes[:200] if p.notes else "", "created_at": str(p.created_at or ""),
        "contacts": p.contacts or [], "social_links": p.social_links or {},
    } for p in result.scalars().all()]


@app.get("/api/profile")
async def api_profile(session: AsyncSession = Depends(get_session)):
    profile = (await session.execute(select(UserProfile))).scalar_one_or_none()
    if not profile:
        return {}
    return {
        "name": profile.name, "title": profile.title, "summary": profile.summary,
        "skills": profile.skills, "portfolio_urls": profile.portfolio_urls,
        "experience_years": profile.experience_years, "location": profile.location,
        "preferred_roles": profile.preferred_roles,
    }


@app.post("/api/run/search")
async def api_run_search():
    _set_task("Discover", "running", "Searching for companies...")
    async def task():
        try:
            from app.discovery.web_search import MultiScrapeAgent
            async with MultiScrapeAgent() as agent:
                await agent.run()
            _set_task("Discover", "completed", "Discovery complete")
        except Exception as e:
            _set_task("Discover", "failed", str(e))
    asyncio.create_task(task())
    return JSONResponse({"status": "started", "message": "Searching for companies to prospect..."})


async def _seed_user_profile(session):
    profile = (await session.execute(select(UserProfile))).scalar_one_or_none()
    if not profile:
        profile = UserProfile()
        session.add(profile)
    profile.name = "Sium Ahameed"
    profile.title = "Machine Learning Engineer & Data Analyst"
    profile.summary = "Statistics graduate with strong foundation in statistical modeling and data analysis. Skilled in building predictive models with Scikit-learn, data visualization, and FastAPI web applications. Based in Dhaka, Bangladesh."
    profile.skills = ["Python", "Scikit-learn", "Pandas", "NumPy", "Matplotlib", "Seaborn", "Plotly", "FastAPI", "SQL", "Statistics", "NLTK", "Data Visualization", "Exploratory Data Analysis", "Classification", "Regression", "Clustering"]
    profile.portfolio_urls = ["https://siumahameed.github.io/portfolio/", "https://github.com/siumahameed", "https://www.linkedin.com/in/sium11/"]
    profile.location = "Dhaka, Bangladesh"
    profile.experience_years = 2
    profile.preferred_roles = ["Data Analyst", "ML Engineer (Scikit-learn)", "Data Visualization", "FastAPI Developer", "Business Intelligence", "Statistical Analysis"]
    await session.commit()


@app.post("/api/run/score")
async def api_run_score():
    _set_task("Score", "running", "Scoring companies...")
    async def task():
        try:
            from app.matching.matcher import ProspectMatcherAgent
            async with ProspectMatcherAgent() as agent:
                await agent.run()
            _set_task("Score", "completed", "Scoring complete")
        except Exception as e:
            _set_task("Score", "failed", str(e))
    asyncio.create_task(task())
    return JSONResponse({"status": "started", "message": "Scoring companies against your skills..."})


@app.post("/api/run/generate")
async def api_run_generate():
    _set_task("Generate Drafts", "running", "Writing cold emails...")
    async def task():
        try:
            from app.outreach.outreach import OutreachAgent
            async with OutreachAgent() as agent:
                await agent.run()
            _set_task("Generate Drafts", "completed", "Drafts ready")
        except Exception as e:
            _set_task("Generate Drafts", "failed", str(e))
    asyncio.create_task(task())
    return JSONResponse({"status": "started", "message": "Writing cold emails..."})


@app.post("/api/run/find-contacts")
async def api_run_find_contacts():
    _set_task("Find Contacts", "running", "Finding contacts...")
    async def task():
        try:
            from app.discovery.contact_finder import ContactFinderAgent
            async with ContactFinderAgent() as agent:
                await agent.run()
            _set_task("Find Contacts", "completed", "Contacts found")
        except Exception as e:
            _set_task("Find Contacts", "failed", str(e))
    asyncio.create_task(task())
    return JSONResponse({"status": "started", "message": "Finding decision-makers..."})


@app.post("/api/run/pipeline")
async def api_run_pipeline():
    _set_task("Pipeline", "running", "Step 1/4: Discovering companies...")
    async def task():
        try:
            from app.discovery.web_search import MultiScrapeAgent
            async with MultiScrapeAgent() as agent:
                await agent.run()
            _set_task("Pipeline", "running", "Step 2/4: Scoring companies...")
            from app.matching.matcher import ProspectMatcherAgent
            async with ProspectMatcherAgent() as agent:
                await agent.run()
            _set_task("Pipeline", "running", "Step 3/4: Finding contacts...")
            from app.discovery.contact_finder import ContactFinderAgent
            async with ContactFinderAgent() as agent:
                await agent.run()
            _set_task("Pipeline", "running", "Step 4/4: Writing drafts...")
            from app.outreach.outreach import OutreachAgent
            async with OutreachAgent() as agent:
                await agent.run()
            _set_task("Pipeline", "completed", "All done!")
        except Exception as e:
            _set_task("Pipeline", "failed", str(e))
    asyncio.create_task(task())
    return JSONResponse({"status": "started", "message": "Pipeline started — discovering companies, scoring, and finding contacts..."})


@app.post("/api/cleanup/fakes")
async def api_cleanup_fakes(session: AsyncSession = Depends(get_session)):
    """Delete prospects whose company name is a generic social/platform name (fakes)."""
    from app.discovery.web_search import GENERIC_COMPANY_NAMES
    from sqlalchemy import delete

    generic_pattern = [n.title() for n in GENERIC_COMPANY_NAMES] + [n.lower() for n in GENERIC_COMPANY_NAMES]
    deleted = 0
    for name in GENERIC_COMPANY_NAMES:
        result = await session.execute(
            delete(Prospect).where(
                (Prospect.company_name.ilike(name)) |
                (Prospect.company_name.ilike(name.title())) |
                (Prospect.company_name.ilike(name.upper()))
            )
        )
        deleted += result.rowcount or 0
    await session.commit()
    return {"status": "ok", "deleted": deleted, "message": f"Removed {deleted} fake prospects"}


@app.get("/research/bd", response_class=HTMLResponse)
async def research_bd_page(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(ResearchLead)
        .where(ResearchLead.region == "bangladesh")
        .order_by(ResearchLead.relevance_score.desc())
    )
    leads = result.scalars().all()
    return templates.TemplateResponse(request, "research_bd.html", {
        "leads": leads,
        "region_label": "Bangladesh",
    })


@app.get("/research/global", response_class=HTMLResponse)
async def research_global_page(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(ResearchLead)
        .where(ResearchLead.region != "bangladesh")
        .order_by(ResearchLead.relevance_score.desc())
    )
    leads = result.scalars().all()
    return templates.TemplateResponse(request, "research_global.html", {
        "leads": leads,
        "region_label": "Worldwide",
    })


@app.get("/api/research/leads")
async def api_research_leads(
    region: str = "",
    min_score: int = 0,
    session: AsyncSession = Depends(get_session),
):
    q = select(ResearchLead)
    if region:
        q = q.where(ResearchLead.region == region)
    if min_score > 0:
        q = q.where(ResearchLead.relevance_score >= min_score)
    result = await session.execute(q.order_by(ResearchLead.relevance_score.desc()).limit(200))
    return [{
        "id": r.id, "name": r.name, "title": r.title,
        "institution": r.institution, "department": r.department,
        "country": r.country, "region": r.region,
        "office_address": r.office_address or "",
        "current_fields": r.current_fields or [],
        "past_fields": r.past_fields or [],
        "research_fields": r.research_fields or [],
        "recent_papers": r.recent_papers or [],
        "bio": r.bio,
        "contact_email": r.contact_email,
        "all_emails": r.all_emails or [],
        "contact_phone": r.contact_phone or "",
        "personal_website": r.personal_website or "",
        "linkedin_url": r.linkedin_url,
        "twitter_url": r.twitter_url or "",
        "github_url": r.github_url or "",
        "google_scholar_url": r.google_scholar_url or "",
        "orcid_url": r.orcid_url or "",
        "researchgate_url": r.researchgate_url or "",
        "profile_url": r.profile_url,
        "source": r.source, "relevance_score": r.relevance_score,
        "relevance_reason": r.relevance_reason, "why_good_fit": r.why_good_fit,
        "outreach_draft": r.outreach_draft, "status": r.status,
        "created_at": str(r.created_at or ""),
    } for r in result.scalars().all()]


@app.post("/api/run/research")
async def api_run_research(bd_only: bool = False):
    label = "Bangladesh" if bd_only else "Global"
    _set_task("Research Discovery", "running", f"Finding {label} research collaborators...")
    async def task():
        try:
            from app.research.agent import ResearchDiscoveryAgent, ResearchMatcherAgent, ResearchOutreachAgent
            async with ResearchDiscoveryAgent() as agent:
                await agent.run(bd_only=bd_only)
            async with ResearchMatcherAgent() as agent:
                await agent.run()
            async with ResearchOutreachAgent() as agent:
                await agent.run()
            _set_task("Research Discovery", "completed", "Research leads updated")
        except Exception as e:
            _set_task("Research Discovery", "failed", str(e))
    asyncio.create_task(task())
    return JSONResponse({"status": "started", "message": f"Searching for {label} research collaborators..."})


@app.post("/api/research/import-csv")
async def api_import_research_csv():
    """Import manually collected researchers from CSV on disk."""
    import csv
    from pathlib import Path
    csv_path = Path(__file__).parent.parent.parent / "It's Sium - DS & RE.csv"
    if not csv_path.exists():
        return JSONResponse({"status": "error", "message": "CSV file not found at: " + str(csv_path)})

    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    imported = 0
    skipped = 0
    for row in rows:
        name = (row.get("Name") or "").strip()
        if not name:
            skipped += 1
            continue
        email = (row.get("Email") or "").strip()
        linkedin = (row.get("LinkdIn") or "").strip()
        phone = (row.get("Phone") or "").strip()
        institution = (row.get("University") or "").strip()
        extra = (row.get("Extra info") or "").strip()

        if linkedin and not linkedin.startswith("http"):
            linkedin = "https://www." + linkedin
        all_emails = [email] if email else []
        bio = extra[:600] if extra else ""

        from app.core.database import async_session, db_write_lock
        from sqlalchemy import select
        async with db_write_lock:
            async with async_session() as session:
                if email:
                    existing = (await session.execute(
                        select(ResearchLead).where(ResearchLead.contact_email == email)
                    )).scalar_one_or_none()
                    if existing:
                        skipped += 1
                        continue
                if linkedin:
                    existing = (await session.execute(
                        select(ResearchLead).where(ResearchLead.linkedin_url == linkedin)
                    )).scalar_one_or_none()
                    if existing:
                        skipped += 1
                        continue
                lead = ResearchLead(
                    name=name[:200], institution=institution[:200],
                    contact_email=email[:200] if email else "",
                    all_emails=all_emails,
                    contact_phone=phone[:50] if phone else "",
                    linkedin_url=linkedin[:500] if linkedin else "",
                    bio=bio, source="manual_import", source_query="manual_csv_import",
                    relevance_score=60, region="bangladesh", country="Bangladesh", status="new",
                )
                session.add(lead)
                await session.commit()
                imported += 1
    return JSONResponse({
        "status": "ok",
        "imported": imported,
        "skipped": skipped,
        "message": f"Imported {imported} researchers, skipped {skipped} duplicates"
    })


@app.post("/api/research/generate-outreach")
async def api_generate_research_outreach(session: AsyncSession = Depends(get_session)):
    """Generate outreach drafts for high-scoring research leads."""
    from app.research.agent import ResearchOutreachAgent
    async with ResearchOutreachAgent() as agent:
        await agent.run(min_score=30)
    result = await session.execute(
        select(ResearchLead).where(ResearchLead.outreach_draft != "").limit(1)
    )
    return {"status": "ok", "message": "Outreach drafts generated"}


@app.post("/api/profile/update")
async def api_profile_update(data: dict, session: AsyncSession = Depends(get_session)):
    profile = (await session.execute(select(UserProfile))).scalar_one_or_none()
    if not profile:
        profile = UserProfile()
        session.add(profile)
    if "name" in data:
        profile.name = data["name"]
    if "title" in data:
        profile.title = data["title"]
    if "summary" in data:
        profile.summary = data["summary"]
    if "location" in data:
        profile.location = data["location"]
    if "experience_years" in data:
        profile.experience_years = int(data["experience_years"])
    if "skills" in data:
        profile.skills = [s.strip() for s in data["skills"].split(",") if s.strip()]
    if "portfolio_urls" in data:
        profile.portfolio_urls = [p.strip() for p in data["portfolio_urls"].split(",") if p.strip()]
    if "preferred_roles" in data:
        profile.preferred_roles = [r.strip() for r in data["preferred_roles"].split(",") if r.strip()]
    await session.commit()
    return {"status": "ok", "message": "Profile updated"}


@app.get("/api/prospects/filter")
async def api_prospects_filter(
    source: str = "",
    status: str = "",
    min_score: int = 0,
    search: str = "",
    session: AsyncSession = Depends(get_session),
):
    q = select(Prospect)
    if source:
        q = q.where(Prospect.source == source)
    if status:
        q = q.where(Prospect.status == status)
    if min_score > 0:
        q = q.where(Prospect.relevance_score >= min_score)
    if search:
        q = q.where(or_(Prospect.company_name.ilike(f"%{search}%"), Prospect.notes.ilike(f"%{search}%")))
    result = await session.execute(q.order_by(Prospect.relevance_score.desc()).limit(100))
    return [{
        "id": p.id, "company_name": p.company_name, "contact_name": p.contact_name,
        "email": p.email, "linkedin_url": p.linkedin_url, "company_url": p.company_url,
        "source": p.source, "relevance_score": p.relevance_score,
        "relevance_reason": p.relevance_reason, "status": p.status,
        "notes": p.notes[:200] if p.notes else "", "created_at": str(p.created_at or ""),
        "contacts": p.contacts or [],
    } for p in result.scalars().all()]


@app.get("/api/export/csv")
async def api_export_csv(session: AsyncSession = Depends(get_session)):
    import csv, io
    result = await session.execute(
        select(Prospect).where(Prospect.relevance_score >= 20)
        .order_by(Prospect.relevance_score.desc())
    )
    prospects = result.scalars().all()

    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["Company", "Contact Name", "Contact Title", "Email", "LinkedIn", "Website", "Score", "Notes", "Source"])
    for p in prospects:
        w.writerow([p.company_name, p.contact_name, p.contact_title, p.email,
                    p.linkedin_url, p.company_url, p.relevance_score,
                    (p.notes or "")[:200], p.source])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=prospects.csv"},
    )
