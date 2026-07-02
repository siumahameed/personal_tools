import asyncio
import re
import httpx

async def go():
    urls = [
        "https://arxiv.org/auth/Yann_LeCun",
        "https://arxiv.org/auth/Judea_Pearl_1",
        "https://dblp.org/pid/04/3683.html",
        "https://www.semanticscholar.org/author/Christopher-D.-Manning/1629531",
        "https://loop.frontiersin.org/people/555054/overview",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
        for u in urls:
            try:
                r = await c.get(u, headers=headers)
                print(f"\n=== {u} ===")
                print(f"  status: {r.status_code}, length: {len(r.text)}")
                h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", r.text, re.S)
                h1 = [re.sub(r"<[^>]+>", " ", h).strip()[:80] for h in h1]
                print(f"  h1: {h1[:3]}")
                og = re.findall(r'og:title"\s+content="([^"]+)"', r.text)
                print(f"  og:title: {og[:2]}")
                title = re.findall(r"<title[^>]*>(.*?)</title>", r.text, re.S)
                title = [re.sub(r"\s+", " ", t).strip()[:80] for t in title]
                print(f"  title: {title[:1]}")
            except Exception as e:
                print(f"  ERROR: {e}")

asyncio.run(go())
