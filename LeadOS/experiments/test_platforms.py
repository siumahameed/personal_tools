"""Test what we can extract from each platform's API or URL slug."""
import asyncio
import re
import httpx


# ── Test DBLP XML API ────────────────────────────────────────────
async def test_dblp():
    """DBLP pid URLs: /pid/04/3683 etc. XML at /pid/04/3683.xml"""
    pids = ["04/3683", "88/3928", "72/5879"]  # random pids
    print("\n=== DBLP XML API ===")
    async with httpx.AsyncClient(timeout=10) as c:
        for pid in pids:
            url = f"https://dblp.org/pid/{pid}.xml"
            try:
                r = await c.get(url)
                print(f"  {url}: {r.status_code}, len={len(r.text)}")
                if r.status_code == 200:
                    # Try to extract name
                    m = re.search(r'<author[^>]*>([^<]+)</author>', r.text)
                    if not m:
                        m = re.search(r'<dblpperson[^>]+name="([^"]+)"', r.text)
                    if not m:
                        m = re.search(r'<title>([^<]+)</title>', r.text)
                    print(f"    name: {m.group(1) if m else 'NOT FOUND'}")
            except Exception as e:
                print(f"  ERROR: {e}")


# ── Test Semantic Scholar Author Search API ──────────────────────
async def test_s2():
    """S2 author search: https://api.semanticscholar.org/graph/v1/author/search?query=... """
    queries = ["Andrew Ng", "Yann LeCun"]
    print("\n=== Semantic Scholar API ===")
    async with httpx.AsyncClient(timeout=10) as c:
        for q in queries:
            url = f"https://api.semanticscholar.org/graph/v1/author/search?query={q}&fields=name,affiliations,homepage,paperCount"
            try:
                r = await c.get(url)
                print(f"  {q}: {r.status_code}, len={len(r.text)}")
                if r.status_code == 200:
                    import json
                    d = r.json()
                    for a in d.get("data", [])[:3]:
                        print(f"    {a.get('authorId')}: {a.get('name')} - {a.get('affiliations')}")
            except Exception as e:
                print(f"  ERROR: {e}")


# ── Test arXiv /a/<id> pattern ───────────────────────────────────
async def test_arxiv():
    print("\n=== arXiv /a/<id> ===")
    ids = ["Yann_LeCun_1", "Andrew_Ng_1", "Tomas_Mikolov"]
    async with httpx.AsyncClient(timeout=10) as c:
        for a in ids:
            url = f"https://arxiv.org/a/{a}"
            try:
                r = await c.get(url, follow_redirects=True)
                print(f"  {url}: {r.status_code}, len={len(r.text)}")
                if r.status_code == 200:
                    # Look for h1 or title
                    h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", r.text, re.S)
                    h1 = [re.sub(r"<[^>]+>", " ", h).strip()[:80] for h in h1]
                    print(f"    h1: {h1[:2]}")
            except Exception as e:
                print(f"  ERROR: {e}")


# ── Test LinkedIn slug → name parsing ────────────────────────────
def test_linkedin_slug():
    print("\n=== LinkedIn slug → name ===")
    slugs = [
        "dr-md-shafiqul-islam-1bb86842",
        "dr-hasinur-rahaman-khan-20955324",
        "anwarstat",
        "mohaimen-mansur",
        "md-galib-hossain-570322139",
        "jane-doe",
        "john-doe-12345",
    ]
    for s in slugs:
        # Strip trailing numeric ID like "1bb86842" or "1234567"
        cleaned = re.sub(r"-\d{4,}$", "", s)
        # Title-case
        name = " ".join(p.capitalize() for p in cleaned.split("-"))
        print(f"  {s:40s} -> {name!r}")


async def main():
    await test_dblp()
    await test_s2()
    await test_arxiv()
    test_linkedin_slug()

asyncio.run(main())
