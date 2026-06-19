import asyncio
import logging
import re
from urllib.parse import quote

import httpx
from ddgs import DDGS

from app.core.config import settings

logger = logging.getLogger(__name__)

_ddgs_semaphore = asyncio.Semaphore(2)


RECENCY_MAP = {
    "d": "qdr:d", "w": "qdr:w", "m": "qdr:m",
    "3m": "qdr:3", "6m": "qdr:6",
}


_SITE_OPERATOR_RE = re.compile(r'\bsite:\S+', re.IGNORECASE)


def _has_site_operator(query: str) -> bool:
    return bool(_SITE_OPERATOR_RE.search(query))


def _strip_site_operator(query: str) -> str:
    return _SITE_OPERATOR_RE.sub('', query).strip()


class SearchClient:
    """Multi-backend search with cascading fallback.

    Order:
    1. site-aware backends (SerpAPI, Google CSE) — use the original query
    2. DDGS with the site: operator STRIPPED — natural-language fallback

    If a site-aware backend fails (e.g. rate-limited) we move on to the next,
    then fall back to DDGS with site: stripped so a site: query still has a
    chance of returning useful results.
    """

    def __init__(self):
        self.backends: list[tuple[str, callable, bool]] = []
        if settings.serpapi_api_key:
            self.backends.append(("serpapi", self._search_serpapi, True))
        if settings.google_api_key and settings.google_cse_id:
            self.backends.append(("google", self._search_google, True))
        self.backends.append(("ddgs", self._search_ddgs, False))
        self._serpapi_cooldown_until: float = 0.0

    async def search(
        self, query: str, num: int = 10, recency: str = "",
    ) -> list[str]:
        if not recency:
            recency = settings.search_recency

        has_site = _has_site_operator(query)
        errors: list[str] = []
        now = asyncio.get_event_loop().time()

        for name, backend, site_aware in self.backends:
            if name == "serpapi" and now < self._serpapi_cooldown_until:
                logger.debug("Skipping SerpAPI: in cooldown until %.0f", self._serpapi_cooldown_until)
                continue
            try:
                urls = await backend(query, num, recency)
                if urls:
                    logger.debug(
                        "Search backend '%s' returned %d results for '%.50s'",
                        name, len(urls), query,
                    )
                    return urls
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and name == "serpapi":
                    self._serpapi_cooldown_until = now + 300  # 5 min cooldown
                    logger.warning("SerpAPI 429 — entering 5min cooldown")
                errors.append(f"{name}: {e}")
                logger.debug("Search backend '%s' failed: %s", name, e)
            except Exception as e:
                errors.append(f"{name}: {e}")
                logger.debug("Search backend '%s' failed: %s", name, e)

        # Final fallback: if the query had site: and DDGS already ran (without site:),
        # try DDGS again with the full query stripped. Some backends get noisy without
        # the operator anyway, so we only do this if DDGS is the only site-aware-less
        # backend AND we didn't just get any results.
        if has_site:
            stripped = _strip_site_operator(query)
            if stripped and stripped != query:
                try:
                    urls = await self._search_ddgs(stripped, num, recency)
                    if urls:
                        logger.info(
                            "Search fallback (DDGS w/o site:) returned %d for '%.50s'",
                            len(urls), stripped,
                        )
                        return urls
                except Exception as e:
                    errors.append(f"ddgs(stripped): {e}")

        logger.warning(
            "All search backends failed for '%.50s': %s",
            query, "; ".join(errors),
        )
        return []

    async def _search_serpapi(
        self, query: str, num: int, recency: str,
    ) -> list[str]:
        params = {
            "q": query,
            "api_key": settings.serpapi_api_key,
            "num": min(num, 10),
            "engine": "google",
        }
        tbs = RECENCY_MAP.get(recency)
        if tbs:
            params["tbs"] = tbs
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://serpapi.com/search", params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            organic = data.get("organic_results") or []
            return [r["link"] for r in organic if r.get("link")]

    async def _search_google(
        self, query: str, num: int, recency: str,
    ) -> list[str]:
        params = {
            "q": query,
            "key": settings.google_api_key,
            "cx": settings.google_cse_id,
            "num": min(num, 10),
        }
        if recency:
            params["sort"] = "date"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items") or []
            return [r["link"] for r in items if r.get("link")]

    @staticmethod
    def _ddgs_timelimit(recency: str) -> str | None:
        if not recency:
            return None
        if recency in ("d", "w", "m"):
            return recency
        if recency in ("3m", "6m"):
            return "m"
        return None

    async def _search_ddgs(
        self, query: str, num: int, recency: str,
    ) -> list[str]:
        tl = self._ddgs_timelimit(recency)
        clean_query = _strip_site_operator(query)
        if clean_query != query:
            logger.debug("DDGS stripped site: query: '%s' -> '%s'", query, clean_query)
        async with _ddgs_semaphore:
            return await asyncio.to_thread(
                lambda: [
                    r["href"]
                    for r in DDGS().text(
                        clean_query, max_results=num, timelimit=tl,
                    )
                ],
            )
