"""Quick dry-run with debug logging."""
import asyncio
import logging
import sys
import time
from pathlib import Path

LOG = Path(__file__).parent.parent / "logs" / "dry_run.log"


def log(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


async def main():
    LOG.write_text("", encoding="utf-8")
    # enable debug logging
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

    log("Dry run starting — 1 query with debug logging")

    from app.research.agent import ResearchDiscoveryAgent
    from app.core.database import async_session
    from app.core.models import ResearchLead
    from sqlalchemy import select, func

    queries = [
        "Bangladesh statistics professor researchgate",
    ]

    try:
        async with ResearchDiscoveryAgent() as agent:
            for q in queries:
                log(f"Running: {q}")
                await agent.run(custom_query=q)
        log("Done.")
    except Exception as e:
        import traceback
        log(f"FAILED: {e}")
        log(traceback.format_exc())
        sys.exit(1)

    async with async_session() as session:
        total = (await session.execute(select(func.count(ResearchLead.id)))).scalar()
        log(f"FINAL: {total} leads in DB")


if __name__ == "__main__":
    asyncio.run(main())
