import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import random
import re
import time
import logging
from urllib.parse import urlparse, urljoin, parse_qs

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]


def _with_retries(func, max_retries=3, base_delay=1.0, backoff=2.0):
    """Retry a function with exponential backoff on failures."""
    for attempt in range(max_retries + 1):
        try:
            result = func()
            if result is not None:
                return result
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                delay = base_delay * (backoff ** attempt) + random.uniform(0, 0.5)
                logger.warning(f"Rate limited (429), retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries})")
                time.sleep(delay)
                continue
            elif e.response is not None and e.response.status_code >= 500:
                delay = base_delay * (backoff ** attempt) + random.uniform(0, 0.5)
                logger.warning(f"Server error {e.response.status_code}, retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries})")
                time.sleep(delay)
                continue
            raise
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < max_retries:
                delay = base_delay * (backoff ** attempt) + random.uniform(0, 0.5)
                logger.warning(f"Connection error: {e}, retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries})")
                time.sleep(delay)
                continue
            raise
        except Exception:
            if attempt < max_retries:
                delay = base_delay * (backoff ** attempt)
                time.sleep(delay)
                continue
            raise
    return None


class BaseAgent:
    def __init__(self, name, sheets_client=None, interactive=True):
        self.name = name
        self.sheets = sheets_client
        self.interactive = interactive
        self.data_dir = os.path.join(os.path.join(os.path.dirname(__file__), '..', '..'), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self.results_cache = {}

    def search_web(self, query, num_results=5):
        """Search the web with fallback chain: DuckDuckGo -> Bing -> Google."""
        self.session.cookies.clear()
        self.session.headers.update({"User-Agent": random.choice(USER_AGENTS)})

        results = self.search_ddg(query, num_results)
        if results:
            return results

        results = self.search_bing(query, num_results)
        if results:
            return results

        results = self.search_google(query, num_results)
        return results

    def search_ddg(self, query, num_results=5):
        try:
            url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            resp = _with_retries(lambda: self._raw_get(url, timeout=8))
            if resp and resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for result in soup.select(".result")[:num_results]:
                    title_el = result.select_one(".result__title")
                    snippet_el = result.select_one(".result__snippet")
                    if title_el:
                        a_tag = title_el.select_one("a")
                        href = a_tag.get("href", "") if a_tag else ""
                        if "/l/?kh=" in href or "uddg=" in href:
                            parsed_href = urlparse(href)
                            query_params = parse_qs(parsed_href.query)
                            if "uddg" in query_params:
                                href = query_params["uddg"][0]
                        results.append({
                            "title": title_el.get_text(strip=True),
                            "url": href,
                            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        })
                return results
            return []
        except Exception as e:
            self.log(f"DDG Search error: {e}")
            return []

    def search_bing(self, query, num_results=5):
        try:
            url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
            resp = _with_retries(lambda: self._raw_get(url, timeout=8))
            if resp and resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for li in soup.select("#b_results .b_algo")[:num_results]:
                    title_el = li.select_one("h2 a")
                    snippet_el = li.select_one(".b_caption p")
                    if title_el:
                        results.append({
                            "title": title_el.get_text(strip=True),
                            "url": title_el.get("href", ""),
                            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        })
                return results
            return []
        except Exception as e:
            self.log(f"Bing Search error: {e}")
            return []

    def search_google(self, query, num_results=5):
        try:
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}&hl=en"
            resp = _with_retries(lambda: self._raw_get(url, timeout=8))
            if resp and resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for g in soup.select("#search .g")[:num_results]:
                    title_el = g.select_one("h3")
                    link_el = g.select_one("a")
                    snippet_el = g.select_one(".VwiC3b")
                    if title_el and link_el:
                        results.append({
                            "title": title_el.get_text(strip=True),
                            "url": link_el.get("href", ""),
                            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        })
                return results
            return []
        except Exception as e:
            self.log(f"Google Search error: {e}")
            return []

    def _raw_get(self, url, timeout=15):
        """Low-level GET with current session headers."""
        return self.session.get(url, timeout=timeout)

    def fetch_page(self, url, cache=True):
        if cache and url in self.results_cache:
            return self.results_cache[url]
        try:
            self.session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
            resp = _with_retries(lambda: self._raw_get(url, timeout=20))
            if resp and resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                if cache:
                    self.results_cache[url] = soup
                return soup
            self.log(f"Fetch returned {resp.status_code if resp else 'None'} for {url[:80]}")
            return None
        except Exception as e:
            self.log(f"Fetch error for {url[:60]}: {e}")
            return None

    def extract_text(self, soup, selector):
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else ""

    def extract_all_text(self, soup, selector):
        return [el.get_text(strip=True) for el in soup.select(selector)]

    def extract_links(self, soup, selector, base_url=""):
        links = []
        for a in soup.select(selector):
            href = a.get("href", "")
            if href and not href.startswith("#"):
                if base_url and not href.startswith("http"):
                    href = urljoin(base_url, href)
                links.append({"text": a.get_text(strip=True), "url": href})
        return links

    @staticmethod
    def make_row(item, headers, key_map):
        row = []
        for h in headers:
            key = key_map.get(h)
            if key:
                val = item.get(key, "")
            else:
                val = ""
            row.append(str(val) if val is not None else "")
        return row

    def extract_emails(self, text):
        return re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)

    def extract_phones(self, text):
        return re.findall(r'\+?\d[\d\s\-().]{7,15}\d', text)

    def multi_search(self, queries, max_per_query=3):
        all_results = []
        seen_urls = set()
        for query in queries:
            results = self.search_web(query, max_per_query)
            for r in results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
            self.log(f"  Searched: {query[:60]}... -> {len(results)} results")
        return all_results

    def scrape_table(self, url, row_selector, cell_selector="td"):
        soup = self.fetch_page(url)
        if not soup:
            return []
        rows = []
        for tr in soup.select(row_selector):
            cells = [td.get_text(strip=True) for td in tr.select(cell_selector)]
            if cells:
                rows.append(cells)
        return rows

    def save_json(self, filename, data):
        path = os.path.join(self.data_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_json(self, filename):
        path = os.path.join(self.data_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_to_sheets(self, sheet_name, headers, rows):
        if self.sheets:
            try:
                self.sheets.sync_table(sheet_name, headers, rows)
            except Exception as e:
                self.log(f"Google Sheets write error: {e}")

        filename = f"{sheet_name.lower()}.json"
        existing = self.load_json(filename)
        if not existing:
            existing_headers = headers
            existing_rows = []
        else:
            existing_headers = existing[0] if existing else headers
            existing_rows = existing[1:] if len(existing) > 1 else []

        existing_name_idx = -1
        for i, h in enumerate(h.lower().strip() for h in existing_headers):
            if "name" in h:
                existing_name_idx = i
                break

        existing_names = set()
        if existing_name_idx != -1:
            for r in existing_rows:
                if len(r) > existing_name_idx:
                    existing_names.add(r[existing_name_idx].strip().lower())

        incoming_name_idx = -1
        for i, h in enumerate(h.lower().strip() for h in headers):
            if "name" in h:
                incoming_name_idx = i
                break

        new_rows = []
        for row in rows:
            if incoming_name_idx != -1 and len(row) > incoming_name_idx:
                name_val = str(row[incoming_name_idx]).strip().lower()
                if name_val in existing_names:
                    continue
                existing_names.add(name_val)
            new_rows.append(row)

        updated = [headers]
        updated.extend(existing_rows)
        updated.extend(new_rows)
        self.save_json(filename, updated)
        self.log(f"Appended {len(new_rows)} new rows to local storage file: {filename}")

    def ask_user(self, prompt, default=True):
        if not self.interactive:
            return default
        print(f"\n[{self.name}] >>> {prompt}")
        return input("  Your answer (yes/no): ").strip().lower() == "yes"

    def ask_input(self, prompt):
        print(f"\n[{self.name}] >>> {prompt}")
        return input("  > ").strip()

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"  [{timestamp}] {message}")
