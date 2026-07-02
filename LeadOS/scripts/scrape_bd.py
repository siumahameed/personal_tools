"""Run BD-only research scrape in the background.

Outputs to bd_scrape.log so the user can monitor progress.
Writes results directly to the SQLite DB. No need to touch the running server.
"""
import asyncio
import sys
import time
from pathlib import Path

LOG = Path(__file__).parent.parent / "logs" / "bd_scrape.log"


def log(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


async def main():
    LOG.write_text("", encoding="utf-8")
    log("BD research scrape starting...")
    log(f"Python: {sys.executable}")
    log("")

    from app.research.agent import ResearchDiscoveryAgent, ResearchMatcherAgent, ResearchOutreachAgent

    try:
        log("Step 1/3: Discovery (BD faculty + students only)")
        log("  - 28 BD queries (faculty + students)")
        log("  - ~5 URLs per query = ~140 pages to fetch")
        log("  - LLM extraction on each")
        log("  - This typically takes 3-5 minutes...")
        log("")
        async with ResearchDiscoveryAgent() as agent:
            await agent.run(bd_only=True)
        log("Step 1 done.")
        log("")

        log("Step 2/3: Scoring leads against your profile (statistics, ML, scikit-learn, etc.)")
        async with ResearchMatcherAgent() as agent:
            await agent.run()
        log("Step 2 done.")
        log("")

        log("Step 3/3: Generating outreach drafts for matched leads")
        async with ResearchOutreachAgent() as agent:
            await agent.run(min_score=30)
        log("Step 3 done.")
        log("")

        from app.core.database import async_session
        from app.core.models import ResearchLead
        from sqlalchemy import select, func
        async with async_session() as session:
            total = (await session.execute(select(func.count(ResearchLead.id)))).scalar()
            bd = (await session.execute(
                select(func.count(ResearchLead.id)).where(ResearchLead.region == "bangladesh")
            )).scalar()
            with_contact = (await session.execute(
                select(func.count(ResearchLead.id)).where(ResearchLead.contact_email != "")
            )).scalar()
            log(f"FINAL: {total} total research leads in DB")
            log(f"FINAL: {bd} Bangladesh-based leads")
            log(f"FINAL: {with_contact} with contact email")
        log("")
        log("Open http://127.0.0.1:8000/research/bd to see the results.")

    except Exception as e:
        import traceback
        log(f"FAILED: {e}")
        log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
