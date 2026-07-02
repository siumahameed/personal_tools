"""Verbose smoke test."""
import asyncio
import sys
import time
import logging
from pathlib import Path

LOG = Path(__file__).parent.parent / "logs" / "smoke.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=open(LOG, "w", encoding="utf-8"),
)
# Quiet down noisy libraries
for name in ("httpx", "httpcore", "aiosqlite", "ddgs", "rustls", "hickory_net", "reqwest", "search"):
    logging.getLogger(name).setLevel(logging.WARNING)


def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def main():
    log("Smoke test starting — 1 query, INFO logging")

    from app.research.agent import ResearchDiscoveryAgent
    from app.core.database import async_session
    from app.core.models import ResearchLead
    from sqlalchemy import select, func

    try:
        async with ResearchDiscoveryAgent() as agent:
            log("Running: Bangladesh statistics professor researchgate")
            await agent.run(custom_query="Bangladesh statistics professor researchgate")
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
