import re
import json
import os
import random
import requests
from datetime import datetime
from urllib.parse import urlparse

from agents.base import USER_AGENTS


PLACEHOLDER_VALUES = {
    "check website", "check link", "check eligibility", "check requirements",
    "check soon", "unknown", "varies", "likely required", "check",
    "auto-discovered. verify details on website before applying.",
    "msc/phd", "ml, ai, data science, statistics (verify)",
    "english (likely)", "n/a", "",
}

AMOUNT_RE = re.compile(
    r'(?:€|EUR|euro|euros|USD|US\$|\$)\s*([\d,]+(?:\.\d{2})?)',
    re.IGNORECASE
)

MONTH_PATTERN = r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'

DEADLINE_RE = re.compile(
    r'(?:deadline|due\s*date|closing\s*date|application\s*deadline|apply\s*by)\s*:?\s*'
    r'(?:'
    r'(\d{1,2}(?:st|nd|rd|th)?\s+' + MONTH_PATTERN + r'\s*\d{4})'
    r'|'
    r'(' + MONTH_PATTERN + r'\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})'
    r')',
    re.IGNORECASE
)

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

TUITION_RE = re.compile(
    r'(?:tuition|fee|fees|cost|semester\s*fee)\s*:?\s*(?:is|:|-)?\s*(?:€|EUR|euro|\$|USD)\s*([\d,]+(?:\.\d{2})?)',
    re.IGNORECASE
)

TOEFL_RE = re.compile(r'(?:TOEFL|IELTS)\s*(?:score|requirement|required)?\s*:?\s*(\d+(?:\.\d)?(?:\s*\+)?)', re.IGNORECASE)
GRE_RE = re.compile(r'\bGRE\b', re.IGNORECASE)


class TargetEnricherAgent:
    ENRICH_LOG = "enrichment_log.json"

    def __init__(self, profile, sheets_client=None, interactive=False):
        self.profile = profile
        self.sheets = sheets_client
        self.interactive = interactive
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.logs = []

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.logs.append(line)
        print(f"  [TargetEnricher] {msg}")

    def load_json(self, filename):
        path = os.path.join(self.data_dir, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.log(f"Error loading {filename}: {e}")
        return None

    def save_json(self, filename, data):
        os.makedirs(self.data_dir, exist_ok=True)
        path = os.path.join(self.data_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def fetch_text(self, url, timeout=12):
        try:
            ua = random.choice(USER_AGENTS)
            self.session.headers.update({"User-Agent": ua})
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            return soup.get_text(separator=" ")
        except Exception as e:
            self.log(f"  Fetch failed for {urlparse(url).netloc}: {e}")
            return None

    def is_placeholder(self, val):
        if not val:
            return True
        v = str(val).strip().lower()
        return v in PLACEHOLDER_VALUES or (len(v) < 3)

    def col_index(self, headers, *keywords):
        for i, h in enumerate(h.lower().strip() for h in headers):
            for kw in keywords:
                if kw in h:
                    return i
        return -1

    def row_by_name(self, headers, rows, name):
        name_idx = self.col_index(headers, "name")
        if name_idx == -1:
            return None
        for row in rows:
            if len(row) > name_idx and str(row[name_idx]).strip().lower() == name.strip().lower():
                return row
        return None

    def enrich(self):
        self.log("Starting target enrichment...")
        followed = self.load_json("followed.json") or {"scholarships": [], "professors": [], "universities": []}
        enr_log = self.load_json(self.ENRICH_LOG) or {}

        if any(followed.values()):
            self._enrich_type("scholarships", followed.get("scholarships", []), enr_log)
            self._enrich_type("professors", followed.get("professors", []), enr_log)
            self._enrich_type("universities", followed.get("universities", []), enr_log)

        self.save_json(self.ENRICH_LOG, enr_log)
        self.log("Target enrichment complete")
        return self.logs

    def _enrich_type(self, item_type, followed_names, enr_log):
        if not followed_names:
            return

        filename = f"{item_type}.json"
        data = self.load_json(filename)
        if not data or len(data) < 2:
            self.log(f"No data found for {item_type}")
            return

        headers = data[0]
        rows = data[1:]
        changed = 0

        for name in followed_names:
            enr_key = f"{item_type}::{name}"
            if enr_key in enr_log:
                self.log(f"  Skipping {name[:50]} (already enriched)")
                continue

            row = self.row_by_name(headers, rows, name)
            if not row:
                self.log(f"  {name[:50]} not found in stored data")
                continue

            url = self._get_url(item_type, headers, row)
            if not url:
                self.log(f"  {name[:50]}: no URL to fetch")
                continue

            self.log(f"  Fetching {urlparse(url).netloc} for {name[:40]}...")
            text = self.fetch_text(url)
            if not text:
                continue

            enriched = self._extract_fields(item_type, text)
            for col_name, value in enriched.items():
                ci = self.col_index(headers, *col_name)
                if ci != -1 and ci < len(row):
                    if self.is_placeholder(row[ci]):
                        row[ci] = value

            enr_log[enr_key] = datetime.now().isoformat()
            changed += 1

        if changed:
            data[0] = headers
            data[1:] = rows
            self.save_json(filename, data)
            self.log(f"Enriched {changed} {item_type} entries")

    def _get_url(self, item_type, headers, row):
        for kw in ["url", "portal", "profile", "page"]:
            ci = self.col_index(headers, kw)
            if ci != -1 and ci < len(row):
                val = str(row[ci]).strip()
                if val and val.startswith("http"):
                    return val
        return None

    def _extract_fields(self, item_type, text):
        result = {}
        if item_type == "scholarships":
            result.update(self._extract_amount(text))
            result.update(self._extract_deadline(text))
            result["Coverage Details"] = self._extract_snippet(text)
        elif item_type == "professors":
            emails = EMAIL_RE.findall(text)
            if emails:
                result["Email"] = emails[0]
        elif item_type == "universities":
            result.update(self._extract_tuition(text))
            result.update(self._extract_deadline(text))
            result.update(self._extract_language(text))
            result["GRE/GMAT Required"] = "Yes" if GRE_RE.search(text) else "Check website"
        return result

    def _extract_amount(self, text):
        try:
            matches = AMOUNT_RE.findall(text)
            if matches:
                amt = matches[0].replace(",", "").strip()
                float(amt)
                return {"Amount (per year)": amt, "Currency": "Check"}
        except (ValueError, AttributeError):
            pass
        return {}

    def _extract_deadline(self, text):
        try:
            match = DEADLINE_RE.search(text)
            if match:
                deadline_str = match.group(1) or match.group(2) or ""
                if deadline_str:
                    return {"Deadline Start": deadline_str.strip(), "Deadline End": deadline_str.strip()}
        except Exception:
            pass
        return {}

    def _extract_tuition(self, text):
        try:
            match = TUITION_RE.search(text)
            if match:
                return {"Tuition Fees": match.group(1)}
        except Exception:
            pass
        return {}

    def _extract_language(self, text):
        try:
            match = TOEFL_RE.search(text)
            if match:
                return {"Language Requirements": f"TOEFL/IELTS {match.group(1)}"}
        except Exception:
            pass
        return {}

    def _extract_snippet(self, text, max_len=200):
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        meaningful = [s for s in sentences if len(s) > 30 and not s.startswith("http")]
        if meaningful:
            return meaningful[0][:max_len]
        return "Check website"
