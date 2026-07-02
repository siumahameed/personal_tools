import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime


class PaperScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def scrape_google_scholar(self, scholar_url, max_papers=10):
        try:
            resp = self.session.get(scholar_url, timeout=20)
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, "html.parser")
            papers = []
            for entry in soup.select("#gsc_a_b .gsc_a_tr")[:max_papers]:
                title_el = entry.select_one(".gsc_a_at")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link = title_el.get("href", "")
                if link and not link.startswith("http"):
                    link = "https://scholar.google.com" + link

                authors_venue = entry.select_one(".gs_gray")
                authors_venue_text = authors_venue.get_text(strip=True) if authors_venue else ""

                year_el = entry.select_one(".gsc_a_y span")
                year = year_el.get_text(strip=True) if year_el else ""

                cited_el = entry.select_one(".gsc_a_c a")
                citations = cited_el.get_text(strip=True) if cited_el else "0"

                papers.append({
                    "title": title,
                    "url": link,
                    "authors_venue": authors_venue_text,
                    "year": year,
                    "citations": citations,
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                time.sleep(1)
            return papers
        except Exception as e:
            print(f"  PaperScraper error for {scholar_url[:60]}: {e}")
            return []

    def _ss_get(self, url, params=None, retries=3):
        for attempt in range(retries):
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            return resp
        return resp

    def scrape_by_author_name(self, author_name, max_papers=10):
        raw = author_name.replace("Prof. ", "").replace("Prof ", "").strip()

        def apply_umlaut(s):
            result = s
            result = result.replace("ue", "ü").replace("Ue", "Ü").replace("UE", "Ü")
            result = result.replace("oe", "ö").replace("Oe", "Ö").replace("OE", "Ö")
            result = result.replace("ae", "ä").replace("Ae", "Ä").replace("AE", "Ä")
            return result

        def unapply_umlaut(s):
            result = s
            result = result.replace("ü", "ue").replace("Ü", "Ue")
            result = result.replace("ö", "oe").replace("Ö", "Oe")
            result = result.replace("ä", "ae").replace("Ä", "Ae")
            return result

        queries = [raw]
        alt = apply_umlaut(raw)
        if alt != raw:
            queries.append(alt)
        alt2 = unapply_umlaut(raw)
        if alt2 != raw and alt2 not in queries:
            queries.append(alt2)
        parts = raw.replace("-", " ").split()
        if len(parts) >= 2:
            first_last = f"{parts[0]} {parts[-1]}"
            queries.append(first_last.replace("-", " "))
            for v in list(queries):
                queries.append(f"{parts[-1]}, {parts[0]}")
                queries.append(parts[-1])
        queries = list(dict.fromkeys(q for q in queries if q.strip()))

        def match_score(aname, ql):
            al = aname.lower().replace("-", " ")
            ql = ql.lower().replace("-", " ")
            if al == ql:
                return 4
            if ql in al:
                return 3
            if al in ql:
                return 2
            aname_words = set(al.split())
            qwords = set(ql.split())
            common = aname_words & qwords
            if len(common) >= 2:
                return 2
            if len(common) >= 1:
                return 1
            return 0

        try:
            best = None
            best_score = 0
            for q in queries:
                resp = self._ss_get("https://api.semanticscholar.org/graph/v1/author/search", params={"query": q, "limit": 5})
                if resp.status_code != 200:
                    continue
                authors = resp.json().get("data", [])
                for a in authors:
                    score = match_score(a.get("name", ""), q)
                    if score > best_score and a.get("authorId"):
                        best = (a.get("authorId"), a["name"], q)
                        best_score = score
                if best_score >= 2:
                    break
                time.sleep(1)

            if not best:
                print(f"  No Semantic Scholar author found for: {raw}")
                return []

            author_id, matched_name, query = best
            print(f"  Semantic Scholar: matched '{query}' -> {matched_name} ({author_id})")
            time.sleep(1)
            papers_url = f"https://api.semanticscholar.org/graph/v1/author/{author_id}/papers"
            resp = self._ss_get(papers_url, params={"limit": max_papers, "fields": "title,url,year,citationCount,authors,venue"})
            if resp.status_code != 200:
                return []
            raw_papers = resp.json().get("data", [])
            papers = []
            for p in raw_papers:
                if not p.get("title"):
                    continue
                author_names = [a.get("name", "") for a in p.get("authors", []) if a.get("name")]
                authors_text = ", ".join(author_names[:3])
                if len(author_names) > 3:
                    authors_text += " et al."
                venue = p.get("venue", "") or ""
                papers.append({
                    "title": p["title"],
                    "url": p.get("url", "") or "",
                    "authors_venue": f"{authors_text} - {venue}" if authors_text and venue else authors_text or venue,
                    "year": str(p.get("year", "")) if p.get("year") else "",
                    "citations": str(p.get("citationCount", 0)),
                    "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
            if papers:
                print(f"  Semantic Scholar: {len(papers)} papers for {raw}")
            return papers
        except Exception as e:
            print(f"  Semantic Scholar error for {raw}: {e}")
            return []
