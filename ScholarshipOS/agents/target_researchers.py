import os
import re
import json
import time
import random
import requests
from datetime import datetime
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from agents.base import BaseAgent, USER_AGENTS
from features.paper_scraper import PaperScraper

PLACEHOLDERS = {
    "check website", "check link", "check eligibility", "check requirements",
    "check soon", "unknown", "varies", "likely required", "check",
    "auto-discovered. verify details on website before applying.",
    "msc/phd", "ml, ai, data science, statistics (verify)",
    "english (likely)", "n/a", "", "check city", "check program page", "check department page",
    "check with university", "check website for info", "verify"
}

def is_placeholder(val):
    if not val:
        return True
    v = str(val).strip().lower()
    return v in PLACEHOLDERS or len(v) < 3

class ScholarshipResearcherAgent(BaseAgent):
    def __init__(self, sheets_client=None):
        super().__init__("ScholarshipResearcherAgent", sheets_client, interactive=False)

    def research(self, name, current_data):
        self.log(f"Starting deep search for followed scholarship: {name}")
        query = f"{name} official application requirements deadline eligibility coverage funding selection criteria"
        search_results = self.search_web(query, num_results=5)
        
        if not search_results:
            self.log("  No search results found.")
            return {}
            
        combined_text = ""
        urls_visited = []
        for r in search_results:
            url = r.get("url")
            if url and url.startswith("http"):
                self.log(f"  Scraping: {url[:60]}")
                soup = self.fetch_page(url)
                if soup:
                    urls_visited.append(url)
                    # Clean up head/nav/footer text
                    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        tag.decompose()
                    combined_text += " " + soup.get_text(separator=" ")
                    
        if not combined_text:
            self.log("  Failed to extract page content.")
            return {}
            
        extracted = self.parse_scholarship_text(combined_text)
        
        # Preserve original official URL / Portal if present
        if urls_visited and (is_placeholder(current_data.get("url")) or is_placeholder(current_data.get("official_url"))):
            extracted["Official URL"] = urls_visited[0]
        if urls_visited and len(urls_visited) > 1 and is_placeholder(current_data.get("portal")):
            extracted["Application Portal"] = urls_visited[1]
            
        return extracted

    def parse_scholarship_text(self, text):
        info = {}
        text_lower = text.lower()
        
        # 1. Coverage Type
        if "full tuition" in text_lower or "full ride" in text_lower or "fully funded" in text_lower:
            info["Coverage Type"] = "Full-ride"
        elif "partial tuition" in text_lower or "partially funded" in text_lower or "tuition waiver" in text_lower:
            info["Coverage Type"] = "Partial"
            
        # 2. Coverage details
        details = []
        if "stipend" in text_lower or "allowance" in text_lower:
            details.append("Monthly stipend/allowance")
        if "travel" in text_lower or "flights" in text_lower:
            details.append("Travel expenses")
        if "health insurance" in text_lower or "medical insurance" in text_lower:
            details.append("Health insurance")
        if "tuition fee" in text_lower or "tuition waiver" in text_lower:
            details.append("Tuition waiver")
        if details:
            info["Coverage Details"] = ", ".join(details)
            
        # 3. Amount
        amt_match = re.search(r'(?:€|EUR|euro|euros|USD|US\$|\$)\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s*month|/month|monthly)', text, re.IGNORECASE)
        if amt_match:
            info["Amount (per year)"] = f"{amt_match.group(0)} (monthly stipend)"
            info["Currency"] = "EUR" if "€" in amt_match.group(0) or "eur" in amt_match.group(0).lower() else "USD"
        else:
            amt_year = re.search(r'(?:€|EUR|euro|euros|USD|US\$|\$)\s*([\d,]{4,6})', text)
            if amt_year:
                info["Amount (per year)"] = amt_year.group(0)
                info["Currency"] = "EUR" if "€" in amt_year.group(0) or "eur" in amt_year.group(0).lower() else "USD"

        # 4. English Test Required
        ielts_match = re.search(r'IELTS\s*(?:score\s*of|minimum\s*of|score)?\s*([5678]\.?\d?)', text, re.IGNORECASE)
        toefl_match = re.search(r'TOEFL\s*(?:score\s*of|minimum\s*of|score|iBT)?\s*(\d{2,3})', text, re.IGNORECASE)
        lang_reqs = []
        if ielts_match:
            lang_reqs.append(f"IELTS {ielts_match.group(1)}")
        if toefl_match:
            lang_reqs.append(f"TOEFL {toefl_match.group(1)}")
        if lang_reqs:
            info["English Test Required"] = " / ".join(lang_reqs)
        elif "ielts" in text_lower or "toefl" in text_lower:
            info["English Test Required"] = "Yes (IELTS/TOEFL)"
            
        # 5. GRE
        if "gre" in text_lower or "gmat" in text_lower:
            if "not required" in text_lower or "optional" in text_lower:
                info["GRE/GMAT Required"] = "Optional / Not Required"
            else:
                info["GRE/GMAT Required"] = "Required"
        else:
            info["GRE/GMAT Required"] = "Not Required"
            
        # 6. Deadlines
        deadline_matches = re.findall(
            r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)',
            text_lower
        )
        if deadline_matches:
            # Clean up and normalize
            unique_dates = list(set([d.capitalize() for d in deadline_matches]))
            if len(unique_dates) == 1:
                info["Deadline End"] = unique_dates[0]
            elif len(unique_dates) > 1:
                info["Deadline Start"] = unique_dates[0]
                info["Deadline End"] = unique_dates[1]
                
        # 7. Required Documents
        docs = []
        if "recommendation letter" in text_lower or "reference letter" in text_lower or "letters of recommendation" in text_lower:
            docs.append("Recommendation Letters")
        if "motivational letter" in text_lower or "statement of purpose" in text_lower or "sop" in text_lower:
            docs.append("SOP/Motivation Letter")
        if "cv" in text_lower or "resume" in text_lower:
            docs.append("CV")
        if "transcript" in text_lower or "academic record" in text_lower:
            docs.append("Transcripts")
        if "english certificate" in text_lower or "language certificate" in text_lower:
            docs.append("English Proficiency Proof")
        if docs:
            info["Required Documents"] = ", ".join(docs)
            
        # 8. Strategy Notes summary
        notes = []
        if "developing countries" in text_lower or "developing nations" in text_lower:
            notes.append("Targeted specifically at developing nations like Bangladesh.")
        if "work experience" in text_lower or "professional experience" in text_lower:
            notes.append("Requires professional or work experience.")
        if notes:
            info["Strategy Notes"] = " ".join(notes)

        # 9. Selection Criteria
        criteria_match = re.search(
            r'(?:selection\s*criteria|how\s*we\s*select|evaluation\s*criteria)\s*:?\s*(.*?)(?:\n\s*\n|\Z)',
            text, re.IGNORECASE | re.DOTALL
        )
        if criteria_match:
            info["Selection Criteria"] = criteria_match.group(1).strip()[:200]

        # 10. Success Rate (maps to existing column "Success Rate / Competitiveness")
        rate_match = re.search(
            r'(?:approximately|about|around|~)\s*(\d+(?:\.\d+)?)\s*[%]\s*(?:of\s*applicants|acceptance|success|awarded|selected)',
            text, re.IGNORECASE
        )
        if not rate_match:
            rate_match = re.search(
                r'(\d+(?:\.\d+)?)\s*[%]\s*(?:acceptance|success|awarded|selected)',
                text, re.IGNORECASE
            )
        if rate_match:
            info["Success Rate / Competitiveness"] = f"{rate_match.group(1)}%"

        # 11. Number of Awards
        awards_match = re.search(
            r'(?:up\s*to|approximately|about)\s*(\d[\d,]*)\s*(?:scholarships|awards|fellowships|grants|positions)',
            text, re.IGNORECASE
        )
        if awards_match:
            info["Number of Awards"] = awards_match.group(1).replace(",", "")

        # 12. Age Limit
        age_match = re.search(
            r'(?:age\s*limit|maximum\s*age|aged?\s*at\s*most|under\s*the\s*age\s*of)\s*:?\s*(\d{2})',
            text, re.IGNORECASE
        )
        if age_match:
            info["Age Limit"] = f"{age_match.group(1)} years"

        # 13. Bond / Return Requirement
        bond_patterns = [
            r'return\s+to\s+(?:their\s+)?(?:home\s+)?country',
            r'return\s+(?:to\s+)?(?:after\s+)?completion',
            r'obliged?\s+to\s+return',
            r'bond\s+(?:agreement|requirement)',
        ]
        for pat in bond_patterns:
            if re.search(pat, text, re.IGNORECASE):
                info["Bond Requirement"] = "Must return to home country after studies"
                break

        # 14. Funding Specifics (merge into Coverage Details column)
        funding_items = []
        stipend_match = re.search(
            r'(?:€|EUR|euro|euros|USD|US\$|\$)\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s*month|/month|monthly)\s*(?:stipend|allowance)',
            text, re.IGNORECASE
        )
        if stipend_match:
            funding_items.append(f"Monthly stipend: {stipend_match.group(0)}")
        if "travel" in text_lower or "flights" in text_lower:
            funding_items.append("Travel expenses covered")
        if "health insurance" in text_lower or "medical insurance" in text_lower:
            funding_items.append("Health insurance covered")
        if "tuition" in text_lower and ("waiver" in text_lower or "free" in text_lower):
            funding_items.append("Tuition waiver")
        if funding_items:
            existing = info.get("Coverage Details", "")
            new_funding = " | ".join(funding_items)
            info["Coverage Details"] = f"{existing}; {new_funding}" if existing else new_funding

        # 15. Eligible Nationalities (maps to existing column "Eligibility (Nationality)")
        nat_match = re.search(
            r'(?:eligible\s*)?nationalit(?:y|ies)\s*:?\s*(.*?)(?:\.|$)(?:\s|$)',
            text, re.IGNORECASE
        )
        if nat_match:
            info["Eligibility (Nationality)"] = nat_match.group(1).strip()[:200]

        # 16. Contact Email
        emails_found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if emails_found:
            valid_emails = [e for e in emails_found if "ref" not in e and "webmaster" not in e and "support" not in e]
            if valid_emails:
                info["Contact Email"] = valid_emails[0]

        return info


class UniversityResearcherAgent(BaseAgent):
    def __init__(self, sheets_client=None):
        super().__init__("UniversityResearcherAgent", sheets_client, interactive=False)

    def research(self, name, program, current_data):
        self.log(f"Starting deep search for followed university program: {name} - {program}")

        query1 = f"{name} {program} application deadline tuition requirements IELTS TOEFL GRE GPA"
        search_results1 = self.search_web(query1, num_results=3)

        query2 = f"{name} {program} acceptance rate cost of living student housing prerequisites"
        search_results2 = self.search_web(query2, num_results=3)

        all_results = (search_results1 or []) + (search_results2 or [])
        if not all_results:
            self.log("  No search results found.")
            return {}

        combined_text = ""
        urls_visited = []
        seen_urls = set()
        for r in all_results:
            url = r.get("url")
            if url and url.startswith("http") and url not in seen_urls:
                seen_urls.add(url)
                self.log(f"  Scraping: {url[:60]}")
                soup = self.fetch_page(url)
                if soup:
                    urls_visited.append(url)
                    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        tag.decompose()
                    combined_text += " " + soup.get_text(separator=" ")

        if not combined_text:
            self.log("  Failed to extract university page content.")
            return {}

        extracted = self.parse_university_text(combined_text)
        
        if urls_visited and is_placeholder(current_data.get("portal")):
            extracted["Application Portal / Platform"] = urls_visited[0]
        if urls_visited and len(urls_visited) > 1 and is_placeholder(current_data.get("dept_url")):
            extracted["Department / Faculty URL"] = urls_visited[1]
            
        return extracted

    def parse_university_text(self, text):
        info = {}
        text_lower = text.lower()
        
        # 1. Tuition
        tuition_match = re.search(r'(?:tuition|fees?|cost)\s*(?:is|of)?\s*(?:€|EUR|euro|euros|USD|US\$|\$)?\s*([\d,]+)\s*(?:per\s*semester|/semester|semesterly|per\s*term)', text, re.IGNORECASE)
        if tuition_match:
            val = tuition_match.group(1).replace(",", "")
            if val.isdigit() and int(val) > 0:
                info["Tuition (per semester)"] = val
            else:
                info["Tuition (per semester)"] = "0"
        elif "no tuition" in text_lower or "tuition-free" in text_lower or "tuition free" in text_lower or "0 tuition" in text_lower:
            info["Tuition (per semester)"] = "0"
            
        # 2. Semester contribution fee
        sem_fee_match = re.search(r'(?:semester\s*fee|semester\s*contribution|social\s*contribution)\s*(?:is|of)?\s*(?:€|EUR|\$)?\s*(\d{2,3})', text, re.IGNORECASE)
        if sem_fee_match:
            info["Semester Fee / Contribution"] = sem_fee_match.group(1)
            
        # 3. Application Fee
        app_fee_match = re.search(r'(?:application\s*fee|fee\s*to\s*apply)\s*(?:is|of)?\s*(?:€|EUR|\$)?\s*(\d{2,3})', text, re.IGNORECASE)
        if app_fee_match:
            info["Application Fee"] = app_fee_match.group(1)
        elif "no application fee" in text_lower or "free to apply" in text_lower:
            info["Application Fee"] = "0"
            
        # 4. GPA requirement
        gpa_match = re.search(r'(?:gpa|cgpa)\s*(?:of|minimum|required)?\s*([23]\.\d{1,2})', text, re.IGNORECASE)
        if gpa_match:
            info["Minimum GPA Required"] = gpa_match.group(1)
            
        # 5. ECTS Credits
        ects_match = re.search(r'(\d{2,3})\s*ects', text_lower)
        if ects_match:
            info["ECTS Credits"] = ects_match.group(1)
            
        # 6. Deadlines
        deadlines = re.findall(r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)', text_lower)
        if deadlines:
            unique_dates = list(set([d.capitalize() for d in deadlines]))
            if len(unique_dates) == 1:
                info["Application Deadline (Winter)"] = unique_dates[0]
            elif len(unique_dates) > 1:
                info["Application Deadline (Winter)"] = unique_dates[0]
                info["Application Deadline (Summer)"] = unique_dates[1]
                
        # 7. English requirements
        ielts_match = re.search(r'IELTS\s*(?:score\s*of|minimum\s*of|score)?\s*([567]\.?\d?)', text, re.IGNORECASE)
        toefl_match = re.search(r'TOEFL\s*(?:score\s*of|minimum\s*of|score|iBT)?\s*(\d{2,3})', text, re.IGNORECASE)
        lang_reqs = []
        if ielts_match:
            lang_reqs.append(f"IELTS {ielts_match.group(1)}")
        if toefl_match:
            lang_reqs.append(f"TOEFL {toefl_match.group(1)}")
        if lang_reqs:
            info["English Test Requirement"] = " / ".join(lang_reqs)
            
        # 8. GRE requirement
        if "gre" in text_lower or "gmat" in text_lower:
            if "not required" in text_lower or "optional" in text_lower:
                info["GRE/GMAT Required"] = "Optional"
            else:
                info["GRE/GMAT Required"] = "Yes"
        else:
            info["GRE/GMAT Required"] = "No"
            
        # 9. Program Duration
        dur_match = re.search(r'(\d)\s*semesters', text_lower)
        if dur_match:
            info["Program Duration (semesters)"] = f"{dur_match.group(1)} semesters"

        # 10. Acceptance Rate
        rate_match = re.search(
            r'(?:acceptance|admission)\s*(?:rate)?\s*[:\-]?\s*(?:approximately|about|around|~)?\s*([\d.]+)\s*[%]',
            text, re.IGNORECASE
        )
        if rate_match:
            info["Acceptance Rate"] = f"{rate_match.group(1)}%"

        # 11. RA/TA Positions
        if re.search(r'HiWi|teaching assistant|research assistant|student assistant|wissenschaftliche Hilfskraft', text, re.IGNORECASE):
            hours_match = re.search(r'(\d+)\s*(?:-?\s*\d+)?\s*(?:hours|hrs|h)\s*(?:per|/)\s*(?:week|wk)', text, re.IGNORECASE)
            if hours_match:
                info["RA/TA Positions"] = f"Available ({hours_match.group(0)})"
            else:
                info["RA/TA Positions"] = "Available (check department)"

        # 12. Cost of Living (maps to existing column "Cost of Living (monthly EUR/USD)")
        col_match = re.search(
            r'(?:cost\s*of\s*living|living\s*costs|living\s*expenses)\s*[:\-]?\s*(?:approximately|about|around|~)?\s*(?:€|EUR|euro)?\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s*month|/month|monthly)',
            text, re.IGNORECASE
        )
        if col_match:
            info["Cost of Living (monthly EUR/USD)"] = f"€{col_match.group(1).replace(',', '')}/month"

        # 13. Housing Options
        housing_info = []
        dorm_match = re.search(
            r'(?:dormitor|housing|accommodation|studentwohnheim)\s*(?:ies|y|s)?\s*(?:are|is|:)?\s*(?:available|from)?\s*(?:€|EUR)?\s*(\d[\d.,]*)\s*(?:-|to)\s*(?:€|EUR)?\s*(\d[\d.,]*)\s*(?:per\s*month|/month)',
            text, re.IGNORECASE
        )
        if dorm_match:
            housing_info.append(f"Dormitories: {dorm_match.group(0)}")
        if re.search(r'private\s+housing|private\s+accommodation|wg|apartment', text, re.IGNORECASE):
            housing_info.append("Private housing available")
        if housing_info:
            info["Housing Options"] = " | ".join(housing_info)

        # 14. Program Structure
        struct_parts = []
        sem_count = re.search(r'(\d+)\s*semesters?', text_lower)
        if sem_count:
            struct_parts.append(f"{sem_count.group(1)} semesters")
        if re.search(r'thesis', text_lower):
            struct_parts.append("Thesis required")
        if re.search(r'coursework|course\s*work', text_lower):
            struct_parts.append("Coursework")
        if struct_parts:
            info["Program Structure"] = ", ".join(struct_parts)

        # 15. Prerequisites (merge into Admission Requirements if that column exists)
        prereq_match = re.search(
            r'(?:prerequisite|prerequisites|required\s*background|previous\s*(?:degree|coursework)|prior\s*knowledge)\s*[:\-]?\s*(.*?)(?:\.|$)(?:\s|$)',
            text, re.IGNORECASE
        )
        if prereq_match:
            prereq_text = prereq_match.group(1).strip()[:200]
            if prereq_text:
                info["Prerequisite Courses"] = prereq_text

        # 16. Department Contact
        dept_email = re.search(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(?:edu|de|ch|uk|sg|ca|au)\b',
            text
        )
        if dept_email:
            email_val = dept_email.group(0)
            if "admission" in email_val.lower() or "apply" in email_val.lower() or "info" in email_val.lower():
                info["Department Contact"] = email_val

        return info


class ProfessorResearcherAgent(BaseAgent):
    def __init__(self, sheets_client=None):
        super().__init__("ProfessorResearcherAgent", sheets_client, interactive=False)
        self.paper_scraper = PaperScraper()

    def research(self, name, university, current_data):
        self.log(f"Starting deep search for followed advisor: {name} at {university}")
        extracted = {}
        
        # 1. Scrape Google Scholar papers if Google Scholar URL is available or can be found
        scholar_url = current_data.get("google_scholar_url") or current_data.get("scholar_url")
        
        if is_placeholder(scholar_url):
            # Try to find their Google Scholar profile URL
            self.log(f"  Searching Google Scholar profile for: {name}")
            scholar_search = self.search_web(f"{name} {university} Google Scholar profile", num_results=2)
            for res in scholar_search:
                link = res.get("url", "")
                if "scholar.google." in link and ("user=" in link or "citations?" in link):
                    scholar_url = link
                    extracted["Google Scholar URL"] = link
                    self.log(f"  Found Scholar URL: {link}")
                    break
                    
        if scholar_url and scholar_url.startswith("http"):
            self.log(f"  Scraping Google Scholar profile page...")
            try:
                soup = self.fetch_page(scholar_url)
                if soup:
                    # Citations count & h-index
                    std_fields = soup.select(".gsc_rsb_std")
                    if len(std_fields) >= 3:
                        extracted["Google Scholar Citations"] = std_fields[0].get_text(strip=True)
                        extracted["h-index"] = std_fields[2].get_text(strip=True)
                        self.log(f"  Stats: Citations={std_fields[0].text}, h-index={std_fields[2].text}")
                    
                    # Scrape papers
                    papers = self.paper_scraper.scrape_google_scholar(scholar_url, max_papers=10)
                    if papers:
                        extracted["_deep_papers"] = papers
                        # Update top 3 publications summary string
                        top_3 = [p["title"] for p in papers[:3]]
                        extracted["Recent Publications (top 3)"] = " | ".join(top_3)
            except Exception as e:
                self.log(f"  Scholar scraping error: {e}")

        # 2. General web research for email, research group, and active funding
        query1 = f"{name} {university} faculty website email research interests open positions"
        search_results1 = self.search_web(query1, num_results=3)

        # 3. Lab and project research
        query2 = f"{name} {university} lab research group projects open positions"
        search_results2 = self.search_web(query2, num_results=3)

        all_results = (search_results1 or []) + (search_results2 or [])
        combined_text = ""
        urls_visited = []
        seen_urls = set()
        for r in all_results:
            url = r.get("url")
            if url and url.startswith("http") and "scholar.google" not in url and url not in seen_urls:
                seen_urls.add(url)
                self.log(f"  Scraping: {url[:60]}")
                soup = self.fetch_page(url)
                if soup:
                    urls_visited.append(url)
                    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        tag.decompose()
                    combined_text += " " + soup.get_text(separator=" ")

        if combined_text:
            parsed = self.parse_professor_text(combined_text)
            extracted.update(parsed)

        if urls_visited and (is_placeholder(current_data.get("profile_page_url")) or is_placeholder(current_data.get("profile_url"))):
            extracted["Profile Page URL"] = urls_visited[0]

        return extracted

    def parse_professor_text(self, text):
        info = {}
        text_lower = text.lower()
        
        # 1. Email extraction
        emails = self.extract_emails(text)
        if emails:
            # Filter out non-personal or placeholder emails
            valid_emails = [e for e in emails if "ref" not in e and "webmaster" not in e and "support" not in e]
            if valid_emails:
                info["Email"] = valid_emails[0]
                
        # 2. Research interests
        interests = []
        keywords = ["machine learning", "deep learning", "neural networks", "computer vision", 
                    "natural language processing", "reinforcement learning", "statistics", "data science",
                    "causal inference", "graph neural networks", "optimization", "bayesian"]
        for kw in keywords:
            if kw in text_lower:
                interests.append(kw.title())
        if interests:
            info["Research Interests (full list)"] = ", ".join(interests[:6])
            
        # 3. Lab / Group
        group_match = re.search(r'([A-Za-z0-9\s\-]+(?:Lab|Group|Institute|Chair of Machine Learning|Chair of Computer Vision))', text)
        if group_match:
            info["Research Group / Lab"] = group_match.group(1).strip()
            
        # 4. Funding Available / Open PhD
        funding_terms = ["openings", "phd positions", "open positions", "funding available", "hiring", "join my lab"]
        if any(term in text_lower for term in funding_terms):
            info["Funding Available"] = "Yes (Openings/Funding mentioned on website)"
        else:
            info["Funding Available"] = "Check with professor"

        # 5. Open Positions (detailed)
        pos_candidates = []
        pos_patterns = [
            r'(\d+\s*(?:PhD|postdoc|master|student|research)\s*(?:position|opening|fellowship))',
            r'(?:open\s+positions?|hiring|we\s+are\s+looking\s+for)\s*[:\-]?\s*(.*?(?:PhD|postdoc|student).*?)(?:\.|$)',
        ]
        for pat in pos_patterns:
            pos_match = re.search(pat, text, re.IGNORECASE)
            if pos_match:
                pos_candidates.append(pos_match.group(0).strip()[:200])
        if pos_candidates:
            info["Open Positions"] = " | ".join(pos_candidates[:2])

        # 6. Lab Website
        lab_url_match = re.search(
            r'(?:lab\s*website|group\s*website|lab\s*page|group\s*page)\s*[:\-]?\s*(https?://[^\s,;]+)',
            text, re.IGNORECASE
        )
        if not lab_url_match:
            lab_url_match = re.search(
                r'(https?://[^\s,;]+(?:lab|group|institute)[^\s,;]*)',
                text, re.IGNORECASE
            )
        if lab_url_match:
            candidate = lab_url_match.group(1).strip().rstrip(".)")
            if "scholar.google" not in candidate:
                info["Lab Website"] = candidate

        # 7. Past PhD Students / Alumni
        alumni_match = re.search(
            r'(?:past\s+(?:PhD|graduate|doctoral)\s+students?|alumni|former\s+(?:PhD|group)\s+members?)\s*[:\-]?\s*(.*?)(?:\.|$)(?:\s|$)',
            text, re.IGNORECASE
        )
        if alumni_match:
            info["Past PhD Students"] = alumni_match.group(1).strip()[:200]

        # 8. Research Projects
        proj_match = re.search(
            r'(?:current\s+projects?|research\s+projects?|active\s+projects?|funded\s+projects?)\s*[:\-]?\s*(.*?)(?:\.\s*(?:We|The|Our|I\s)|$)',
            text, re.IGNORECASE | re.DOTALL
        )
        if proj_match:
            proj_text = proj_match.group(1).strip()[:300]
            if proj_text and len(proj_text) > 10:
                info["Research Projects"] = proj_text

        return info


class SavedTargetsResearchManager:
    def __init__(self, sheets_client=None):
        self.sheets = sheets_client
        self.scholarship_agent = ScholarshipResearcherAgent(sheets_client)
        self.university_agent = UniversityResearcherAgent(sheets_client)
        self.professor_agent = ProfessorResearcherAgent(sheets_client)
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"  [{timestamp}] [TargetsManager] {message}")

    def load_json(self, filename):
        path = os.path.join(self.data_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_json(self, filename, data):
        path = os.path.join(self.data_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _ensure_columns(self, headers, rows, new_details):
        added = 0
        for col_name in new_details:
            exists = False
            for h in headers:
                if h.lower().strip() == col_name.lower().strip():
                    exists = True
                    break
            if not exists:
                headers.append(col_name)
                for row in rows:
                    row.append("")
                added += 1
        return added

    def run_priority_research(self, set_progress_callback=None):
        self.log("Loading followed target configurations...")
        followed = self.load_json("followed.json")
        if not followed:
            self.log("No followed targets saved yet.")
            if set_progress_callback:
                set_progress_callback("Done! No followed targets to scan.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. RESEARCH FOLLOWED SCHOLARSHIPS
        followed_scholarships = followed.get("scholarships", [])
        if followed_scholarships:
            self.log(f"Found {len(followed_scholarships)} followed scholarships to research.")
            sch_db = self.load_json("scholarships.json")
            if sch_db and len(sch_db) > 1:
                headers = sch_db[0]
                rows = sch_db[1:]
                
                # Create key map
                key_map = {}
                for idx, h in enumerate(headers):
                    key_map[h.lower().strip()] = idx
                    
                name_idx = key_map.get("scholarship name") or key_map.get("name")
                
                for sname in followed_scholarships:
                    if set_progress_callback:
                        set_progress_callback(f"Researching details for scholarship: {sname[:40]}...")
                        
                    # Find existing row
                    matching_row = None
                    matching_idx = -1
                    for idx, row in enumerate(rows):
                        if name_idx is not None and idx < len(rows) and len(row) > name_idx:
                            if row[name_idx].strip().lower() == sname.strip().lower():
                                matching_row = row
                                matching_idx = idx
                                break
                                
                    current_dict = {}
                    if matching_row:
                        for h, pos in key_map.items():
                            if pos < len(matching_row):
                                current_dict[h] = matching_row[pos]
                                
                    new_details = self.scholarship_agent.research(sname, current_dict)
                    
                    # Update fields in matching_row
                    if matching_row and new_details:
                        self._ensure_columns(headers, rows, new_details)
                        for col_name, val in new_details.items():
                            c_idx = -1
                            for pos, h in enumerate(headers):
                                if h.lower().strip() == col_name.lower().strip():
                                    c_idx = pos
                                    break
                            if c_idx != -1 and c_idx < len(matching_row):
                                # Overwrite only if placeholder or empty
                                if is_placeholder(matching_row[c_idx]) or col_name in ["Deadline End", "Deadline Start"]:
                                    matching_row[c_idx] = str(val)
                        
                        # Set update timestamp
                        lu_idx = -1
                        for pos, h in enumerate(headers):
                            if "last updated" in h.lower().strip():
                                lu_idx = pos
                                break
                        if lu_idx != -1 and lu_idx < len(matching_row):
                            matching_row[lu_idx] = timestamp
                            
                sch_db[1:] = rows
                self.save_json("scholarships.json", sch_db)
                if self.sheets:
                    try:
                        self.sheets.sync_table("Scholarships", headers, rows)
                    except Exception as e:
                        self.log(f"Sync Scholarships error: {e}")

        # 2. RESEARCH FOLLOWED UNIVERSITIES
        followed_universities = followed.get("universities", [])
        if followed_universities:
            self.log(f"Found {len(followed_universities)} followed universities to research.")
            uni_db = self.load_json("universities.json")
            if uni_db and len(uni_db) > 1:
                headers = uni_db[0]
                rows = uni_db[1:]
                
                key_map = {}
                for idx, h in enumerate(headers):
                    key_map[h.lower().strip()] = idx
                    
                name_idx = key_map.get("university name") or key_map.get("name")
                prog_idx = key_map.get("program name") or key_map.get("program")
                
                for uname in followed_universities:
                    # Find all rows matching this university
                    matching_rows = []
                    for idx, row in enumerate(rows):
                        if name_idx is not None and len(row) > name_idx:
                            if row[name_idx].strip().lower() == uname.strip().lower():
                                matching_rows.append((idx, row))
                                
                    for idx, row in matching_rows:
                        program = row[prog_idx] if prog_idx is not None and len(row) > prog_idx else "MSc Data Science"
                        if set_progress_callback:
                            set_progress_callback(f"Researching program requirements: {uname[:25]} ({program[:20]})...")
                            
                        current_dict = {}
                        for h, pos in key_map.items():
                            if pos < len(row):
                                current_dict[h] = row[pos]
                                
                        new_details = self.university_agent.research(uname, program, current_dict)
                        
                        if new_details:
                            self._ensure_columns(headers, rows, new_details)
                            for col_name, val in new_details.items():
                                c_idx = -1
                                for pos, h in enumerate(headers):
                                    if h.lower().strip() == col_name.lower().strip():
                                        c_idx = pos
                                        break
                                if c_idx != -1 and c_idx < len(row):
                                    if is_placeholder(row[c_idx]) or col_name in ["Application Deadline (Winter)", "Application Deadline (Summer)"]:
                                        row[c_idx] = str(val)
                                        
                            lu_idx = -1
                            for pos, h in enumerate(headers):
                                if "last updated" in h.lower().strip():
                                    lu_idx = pos
                                    break
                            if lu_idx != -1 and lu_idx < len(row):
                                row[lu_idx] = timestamp
                                
                uni_db[1:] = rows
                self.save_json("universities.json", uni_db)
                if self.sheets:
                    try:
                        self.sheets.sync_table("Universities", headers, rows)
                    except Exception as e:
                        self.log(f"Sync Universities error: {e}")

        # 3. RESEARCH FOLLOWED PROFESSORS
        followed_professors = followed.get("professors", [])
        if followed_professors:
            self.log(f"Found {len(followed_professors)} followed professors to research.")
            prof_db = self.load_json("professors.json")
            papers_cache = self.load_json("papers_cache.json")
            if not isinstance(papers_cache, dict):
                papers_cache = {}
                
            if prof_db and len(prof_db) > 1:
                headers = prof_db[0]
                rows = prof_db[1:]
                
                key_map = {}
                for idx, h in enumerate(headers):
                    key_map[h.lower().strip()] = idx
                    
                name_idx = key_map.get("professor name") or key_map.get("name")
                uni_idx = key_map.get("university name") or key_map.get("university")
                
                for pname in followed_professors:
                    if set_progress_callback:
                        set_progress_callback(f"Scraping publications & website for: {pname[:35]}...")
                        
                    matching_row = None
                    matching_idx = -1
                    for idx, row in enumerate(rows):
                        if name_idx is not None and len(row) > name_idx:
                            if row[name_idx].strip().lower() == pname.strip().lower():
                                matching_row = row
                                matching_idx = idx
                                break
                                
                    current_dict = {}
                    if matching_row:
                        for h, pos in key_map.items():
                            if pos < len(matching_row):
                                current_dict[h] = matching_row[pos]
                                
                    university = current_dict.get("university name") or current_dict.get("university") or ""
                    
                    new_details = self.professor_agent.research(pname, university, current_dict)
                    
                    if new_details:
                        # Extract deep papers and cache them
                        if "_deep_papers" in new_details:
                            papers_cache[pname] = new_details.pop("_deep_papers")
                        
                        self._ensure_columns(headers, rows, new_details)
                        for col_name, val in new_details.items():
                            c_idx = -1
                            for pos, h in enumerate(headers):
                                if h.lower().strip() == col_name.lower().strip():
                                    c_idx = pos
                                    break
                            if c_idx != -1 and c_idx < len(matching_row):
                                if is_placeholder(matching_row[c_idx]) or col_name in ["Google Scholar Citations", "h-index", "Recent Publications (top 3)"]:
                                    matching_row[c_idx] = str(val)
                                    
                        lu_idx = -1
                        for pos, h in enumerate(headers):
                            if "last updated" in h.lower().strip():
                                lu_idx = pos
                                break
                        if lu_idx != -1 and lu_idx < len(matching_row):
                            matching_row[lu_idx] = timestamp
                            
                prof_db[1:] = rows
                self.save_json("professors.json", prof_db)
                self.save_json("papers_cache.json", papers_cache)
                if self.sheets:
                    try:
                        self.sheets.sync_table("Professors", headers, rows)
                    except Exception as e:
                        self.log(f"Sync Professors error: {e}")

        if set_progress_callback:
            set_progress_callback(f"Done! Updated followed target lists.")
