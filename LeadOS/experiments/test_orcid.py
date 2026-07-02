import asyncio
import re
import httpx

async def go():
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
        r = await c.get("https://orcid.org/0000-0002-1825-0097",
                        headers={"User-Agent": "Mozilla/5.0"})
        with open("orcid_test.html", "wb") as f:
            f.write(r.text.encode("utf-8"))
        m = re.findall(r'<script type="application/ld\+json">(.*?)</script>', r.text, re.S)
        print("JSON-LD scripts:", len(m))
        for i, x in enumerate(m[:3]):
            print(f"  [{i}]", x[:300])
        m = re.findall(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', r.text)
        print("meta desc:", m[:2])
        m = re.findall(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', r.text)
        print("og:title:", m[:2])
        # look for any name-like text
        m = re.findall(r'"givenName"\s*:\s*"([^"]+)"', r.text)
        print("given names:", m)
        m = re.findall(r'"familyName"\s*:\s*"([^"]+)"', r.text)
        print("family names:", m)

asyncio.run(go())
