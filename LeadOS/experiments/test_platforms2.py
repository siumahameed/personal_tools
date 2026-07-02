import asyncio
import re
import httpx

async def test_dblp_search():
    print("=== DBLP search API ===")
    queries = ["Yann LeCun", "Andrew Ng"]
    async with httpx.AsyncClient(timeout=10) as c:
        for q in queries:
            url = f"https://dblp.org/search/author/api?q={q}&format=json"
            r = await c.get(url)
            print(f"  {q}: {r.status_code}, len={len(r.text)}")
            if r.status_code == 200:
                d = r.json()
                hits = d.get("result", {}).get("hits", {}).get("hit", [])
                for h in hits[:2]:
                    info = h.get("info", {})
                    print(f"    {info.get('url')}: {info.get('author')}")


async def test_arxiv_search():
    print("\n=== arXiv /a/<name> (no number) ===")
    names = ["Yann_LeCun", "Andrew_Ng"]
    async with httpx.AsyncClient(timeout=10) as c:
        for n in names:
            url = f"https://arxiv.org/a/{n}"
            r = await c.get(url, follow_redirects=True)
            print(f"  {url}: {r.status_code}, len={len(r.text)}")
            if r.status_code == 200:
                h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", r.text, re.S)
                h1 = [re.sub(r"<[^>]+>", " ", h).strip()[:60] for h in h1]
                print(f"    h1: {h1[:2]}")


def test_linkedin_slug():
    print("\n=== LinkedIn slug parse ===")
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
        # Strip trailing numeric ID
        cleaned = re.sub(r"-\d{4,}$", "", s)
        # Title-case, but keep uppercase like "Md"
        name = " ".join(p.capitalize() for p in cleaned.split("-"))
        print(f"  {s:42s} -> {name!r}")


async def test_s2_author():
    print("\n=== S2 author paper API ===")
    # Author ID for Andrew Y. Ng from the previous test
    author_id = "2067948213"
    url = f"https://api.semanticscholar.org/graph/v1/author/{author_id}?fields=name,affiliations,homepage,paperCount,hIndex,externalIds"
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url)
        print(f"  status: {r.status_code}")
        if r.status_code == 200:
            import json
            print(f"  data: {json.dumps(r.json(), indent=2)[:500]}")


async def main():
    await test_dblp_search()
    await test_arxiv_search()
    test_linkedin_slug()
    await test_s2_author()

asyncio.run(main())
