from agents.base import BaseAgent
from storage.mastery_db import MasteryDB
from datetime import datetime
import re, json, os


def get_groq_client():
    try:
        from groq import Groq
    except ImportError:
        return None
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        try:
            import dotenv
            dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.env'))
            api_key = os.environ.get("GROQ_API_KEY")
        except Exception:
            pass
    if not api_key:
        return None
    try:
        return Groq(api_key=api_key)
    except Exception:
        return None


# ─── Official pages for dynamic deadline/requirement scraping ───
SCHOLARSHIP_URLS = {
    "erasmus-mundus": {
        "official": "https://erasmus-plus.ec.europa.eu/opportunities/opportunities-for-individuals/students/erasmus-mundus-joint-masters",
        "apply": "https://erasmus-plus.ec.europa.eu/opportunities/opportunities-for-individuals/students/erasmus-mundus-joint-masters",
    },
    "daad": {
        "official": "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
        "apply": "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
    },
    "fulbright": {
        "official": "https://bd.usembassy.gov/education/fulbright/",
        "apply": "https://bd.usembassy.gov/education/fulbright/",
    },
    "commonwealth": {
        "official": "https://cscuk.fcdo.gov.uk/scholarships/commonwealth-masters-scholarships/",
        "apply": "https://cscuk.fcdo.gov.uk/",
    },
    "eiffel": {
        "official": "https://www.campusfrance.org/en/the-eiffel-scholarship-program",
        "apply": "https://www.campusfrance.org/en/the-eiffel-scholarship-program",
    },
    "chevening": {
        "official": "https://www.chevening.org/",
        "apply": "https://www.chevening.org/apply/",
    },
    "australian-rtp": {
        "official": "https://www.education.gov.au/research-block-grants/research-training-program",
        "apply": "https://www.education.gov.au/research-block-grants/research-training-program",
    },
    "italian-maeci": {
        "official": "https://www.esteri.it/en/opportunita/borse-di-studio/",
        "apply": "https://www.esteri.it/en/opportunita/borse-di-studio/",
    },
}

SCHOLARSHIP_NEWS_QUERIES = {
    "erasmus-mundus": [
        '"Erasmus Mundus" 2025 deadline',
        '"Erasmus Mundus" new programs 2025',
        '"Erasmus Mundus" update application',
        '"Erasmus Mundus" announcement',
    ],
    "daad": [
        '"DAAD scholarship" deadline 2025 Bangladesh',
        '"DAAD" new program development-related',
        '"DAAD" announcement 2025',
        '"DAAD" update application',
    ],
    "fulbright": [
        '"Fulbright" Bangladesh deadline 2025',
        '"Fulbright" program update',
        '"Fulbright" new announcement',
    ],
    "commonwealth": [
        '"Commonwealth scholarship" deadline 2025',
        '"Commonwealth" new announcement',
        '"Commonwealth" CSC update',
    ],
    "eiffel": [
        '"Eiffel scholarship" deadline 2025 France',
        '"Campus France" Eiffel new announcement',
        '"Eiffel Excellence" update',
    ],
    "chevening": [
        '"Chevening" deadline 2025',
        '"Chevening" new announcement',
        '"Chevening" update application',
    ],
    "australian-rtp": [
        '"Research Training Program" deadline 2025',
        '"Australian RTP" new announcement',
        '"RTP stipend" update',
    ],
    "italian-maeci": [
        '"Italian government scholarship" deadline 2025',
        '"MAECI" new announcement',
        '"Italian Ministry" scholarship update',
    ],
}


class MasteryAgent(BaseAgent):
    TARGET_SCHOLARSHIPS = [
        "Erasmus Mundus Joint Masters (EMJM)",
        "DAAD Development-Related Postgraduate Scholarship",
        "Fulbright Foreign Student Program (Bangladesh)",
        "Commonwealth Masters Scholarships",
        "Eiffel Excellence Scholarship",
        "Chevening Scholarships",
        "Australian Government Research Training Program (RTP)",
        "Italian Government Scholarships (MAECI)",
    ]

    def __init__(self, sheets_client=None, interactive=True):
        super().__init__("MasteryAgent", sheets_client, interactive)
        self.db = MasteryDB()

    def seed_if_empty(self):
        existing = self.db.get_all_scholarships()
        if existing:
            self.log(f"Database already has {len(existing)} scholarships, skipping seed.")
            return False
        self.run_full_scan(seed_only=True)
        return True

    def run_full_scan(self, seed_only=False, progress_callback=None):
        def progress(msg):
            self.log(msg)
            if progress_callback:
                progress_callback(msg)

        progress("Seeding scholarship database...")
        self._seed_all()

        if not seed_only:
            progress("Scraping applicant stories...")
            self.run_scrape_all(progress_callback=progress)

        progress(f"Done! {len(self.TARGET_SCHOLARSHIPS)} scholarships seeded.")
        return True

    def run_refresh_scan(self, progress_callback=None):
        def progress(msg):
            self.log(msg)
            if progress_callback:
                progress_callback(msg)

        progress("Refreshing: scraping new applicant stories...")
        self.run_scrape_all(progress_callback=progress, seen_urls=self._existing_source_urls())
        progress("Enriching data from official pages and news...")
        self.run_enrich_all(progress_callback=progress)
        progress("Refresh complete.")
        return True

    def _existing_source_urls(self):
        urls = set()
        for s in self.db.get_all_scholarships():
            detail = self.db.get_scholarship(s["slug"])
            if detail and detail.get("applicants"):
                for a in detail["applicants"]:
                    if a.get("source_url"):
                        urls.add(a["source_url"].strip().lower().rstrip("/"))
        return urls

    def _seed_all(self):
        for slug, data_func in [
            ("erasmus-mundus", self._seed_erasmus),
            ("daad", self._seed_daad),
            ("fulbright", self._seed_fulbright),
            ("commonwealth", self._seed_commonwealth),
            ("eiffel", self._seed_eiffel),
            ("chevening", self._seed_chevening),
            ("australian-rtp", self._seed_australian_rtp),
            ("italian-maeci", self._seed_italian_maeci),
        ]:
            s = self.db.get_scholarship(slug)
            if s:
                self.db.clear_applicants(s["id"])
                self.db.clear_tips(s["id"])
            data_func()

    # ─── Dynamic Enrichment: Official Page Scraping ──────────

    def _scrape_official_updates(self, slug):
        """Scrape official scholarship page for deadline/requirement updates."""
        urls = SCHOLARSHIP_URLS.get(slug, {})
        official_url = urls.get("official", "")
        if not official_url:
            return []
        updates = []
        try:
            soup = self.fetch_page(official_url, cache=False)
            if soup:
                page_text = soup.get_text(separator=" ", strip=True)[:5000]
                patterns = [
                    r'deadline[:\s]+(\w+\s+\d{4})',
                    r"application[:\s]+(\w+\s+\d{1,2}[,']{0,2}\s*\d{4})",
                    r'closes?[:\s]+(\w+\s+\d{1,2}\s*\d{4})',
                    r'open[:\s]+(\w+\s+\d{1,2}\s*\d{4})',
                    r'(\d{1,2}\s+\w+\s+\d{4})',
                ]
                for pat in patterns:
                    matches = re.findall(pat, page_text, re.IGNORECASE)
                    for m in matches[:2]:
                        updates.append({
                            "source": official_url,
                            "text": f"Found on page: {m.strip()}",
                            "type": "deadline_hint",
                        })
                if not updates:
                    updates.append({
                        "source": official_url,
                        "text": "Page scraped successfully but no deadline text detected. Visit official page directly.",
                        "type": "page_visit",
                    })
                self.log(f"  Scraped official page for {slug}: {len(updates)} hints")
        except Exception as e:
            self.log(f"  Scrape error for {slug}: {e}")
        return updates

    def _scrape_news(self, slug, full_name):
        """Search for news/updates about a scholarship."""
        queries = SCHOLARSHIP_NEWS_QUERIES.get(slug, [f'"{full_name[:30]}" update 2025'])
        news = []
        seen_titles = set()
        for q in queries[:3]:
            results = self.search_web(q, num_results=3)
            for r in results:
                title = (r.get("title", "") or "").strip()
                url = (r.get("url", "") or "").strip()
                if not title or not url:
                    continue
                key = title.lower()[:60]
                if key in seen_titles:
                    continue
                seen_titles.add(key)
                news.append({
                    "title": title[:300],
                    "url": url,
                    "snippet": (r.get("snippet", "") or "")[:400],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                })
        return news

    def _enrich_applicant_from_url(self, url, existing=None):
        """Fetch full article and use GROQ to extract structured applicant fields."""
        groq = get_groq_client()
        if not groq or not url:
            return existing or {}
        try:
            soup = self.fetch_page(url, cache=False)
            if not soup:
                return existing or {}
            content = soup.get_text(separator=" ", strip=True)[:3000]
            if len(content) < 100:
                return existing or {}
            prompt = (
                "Extract scholarship applicant info from this article. "
                "Return JSON with keys: test_scores, work_experience, publications, "
                "application_strategy, what_worked, advice. "
                "Use the article content only. Set null for unknown fields. "
                "Return ONLY the JSON."
            )
            resp = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Extract structured applicant data. Return only JSON."},
                    {"role": "user", "content": f"{prompt}\n\nArticle:\n{content[:2500]}"}
                ],
                temperature=0.1,
                max_tokens=300,
            )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r'^```(?:json)?\s*|```\s*$', '', raw, flags=re.IGNORECASE).strip()
            enriched = json.loads(raw)
            base = existing or {}
            for k in ["test_scores", "work_experience", "publications", "application_strategy", "what_worked", "advice"]:
                if enriched.get(k):
                    base[k] = enriched.get(k)
            self.log(f"  Enriched applicant from {url[:50]}...")
            return base
        except Exception as e:
            self.log(f"  Enrichment error: {e}")
            return existing or {}

    def run_enrich_all(self, progress_callback=None):
        """Scrape official pages + news + enrich applicants for all scholarships."""
        def progress(msg):
            self.log(msg)
            if progress_callback:
                progress_callback(msg)

        progress("Scraping official scholarship pages for updates...")
        total_updates = 0
        for slug, urls in SCHOLARSHIP_URLS.items():
            updates = self._scrape_official_updates(slug)
            if updates:
                for u in updates:
                    self.db.insert_news(slug, u["text"], u["source"], u["type"])
                    total_updates += 1

        progress("Searching for scholarship news...")
        total_news = 0
        for slug, queries in SCHOLARSHIP_NEWS_QUERIES.items():
            s = self.db.get_scholarship(slug)
            if not s:
                continue
            name = s.get("name", slug)
            news = self._scrape_news(slug, name)
            for n in news:
                self.db.insert_news(slug, n["title"], n["url"], "news", n["snippet"])
                total_news += 1

        progress("Enriching applicant stories with full content...")
        enriched = 0
        for s in self.db.get_all_scholarships():
            detail = self.db.get_scholarship(s["slug"])
            if not detail or not detail.get("applicants"):
                continue
            for app in detail["applicants"]:
                url = app.get("source_url", "")
                if not url or app.get("source_type") != "real":
                    continue
                if any(app.get(k) for k in ["test_scores", "work_experience", "publications", "application_strategy", "what_worked", "advice"]):
                    continue
                enriched_data = self._enrich_applicant_from_url(url, dict(app))
                if enriched_data:
                    self.db.update_applicant(app["id"], enriched_data)
                    enriched += 1

        progress(f"Enrichment done: {total_updates} page hints, {total_news} news items, {enriched} applicants enriched")
        return total_updates + total_news + enriched

    # ─── ERASMUS MUNDUS ───────────────────────────────────────

    def _seed_erasmus(self):
        sid = self.db.upsert_scholarship({
            "slug": "erasmus-mundus",
            "name": "Erasmus Mundus Joint Masters (EMJM)",
            "country": "Multi (Europe)",
            "provider": "European Commission",
            "coverage_type": "Full-Ride",
            "coverage_details": "Full tuition + 1,400 EUR/month living + travel (3,000-4,000 EUR) + installation (1,000 EUR) + health insurance",
            "amount": "16,800 + full tuition",
            "currency": "EUR",
            "degree_level": "MSc",
            "target_fields": "Multiple programs incl. Data Science, AI, ML, Statistics",
            "eligibility_nationality": "All international (including Bangladesh); no prior Erasmus scholarship",
            "eligibility_academics": "Bachelor's degree (strong academic record); less than 12 months living in program country",
            "eligibility_experience": "Not required (fresh graduates eligible)",
            "required_documents": '["Online application", "Motivation letter", "CV", "Letters of recommendation", "Academic transcripts", "English proficiency", "Research proposal (varies by program)"]',
            "application_fee": "None (varies by program: 0-90 EUR)",
            "application_language": "English",
            "english_test_required": "TOEFL 80+ / IELTS 6.5+",
            "gre_required": "Not required (some programs may ask)",
            "deadline_start": "October",
            "deadline_end": "February (varies by program)",
            "duration": "12-24 months (study at 2+ European universities)",
            "interview_required": "Possible (for shortlisted candidates)",
            "competitiveness": "Very competitive (~5-10%)",
            "application_portal": "https://erasmus-plus.ec.europa.eu/opportunities/opportunities-for-individuals/students/erasmus-mundus-joint-masters",
            "official_url": "https://erasmus-plus.ec.europa.eu/opportunities/opportunities-for-individuals/students/erasmus-mundus-joint-masters",
            "notification_date": "March-April",
            "match_score": 98,
            "strategy_notes": "PRIMARY TARGET. Find 3 EMJM programs in Data Science/AI. Apply before Feb. Study at 2+ European universities = amazing experience.",
        })

        self.db.insert_steps(sid, [
            {"step_number": 1, "phase": "Preparation", "title": "Research EMJM programs in Data Science/AI", "description": "Browse the Erasmus Mundus catalogue. Shortlist 3 programs (e.g., Euro+Data, MSC in Data Science & AI, etc.). Check eligibility, consortium universities, and language requirements.", "timeline": "12 months before deadline", "tips": "There are ~200+ EMJM programs. Filter by 'Computer Science', 'Data Science', 'Artificial Intelligence'. Read student testimonials on the program website.", "is_critical": 1},
            {"step_number": 2, "phase": "Preparation", "title": "Take English proficiency test", "description": "Register and take IELTS (target 7.0+) or TOEFL (target 95+). Most programs require IELTS 6.5+ or TOEFL 80+.", "timeline": "10 months before deadline", "tips": "IELTS Academic is preferred by most European universities. Book 2 months in advance — slots fill fast in Bangladesh.", "is_critical": 1},
            {"step_number": 3, "phase": "Preparation", "title": "Request academic transcripts and prepare documents", "description": "Collect transcripts from Dhaka College and any previous university. Get them translated and notarized if needed. Prepare passport copy, CV, and degree certificate.", "timeline": "8 months before deadline", "tips": "Start early — transcript collection in Bangladesh can take 2-4 weeks. Get multiple copies.", "is_critical": 1},
            {"step_number": 4, "phase": "Preparation", "title": "Secure 2-3 strong recommendation letters", "description": "Ask professors from Statistics/Math department who know you well. Give them your CV, statement of purpose, and program details at least 1 month before deadline.", "timeline": "6 months before deadline", "tips": "Choose recommenders who can speak to your quantitative skills and research potential. A strong letter from a Statistics professor who supervised your thesis is gold.", "is_critical": 1},
            {"step_number": 5, "phase": "Application", "title": "Write motivation letter / statement of purpose", "description": "Explain why you want to study in Europe, why this specific program, and how your Statistics background connects to Data Science. Show enthusiasm for multi-country study.", "timeline": "4 months before deadline", "tips": "EMJM values the 'European dimension' — emphasize how studying in 2+ countries will broaden your perspective. Connect to your career goals in Bangladesh.", "is_critical": 1},
            {"step_number": 6, "phase": "Application", "title": "Submit online applications", "description": "Complete the online application on the EMJM portal. Upload all documents: CV, motivation letter, transcripts, recommendation letters, English certificate. Proofread everything.", "timeline": "1-2 months before deadline", "tips": "Most EMJM programs use their own portal. Submit at least 2 weeks early — some programs have rolling review. Double-check file formats (PDF only).", "is_critical": 1},
            {"step_number": 7, "phase": "Post-Application", "title": "Prepare for interview (if shortlisted)", "description": "Some EMJM programs conduct interviews. Be ready to discuss: why this program, your background, how you'll handle multi-country study, your career plans.", "timeline": "After submission (March-April)", "tips": "Common questions: 'Why not study in your home country?', 'How will you adapt to 3 different university systems?', 'Describe a challenge you overcame.'", "is_critical": 0},
            {"step_number": 8, "phase": "Post-Application", "title": "Apply for visa and arrange travel", "description": "Once accepted, apply for student visa at the embassy of your first host country. Arrange housing, travel, and health insurance.", "timeline": "May-July (after acceptance)", "tips": "The visa process can take 4-8 weeks. Apply immediately after receiving acceptance letter. Start looking for housing early — student dorms fill fast.", "is_critical": 1},
        ])

        self.db.insert_tip(sid, {"category": "Writing", "tip": "In your motivation letter, explain WHY you chose each specific consortium program. Generic letters are immediately rejected.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Writing", "tip": "Highlight your adaptability and cross-cultural experience. Mention any travel, exchange programs, or work with diverse teams.", "priority": "medium"})
        self.db.insert_tip(sid, {"category": "Documents", "tip": "Some programs require a research proposal (2-3 pages). Check the specific requirements for each program.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Timing", "tip": "Deadlines vary by program — some as early as October, others as late as February. Create a spreadsheet tracking each program's deadline.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "General", "tip": "EMJM is NOT a single application. You apply separately to each program. Each has its own portal, requirements, and timeline.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Interview", "tip": "If interviewed, be ready to discuss how you'll adapt to living in 2-3 different European countries. Show cultural awareness.", "priority": "medium"})

    # ─── DAAD ──────────────────────────────────────────────

    def _seed_daad(self):
        sid = self.db.upsert_scholarship({
            "slug": "daad",
            "name": "DAAD Development-Related Postgraduate Scholarship",
            "country": "Germany",
            "provider": "DAAD (German Academic Exchange Service)",
            "coverage_type": "Full-Ride",
            "coverage_details": "Tuition + 934 EUR/month living + health insurance + travel allowance + rent subsidy + family allowance",
            "amount": "11,208",
            "currency": "EUR",
            "degree_level": "MSc",
            "target_fields": "All fields incl. ML, AI, Data Science, Statistics (development-related)",
            "eligibility_nationality": "Developing countries (Bangladesh eligible)",
            "eligibility_academics": "Bachelor's degree (2.5+ German grade = ~3.0+ US GPA); less than 6 years since graduation",
            "eligibility_experience": "2+ years professional experience strongly recommended",
            "required_documents": '["DAAD application form", "CV (Europass)", "Motivation letter", "Research proposal (max 5 pages)", "Letters of recommendation (2)", "Academic transcripts", "Language certificates", "Work certificates"]',
            "application_fee": "None",
            "application_language": "English or German",
            "english_test_required": "TOEFL or IELTS (score varies by program)",
            "gre_required": "Not required",
            "deadline_start": "June",
            "deadline_end": "August/September (varies by country)",
            "duration": "12-36 months",
            "interview_required": "Possible (for some programs)",
            "competitiveness": "Very competitive (~10-15%)",
            "application_portal": "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
            "official_url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
            "notification_date": "~3-5 months after deadline",
            "match_score": 95,
            "strategy_notes": "PRIMARY TARGET. Apply through DAAD portal. Strong motivation letter + research proposal critical. Highlight Statistics + ML interest.",
        })

        self.db.insert_steps(sid, [
            {"step_number": 1, "phase": "Preparation", "title": "Research eligible Master's programs in Germany", "description": "Find English-taught MSc programs in Data Science, Statistics, or ML at German universities that accept DAAD scholars. Shortlist 3-5 programs.", "timeline": "12 months before deadline", "tips": "Check DAAD's database of eligible programs. Popular choices: University of Bonn (Data Science), TU Munich (Data Engineering), University of Göttingen (Applied Statistics).", "is_critical": 1},
            {"step_number": 2, "phase": "Preparation", "title": "Gain professional/research experience", "description": "DAAD strongly prefers candidates with 2+ years of professional experience. If you don't have it, consider internships, teaching assistantships, or research projects.", "timeline": "Ongoing", "tips": "Even 1 year of experience + strong volunteer work can work. DAAD values development-related experience — highlight your Social Business or Volunteer for Bangladesh work.", "is_critical": 1},
            {"step_number": 3, "phase": "Preparation", "title": "Prepare Europass CV and academic documents", "description": "Create a Europass-format CV. Collect transcripts, degree certificates, and language certificates. Get them translated to English/German.", "timeline": "6 months before deadline", "tips": "DAAD specifically requests the Europass CV format. Download the template from Europass website.", "is_critical": 1},
            {"step_number": 4, "phase": "Application", "title": "Write the research proposal (max 5 pages)", "description": "This is the MOST critical document. Write a concrete research proposal that connects your Statistics background to a development issue in Bangladesh. Include: problem statement, methodology, timeline, expected outcomes.", "timeline": "4 months before deadline", "tips": "DAAD is development-focused. Your proposal must show how studying in Germany will help you solve problems in Bangladesh. Example: 'Using ML for crop yield prediction in Bangladesh agriculture.'", "is_critical": 1},
            {"step_number": 5, "phase": "Application", "title": "Write the motivation letter", "description": "Explain: why Germany, why this specific program, why now, and how you'll use this knowledge for Bangladesh's development. Show passion and clear purpose.", "timeline": "4 months before deadline", "tips": "DAAD wants to see: academic excellence, development commitment, leadership potential. Structure: 1) Your background, 2) Why development matters to you, 3) Why Germany, 4) Your plans.", "is_critical": 1},
            {"step_number": 6, "phase": "Application", "title": "Secure 2 recommendation letters", "description": "Ask academic referees who can speak to your academic ability AND your development interest. Give them your CV and research proposal.", "timeline": "3 months before deadline", "tips": "One academic + one professional referee is ideal. DAAD has its own recommendation form — download from the DAAD portal.", "is_critical": 1},
            {"step_number": 7, "phase": "Application", "title": "Submit DAAD application through the portal", "description": "Submit the online application. Upload all documents in the correct order. Some programs require separate university admission.", "timeline": "1 month before deadline", "tips": "DAAD application is per country. Apply through the DAAD office in Dhaka or the online portal. Check which programs need direct university application first.", "is_critical": 1},
            {"step_number": 8, "phase": "Post-Application", "title": "Apply to German universities separately", "description": "Many DAAD scholarships require you to ALSO secure admission to a German university. Apply to your target programs through uni-assist or directly.", "timeline": "April-July", "tips": "Some programs have earlier deadlines (as early as March). Don't wait for DAAD results — apply to universities simultaneously.", "is_critical": 1},
        ])

        self.db.insert_tip(sid, {"category": "Writing", "tip": "The research proposal is weighted 60%+ of your application. Spend 2-3 months writing and refining it. Get feedback from professors.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Writing", "tip": "Use the 'development-related' angle strongly. Every paragraph should connect your study to solving a problem in Bangladesh.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Documents", "tip": "Convert your GPA to the German grading system. GPA 3.0+ in Bangladesh ≈ German 2.5. DAAD requires German grade 2.5 or better.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Timing", "tip": "The DAAD application window is June-August (varies by country). For Bangladesh, check with the DAAD office in Dhaka for exact dates.", "priority": "medium"})
        self.db.insert_tip(sid, {"category": "General", "tip": "DAAD scholarships are HIGHLY competitive. Apply to 2-3 other scholarships simultaneously (Erasmus, Heinrich Boll) as backup.", "priority": "high"})

    # ─── FULBRIGHT ─────────────────────────────────────────

    def _seed_fulbright(self):
        sid = self.db.upsert_scholarship({
            "slug": "fulbright",
            "name": "Fulbright Foreign Student Program (Bangladesh)",
            "country": "USA",
            "provider": "US Department of State",
            "coverage_type": "Full-Ride",
            "coverage_details": "Full tuition + living stipend + health insurance + airfare + books + professional development",
            "amount": "40,000-60,000",
            "currency": "USD",
            "degree_level": "MSc/PhD",
            "target_fields": "All fields incl. ML, AI, Data Science, Statistics",
            "eligibility_nationality": "Bangladeshi citizens only; reside in Bangladesh; return to Bangladesh after program",
            "eligibility_academics": "Strong academic record (GPA 3.0+/4.0); Bachelor's degree completed",
            "eligibility_experience": "Leadership potential; community involvement; clear career goals for Bangladesh",
            "required_documents": '["Online application", "TOEFL/IELTS", "GRE (recommended)", "Statement of Purpose", "CV", "Letters of recommendation (3)", "Research proposal", "Interview"]',
            "application_fee": "None (application fee waived for Fulbright)",
            "application_language": "English",
            "english_test_required": "TOEFL 90+ / IELTS 6.5+",
            "gre_required": "Strongly recommended (most US universities require)",
            "deadline_start": "February",
            "deadline_end": "May (varies; check US Embassy Dhaka)",
            "duration": "12-36 months",
            "interview_required": "Yes (with US Embassy committee)",
            "competitiveness": "Very competitive (Bangladesh: ~20-30 grants/year)",
            "application_portal": "https://bd.usembassy.gov/education/fulbright/",
            "official_url": "https://bd.usembassy.gov/education/fulbright/",
            "notification_date": "~4-6 months after deadline",
            "match_score": 92,
            "strategy_notes": "USA #1 TARGET. Bangladesh-specific Fulbright program. Your Stats background + Bangladesh citizenship = eligible. Apply through US Embassy Dhaka.",
        })

        self.db.insert_steps(sid, [
            {"step_number": 1, "phase": "Preparation", "title": "Research US universities and programs", "description": "Identify 5-10 US universities with strong Stats/Data Science/ML programs. Consider: Carnegie Mellon, Georgia Tech, UW, UIUC, UCLA, U Michigan.", "timeline": "12 months before deadline", "tips": "Fulbright places you at US universities. You can suggest preferences. Georgia Tech is more attainable than Stanford. Balance reach and safety.", "is_critical": 1},
            {"step_number": 2, "phase": "Preparation", "title": "Take TOEFL/IELTS and GRE", "description": "Register and take TOEFL (target 95+) or IELTS (target 7.0+). Take GRE (target 320+ overall, 165+ quant).", "timeline": "10 months before deadline", "tips": "Fulbright strongly recommends GRE. Most US Stats/ML programs require it. Start quant prep early — Math Olympiad background helps.", "is_critical": 1},
            {"step_number": 3, "phase": "Preparation", "title": "Build leadership profile and community involvement", "description": "Fulbright values leadership. Document volunteer work, extracurricular activities, Math Olympiad, Social Business project. Get letters of appreciation.", "timeline": "Ongoing", "tips": "Your Math Olympiad participation + Volunteer for Bangladesh work are strong assets. Quantify impact: 'Taught 50+ students', 'Organized 3 events'.", "is_critical": 1},
            {"step_number": 4, "phase": "Application", "title": "Write Statement of Purpose", "description": "Explain: why USA, why this field, why you (your unique background), and how you'll contribute to Bangladesh after returning. Show leadership and vision.", "timeline": "4 months before deadline", "tips": "Fulbright specifically wants to see: academic excellence, leadership, community engagement, AND commitment to return to Bangladesh. Don't skip any of these 4 elements.", "is_critical": 1},
            {"step_number": 5, "phase": "Application", "title": "Secure 3 strong recommendation letters", "description": "Choose recommenders who can speak to: (1) academic ability, (2) leadership potential, (3) community involvement. Ideally mix of professors and supervisors.", "timeline": "3 months before deadline", "tips": "Give your recommenders your CV, SOP, and Fulbright program info. Ask 2 months before deadline. Follow up politely.", "is_critical": 1},
            {"step_number": 6, "phase": "Application", "title": "Complete Fulbright online application", "description": "Submit through the Fulbright online portal (IIE). Upload all documents: SOP, CV, transcripts, test scores, recommendations.", "timeline": "2 months before deadline", "tips": "The Fulbright application is comprehensive. Start early and proofread everything. Use the 'Bangladesh' connection throughout.", "is_critical": 1},
            {"step_number": 7, "phase": "Post-Application", "title": "Prepare for Fulbright interview", "description": "If shortlisted, you'll be interviewed by the US Embassy Dhaka selection committee. Be ready to discuss: your plans, Bangladesh development, leadership experience.", "timeline": "After submission (September-November)", "tips": "Interviews are in-person at the US Embassy Dhaka. Dress professionally. Be confident and articulate. Show genuine commitment to Bangladesh.", "is_critical": 1},
            {"step_number": 8, "phase": "Post-Application", "title": "Apply to US universities separately", "description": "Fulbright requires you to ALSO get admission to US universities. Apply to 5-10 programs. Some universities also require TA/RA applications.", "timeline": "October-February", "tips": "Many Fulbright scholars also apply for university-specific funding. Georgia Tech has strong TA/RA opportunities for Stats students.", "is_critical": 1},
        ])

        self.db.insert_tip(sid, {"category": "Writing", "tip": "Your SOP must convince the committee that you'll return to Bangladesh after the program. This is non-negotiable for Fulbright.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Writing", "tip": "Structure your SOP: (1) Your academic journey, (2) Your leadership/community work, (3) Why USA and this field, (4) Your plans for Bangladesh.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Interview", "tip": "The Fulbright interview is at the US Embassy Dhaka. Common questions: 'Why Fulbright?', 'Why not study in Bangladesh?', 'Your post-return plan?'.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Timing", "tip": "Fulbright Bangladesh usually opens in February with a May deadline. Check the US Embassy Dhaka website for exact dates each year.", "priority": "medium"})
        self.db.insert_tip(sid, {"category": "General", "tip": "Only 20-30 Bangladeshis get Fulbright each year. But don't be discouraged — your profile (Statistics + leadership + development interest) is competitive.", "priority": "high"})

    # ─── COMMONWEALTH ──────────────────────────────────────

    def _seed_commonwealth(self):
        sid = self.db.upsert_scholarship({
            "slug": "commonwealth",
            "name": "Commonwealth Masters Scholarships",
            "country": "UK",
            "provider": "Commonwealth Scholarship Commission (CSC)",
            "coverage_type": "Full-Ride",
            "coverage_details": "Full tuition fees + monthly stipend (£1,347 / £1,652 in London) + round-trip flights + warm clothing allowance",
            "amount": "25,000+ tuition",
            "currency": "GBP",
            "degree_level": "MSc",
            "target_fields": "Science and technology for development (includes AI, ML, DL, CS)",
            "eligibility_nationality": "Eligible Commonwealth countries (Bangladesh included)",
            "eligibility_academics": "First class degree or upper second class (2:1) bachelor's degree",
            "eligibility_experience": "Not strictly required; fresh graduates eligible",
            "required_documents": '["References", "University admission offers", "Academic transcripts", "Development impact statement"]',
            "application_fee": "None",
            "application_language": "English",
            "english_test_required": "Determined by host university",
            "gre_required": "Not required",
            "deadline_start": "September",
            "deadline_end": "December",
            "duration": "12 months",
            "interview_required": "None (selection based on written application)",
            "competitiveness": "Very competitive (~5%)",
            "application_portal": "https://cscuk.fcdo.gov.uk/scholarships/commonwealth-masters-scholarships/",
            "official_url": "https://cscuk.fcdo.gov.uk/",
            "notification_date": "July (following year)",
            "match_score": 82,
            "strategy_notes": "STRONG RECOMMENDATION. Very generous scholarship. Focus heavily on how study in UK will help Bangladesh's technological advancement.",
        })

        self.db.insert_steps(sid, [
            {"step_number": 1, "phase": "Preparation", "title": "Research eligible UK universities and programs", "description": "Find UK universities offering 1-year MSc programs in Data Science, ML, AI, or Statistics. Top choices: Oxford, Cambridge, Imperial, UCL, Edinburgh, Manchester.", "timeline": "12 months before deadline", "tips": "You need ADMISSION to a UK university BEFORE you apply for Commonwealth. Focus on programs with strong development/technology connections.", "is_critical": 1},
            {"step_number": 2, "phase": "Preparation", "title": "Apply to UK universities", "description": "Submit applications to 3-5 target UK universities. You must have an admission offer (conditional/unconditional) to apply for Commonwealth.", "timeline": "October-December (for Fall intake)", "tips": "Commonwealth requires you to hold a university offer. Apply to programs early. Some universities have rolling admissions.", "is_critical": 1},
            {"step_number": 3, "phase": "Application", "title": "Write the Development Impact Statement", "description": "This is the most critical document. Explain: how your study will contribute to Bangladesh's development, what specific problems you'll address, and your post-study plan.", "timeline": "3 months before deadline", "tips": "Structure: (1) Development challenges in Bangladesh, (2) How your chosen field addresses these, (3) Your specific plan post-return. Be concrete — name specific organizations or projects.", "is_critical": 1},
            {"step_number": 4, "phase": "Application", "title": "Secure 2 reference letters", "description": "Ask academic referees who can attest to your academic ability and your commitment to development. One reference from a supervisor who knows your development work is ideal.", "timeline": "2 months before deadline", "tips": "Commonwealth has its own reference template. Download it from the CSC website and share it with your referees well in advance.", "is_critical": 1},
            {"step_number": 5, "phase": "Application", "title": "Submit Commonwealth Scholarship application", "description": "Complete the online application through the CSC portal. Include: personal details, academic background, proposed study, development impact statement, references.", "timeline": "1 month before deadline", "tips": "The CSC portal opens in September. Submit early — the system can get busy near the December deadline.", "is_critical": 1},
            {"step_number": 6, "phase": "Post-Application", "title": "Wait for selection results", "description": "Selection takes 4-6 months. Results announced in July. If selected, start visa process immediately.", "timeline": "January-July", "tips": "No interview — selection is purely on written application. The Development Impact Statement carries the most weight.", "is_critical": 0},
        ])

        self.db.insert_tip(sid, {"category": "Writing", "tip": "The Development Impact Statement is weighted higher than your grades. Make it specific, measurable, and tied to Bangladesh's national development priorities.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Timing", "tip": "You need a UK university offer BEFORE applying for Commonwealth. Apply to universities August-October, then Commonwealth September-December.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Documents", "tip": "Some UK universities have earlier deadlines. Oxford and Cambridge typically close in January for Fall intake. Plan accordingly.", "priority": "medium"})
        self.db.insert_tip(sid, {"category": "General", "tip": "Commonwealth is a 'no interview' scholarship — your entire application stands on documents. The Development Impact Statement and references must be flawless.", "priority": "high"})

    # ─── EIFFEL ────────────────────────────────────────────

    def _seed_eiffel(self):
        sid = self.db.upsert_scholarship({
            "slug": "eiffel",
            "name": "Eiffel Excellence Scholarship",
            "country": "France",
            "provider": "French Ministry for Europe and Foreign Affairs",
            "coverage_type": "Full-Ride",
            "coverage_details": "€1,031/month living + international airfare + housing allowance + health insurance + cultural activities",
            "amount": "12,372",
            "currency": "EUR",
            "degree_level": "MSc",
            "target_fields": "ML, AI, Data Science, Statistics, Engineering, Sciences",
            "eligibility_nationality": "International non-French students (Bangladesh eligible)",
            "eligibility_academics": "Bachelor's degree with strong academic record",
            "eligibility_experience": "Not required (fresh graduates eligible)",
            "required_documents": '["Application through French university", "CV", "Academic transcripts", "Motivation letter", "Letters of recommendation", "Research proposal", "Language certificates"]',
            "application_fee": "None (varies by university)",
            "application_language": "English or French",
            "english_test_required": "TOEFL or IELTS (varies by program)",
            "gre_required": "Not required",
            "deadline_start": "January",
            "deadline_end": "January (single deadline per year)",
            "duration": "12-24 months",
            "interview_required": "Possible (for shortlisted candidates)",
            "competitiveness": "Very competitive (~10-15%)",
            "application_portal": "https://www.campusfrance.org/en/the-eiffel-scholarship-program",
            "official_url": "https://www.campusfrance.org/en/the-eiffel-scholarship-program",
            "notification_date": "April",
            "match_score": 82,
            "strategy_notes": "PRIMARY TARGET. France's most prestigious scholarship. Covers full living costs at low-tuition French universities (€200-3,000/yr tuition). Apply THROUGH French universities.",
        })

        self.db.insert_steps(sid, [
            {"step_number": 1, "phase": "Preparation", "title": "Research French universities and programs", "description": "Find English-taught MSc programs at French universities that partner with Eiffel. Top choices: Paris-Saclay (Data Science), IP Paris (AI), Sorbonne (Statistics), Grenoble INP.", "timeline": "6 months before deadline (August-September)", "tips": "Eiffel is NOT a direct application — you apply THROUGH a French university. The university nominates you. So first get admission to a French university.", "is_critical": 1},
            {"step_number": 2, "phase": "Preparation", "title": "Contact French university admissions", "description": "Email the international admissions office of your target programs. Ask about the Eiffel nomination process. Some universities require separate application.", "timeline": "5 months before deadline", "tips": "Each French university has its own Eiffel nomination process and deadline (usually October-November, before the January Eiffel deadline).", "is_critical": 1},
            {"step_number": 3, "phase": "Application", "title": "Apply to French university for admission + Eiffel nomination", "description": "Submit your university application. Indicate your interest in Eiffel. If the university accepts you, they will nominate you for Eiffel.", "timeline": "October-November", "tips": "Apply to 2-3 French universities. If accepted, the stronger your profile, the more likely they'll nominate you. Paris-Saclay has a strong Data Science program.", "is_critical": 1},
            {"step_number": 4, "phase": "Application", "title": "Prepare Eiffel application documents", "description": "Your application must include: motivation letter, CV, transcripts, research proposal (if applicable), recommendation letters. These go through the university.", "timeline": "November-December", "tips": "The motivation letter should explain: why France, why this program, your career goals. French selection committees value academic excellence and clear vision.", "is_critical": 1},
            {"step_number": 5, "phase": "Application", "title": "University submits Eiffel nomination (deadline: January)", "description": "The university submits your application to Campus France for the Eiffel program. You don't submit directly — the university does it for you.", "timeline": "January (hard deadline)", "tips": "The January deadline is strict. Make sure your university has everything they need from you by December. Follow up with the international office.", "is_critical": 1},
            {"step_number": 6, "phase": "Post-Application", "title": "Wait for results (April)", "description": "Eiffel results are announced in April. If selected, you get the full scholarship. If not, you can still study in France with low tuition.", "timeline": "January-April", "tips": "Even if you don't get Eiffel, French university tuition is very low (€200-3,000/year). You can also apply for other French government scholarships.", "is_critical": 0},
        ])

        self.db.insert_tip(sid, {"category": "General", "tip": "Eiffel is NOT a direct application. You MUST go through a French university. First get admitted, then get nominated.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Timing", "tip": "University-specific deadlines for Eiffel nomination are often October-November. The Campus France deadline is January. Don't miss the earlier university deadline.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Writing", "tip": "The motivation letter should highlight: academic excellence, project clarity, and motivation to study in France. Show you've researched French culture and education.", "priority": "medium"})

    # ─── CHEVENING ─────────────────────────────────────────

    def _seed_chevening(self):
        sid = self.db.upsert_scholarship({
            "slug": "chevening",
            "name": "Chevening Scholarships",
            "country": "UK",
            "provider": "Foreign, Commonwealth & Development Office (FCDO)",
            "coverage_type": "Full-Ride",
            "coverage_details": "Full tuition fees + monthly stipend + round-trip flights + visa cost + arrival/departure allowance",
            "amount": "20,000+ tuition",
            "currency": "GBP",
            "degree_level": "MSc",
            "target_fields": "All fields including AI, ML, Deep Learning, and Data Science",
            "eligibility_nationality": "Chevening-eligible countries (Bangladesh included)",
            "eligibility_academics": "Upper second-class 2:1 honours degree or equivalent (GPA 3.0+/4.0)",
            "eligibility_experience": "Minimum 2 years of work experience (2,800 hours of professional work)",
            "required_documents": '["Four essays (Leadership, Networking, Study in UK, Career plans)", "2 reference letters", "University offers"]',
            "application_fee": "None; varies by UK university application",
            "application_language": "English",
            "english_test_required": "Determined by host university (IELTS 6.5+ / TOEFL 90+)",
            "gre_required": "Not required",
            "deadline_start": "August",
            "deadline_end": "November 3",
            "duration": "12 months (1-year taught masters)",
            "interview_required": "Yes (interviews at British High Commission)",
            "competitiveness": "Highly competitive (~2-3%)",
            "application_portal": "https://www.chevening.org/apply/",
            "official_url": "https://www.chevening.org/",
            "notification_date": "June (following year)",
            "match_score": 85,
            "strategy_notes": "PRIMARY TARGET. Work experience requirement is met. Tailor essays to show leadership and networking potential. Select top CS programs (Oxford, UCL, Edinburgh, Imperial).",
        })

        self.db.insert_steps(sid, [
            {"step_number": 1, "phase": "Preparation", "title": "Research UK universities and programs", "description": "Identify target UK universities for 1-year MSc in ML/AI/Data Science. Shortlist 5: Oxford, Cambridge, Imperial, UCL, Edinburgh, Manchester, KCL.", "timeline": "12 months before deadline", "tips": "Chevening doesn't require admission at application time, but having a conditional offer strengthens your application. Research programs early.", "is_critical": 1},
            {"step_number": 2, "phase": "Preparation", "title": "Document leadership and networking experience", "description": "Chevening is looking for leaders and networkers. Compile examples of: leadership roles, team management, initiatives you started, speaking events, mentoring.", "timeline": "Ongoing", "tips": "Your Math Olympiad mentoring, Volunteer for Bangladesh, and Social Business project are all leadership examples. Quantify: 'Led 10-person team', 'Organized 3 workshops'.", "is_critical": 1},
            {"step_number": 3, "phase": "Application", "title": "Write the 4 Chevening essays", "description": "The 4 required essays: (1) Leadership & Influence, (2) Networking, (3) Study in UK, (4) Career Plans. Each needs concrete examples and clear connection to UK study.", "timeline": "August-September", "tips": "Use the STAR method (Situation, Task, Action, Result) for Leadership and Networking essays. Chevening wants to SEE your impact, not just hear about it.", "is_critical": 1},
            {"step_number": 4, "phase": "Application", "title": "Secure 2 reference letters", "description": "Ask 2 people who can speak to your professional and academic abilities. At least one should be able to comment on your leadership.", "timeline": "2 months before deadline", "tips": "Choose referees who know you well and can give specific examples of your leadership. Professional referees (previous manager) are valuable.", "is_critical": 1},
            {"step_number": 5, "phase": "Application", "title": "Submit Chevening application", "description": "Complete the online application through the Chevening website. Upload essays and references. The deadline is typically November 3.", "timeline": "1 week before deadline", "tips": "The application portal opens in August. Don't wait until October to start — the essays take at least 2 months to polish.", "is_critical": 1},
            {"step_number": 6, "phase": "Post-Application", "title": "Prepare for Chevening interview", "description": "If shortlisted (February-March), you'll be interviewed at the British High Commission Dhaka. Be ready to discuss your leadership examples in depth.", "timeline": "February-March", "tips": "Common questions: 'Tell me about a time you led a team', 'How will you network as a Chevening scholar?', 'What will you do after your MSc?'. Practice with mock interviews.", "is_critical": 1},
            {"step_number": 7, "phase": "Post-Application", "title": "Apply to UK universities", "description": "Chevening requires you to hold a UK university offer before the scholarship is confirmed. Apply to 3-5 programs by April.", "timeline": "March-May", "tips": "You need at least ONE unconditional offer or conditional offer by July. Apply to programs with rolling admissions as backup.", "is_critical": 1},
        ])

        self.db.insert_tip(sid, {"category": "Writing", "tip": "The 4 Chevening essays must be cross-referenced — your career plan should connect to your leadership experience and your study choice. Tell ONE coherent story.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Writing", "tip": "The Networking essay is unique to Chevening. Show HOW you'll use the Chevening network, not just that you want to network. Name specific alumni, events, plans.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Interview", "tip": "Chevening interviews at the British High Commission Dhaka test: English fluency, leadership credibility, and career vision. Prepare 3 strong leadership stories.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Timing", "tip": "Chevening deadline is November 3 every year. Results (if shortlisted) come February-March. Interviews April-May. Final results June.", "priority": "medium"})

    # ─── AUSTRALIAN RTP ────────────────────────────────────

    def _seed_australian_rtp(self):
        sid = self.db.upsert_scholarship({
            "slug": "australian-rtp",
            "name": "Australian Government Research Training Program (RTP)",
            "country": "Australia",
            "provider": "Australian Government / Host Universities",
            "coverage_type": "Full-Ride",
            "coverage_details": "Tuition fee offset + living allowance (~$35,000 AUD/year) + Overseas Student Health Cover + relocation allowance",
            "amount": "35,000",
            "currency": "AUD",
            "degree_level": "MSc (Research) / PhD",
            "target_fields": "All research fields (strong fit for Data Science & Machine Learning)",
            "eligibility_nationality": "International students",
            "eligibility_academics": "Outstanding academic record (First Class Honours, GPA 3.7+/4.0)",
            "eligibility_experience": "Prior research experience, thesis, or peer-reviewed publications",
            "required_documents": '["Direct application to host university", "CV", "Research proposal", "Referee reports", "Supervisor agreement"]',
            "application_fee": "None",
            "application_language": "English",
            "english_test_required": "IELTS 6.5+ / TOEFL 90+",
            "gre_required": "Not required",
            "deadline_start": "April",
            "deadline_end": "August/September (varies by university)",
            "duration": "2 years (MSc Research) / 3-4 years (PhD)",
            "interview_required": "None",
            "competitiveness": "Highly competitive",
            "application_portal": "Varies by host university portal",
            "official_url": "https://www.education.gov.au/research-block-grants/research-training-program",
            "notification_date": "October-November",
            "match_score": 75,
            "strategy_notes": "Seek out research supervisors at Melbourne, Sydney, ANU, or UNSW. Publications are heavily weighted in Australian admissions.",
        })

        self.db.insert_steps(sid, [
            {"step_number": 1, "phase": "Preparation", "title": "Research supervisors at Australian universities", "description": "Find professors in ML/Data Science/Statistics at Australian universities (Melbourne, Sydney, ANU, UNSW, Monash, UQ). Review their research profiles.", "timeline": "12 months before deadline", "tips": "Australian RTP is SUPERVISOR-DRIVEN. Find a professor who wants to supervise you before you apply. Read their papers and mention them in your email.", "is_critical": 1},
            {"step_number": 2, "phase": "Preparation", "title": "Contact potential supervisors", "description": "Email 5-10 professors with: brief intro, your interest in their research, your qualifications, attached CV. Ask if they're accepting MSc Research students.", "timeline": "10 months before deadline", "tips": "Supervisor email template: (1) Who you are, (2) Why you're interested in THEIR research (be specific), (3) Your qualifications, (4) Attach CV and transcript.", "is_critical": 1},
            {"step_number": 3, "phase": "Preparation", "title": "Develop research proposal", "description": "Work with interested supervisors to develop a detailed 2-3 page research proposal. This is a critical part of the RTP application.", "timeline": "6 months before deadline", "tips": "The research proposal should be aligned with the supervisor's current projects. Australian universities want research-ready students with clear plans.", "is_critical": 1},
            {"step_number": 4, "phase": "Preparation", "title": "Take English proficiency test", "description": "Take IELTS (target 7.0+) or TOEFL (target 95+). Australian universities typically require IELTS 6.5+ with no band below 6.0.", "timeline": "5 months before deadline", "tips": "IELTS is preferred in Australia. Some universities accept PTE Academic as well.", "is_critical": 1},
            {"step_number": 5, "phase": "Application", "title": "Apply to university for admission", "description": "Submit application through the university's admissions portal. Include: transcripts, CV, research proposal, English test scores, referee reports.", "timeline": "April-August", "tips": "Most Australian universities have 2 intake rounds: Round 1 (April-June) and Round 2 (August-September). Apply early for Round 1.", "is_critical": 1},
            {"step_number": 6, "phase": "Application", "title": "Apply for RTP scholarship", "description": "The RTP application is usually part of the admission application or a separate form. Indicate your interest in the RTP stipend.", "timeline": "Same as admission application", "tips": "RTP is highly competitive. Apply for other scholarships simultaneously: university-specific scholarships, destination Australia scholarships.", "is_critical": 1},
        ])

        self.db.insert_tip(sid, {"category": "General", "tip": "RTP is supervisor-driven. Without a supervisor who wants you, your application goes nowhere. Spend 60% of your effort on finding the right supervisor.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Writing", "tip": "Your research proposal must show: (1) Understanding of the field, (2) Clear methodology, (3) Feasibility within 2 years, (4) Connection to supervisor's work.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Timing", "tip": "Australian universities have 2 main intake periods: Round 1 (April-June) and Round 2 (August-September). Apply for Round 1 for the best chance.", "priority": "medium"})

    # ─── ITALIAN MAECI ─────────────────────────────────────

    def _seed_italian_maeci(self):
        sid = self.db.upsert_scholarship({
            "slug": "italian-maeci",
            "name": "Italian Government Scholarships (MAECI)",
            "country": "Italy",
            "provider": "Italian Ministry of Foreign Affairs",
            "coverage_type": "Full-Ride",
            "coverage_details": "€900/month stipend + health insurance + tuition fee waiver",
            "amount": "10,800",
            "currency": "EUR",
            "degree_level": "MSc",
            "target_fields": "ML, AI, Data Science, Statistics, Engineering, All fields",
            "eligibility_nationality": "International students (Bangladesh eligible)",
            "eligibility_academics": "Bachelor's degree; strong academic record",
            "eligibility_experience": "Not required (fresh graduates eligible)",
            "required_documents": '["Online application", "CV", "Academic transcripts", "Motivation letter", "Letters of recommendation", "Language certificates", "Research proposal (if required)"]',
            "application_fee": "None",
            "application_language": "English or Italian",
            "english_test_required": "TOEFL or IELTS (varies by program)",
            "gre_required": "Not required",
            "deadline_start": "March",
            "deadline_end": "April (each year)",
            "duration": "6-12 months (renewable)",
            "interview_required": "Possible",
            "competitiveness": "Competitive",
            "application_portal": "https://www.esteri.it/en/opportunita/borse-di-studio/",
            "official_url": "https://www.esteri.it/en/opportunita/borse-di-studio/",
            "notification_date": "~3 months after deadline",
            "match_score": 80,
            "strategy_notes": "PRIMARY TARGET. Fully funded. Study at Politecnico di Milano, Bologna, Trento in English. ML/AI programs available. Deadline: March-April each year.",
        })

        self.db.insert_steps(sid, [
            {"step_number": 1, "phase": "Preparation", "title": "Research English-taught programs in Italy", "description": "Find MSc programs in Data Science, AI, Statistics, or Computer Engineering at Italian universities. Top picks: Politecnico di Milano (Data Science), University of Trento (AI), University of Bologna (Statistics).", "timeline": "6 months before deadline", "tips": "Italy has many English-taught programs. Politecnico di Milano's MSc Data Science is among the best in Europe. Tuition is already low (€1,000-3,000/year).", "is_critical": 1},
            {"step_number": 2, "phase": "Preparation", "title": "Take English proficiency test", "description": "Take IELTS (target 6.5+) or TOEFL (target 90+). Most Italian programs require B2 level English (IELTS 6.0+).", "timeline": "4 months before deadline", "tips": "Italian universities are more flexible on English scores than UK/US programs. IELTS 6.0+ is usually sufficient.", "is_critical": 1},
            {"step_number": 3, "phase": "Application", "title": "Prepare MAECI application documents", "description": "Prepare: CV, transcripts, motivation letter, recommendation letters, language certificate, passport copy. Some programs require a study plan or research proposal.", "timeline": "2 months before deadline", "tips": "The motivation letter should explain: why Italy, why this program, your career plans. MAECI values cultural exchange and academic excellence.", "is_critical": 1},
            {"step_number": 4, "phase": "Application", "title": "Submit MAECI online application", "description": "Complete the application on the Italian Ministry of Foreign Affairs portal (Studiare in Italia). Choose your preferred university and program.", "timeline": "March-April", "tips": "The application window is short (4-6 weeks). Prepare all documents IN ADVANCE. The portal can be slow near the deadline.", "is_critical": 1},
            {"step_number": 5, "phase": "Application", "title": "Apply to Italian university for admission (separate)", "description": "MAECI and university admission are SEPARATE processes. Apply to your target Italian university for admission as well. Some universities have different deadlines.", "timeline": "Concurrent (March-June)", "tips": "Check if your target university requires pre-enrollment. Politecnico di Milano typically has an April deadline for international students.", "is_critical": 1},
            {"step_number": 6, "phase": "Post-Application", "title": "Wait for results and arrange visa", "description": "MAECI results are announced ~3 months after deadline (June-July). If selected, apply for a student visa at the Italian Embassy in Dhaka.", "timeline": "May-August", "tips": "Italian student visa processing takes 4-6 weeks. Apply immediately after receiving the scholarship letter. You'll need: acceptance letter, scholarship proof, financial documents.", "is_critical": 1},
        ])

        self.db.insert_tip(sid, {"category": "General", "tip": "MAECI scholarship + low Italian tuition = very affordable. Even without MAECI, Italian public universities charge only €1,000-3,000/year.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Timing", "tip": "The MAECI application window is March-April (4-6 weeks). University admission deadlines are separate and often earlier. Don't miss either.", "priority": "high"})
        self.db.insert_tip(sid, {"category": "Writing", "tip": "Show genuine interest in Italy. Mention specific Italian universities, professors, or research projects. MAECI wants students who will be cultural ambassadors.", "priority": "medium"})

    # ─── FAST SCHOLARSHIP-SPECIFIC SCRAPING ─────────────

    SCHOLARSHIP_QUERIES = {
        "Erasmus Mundus": [
            "Erasmus Mundus Bangladesh scholar accepted",
            "Erasmus Mundus Indian student experience",
            "Erasmus Mundus Pakistani winner",
            "site:reddit.com Erasmus Mundus Bangladesh",
            "linkedin.com Erasmus Mundus scholar Bangladesh",
            "Erasmus Mundus Joint Masters South Asian profile",
        ],
        "DAAD": [
            "DAAD scholarship Bangladesh winner profile",
            "DAAD Indian student received scholarship",
            "DAAD Pakistani scholar Germany",
            "site:reddit.com DAAD Bangladesh accepted",
            "linkedin.com DAAD scholar Bangladesh",
            "DAAD Development-Related Postgraduate alumni Bangladesh profile",
        ],
        "Fulbright": [
            "Fulbright Bangladesh scholar university",
            "Fulbright Indian student USA",
            "Fulbright Pakistani student experience",
            "site:reddit.com Fulbright Bangladesh accepted",
            "linkedin.com Fulbright scholar Bangladesh",
            "Fulbright Foreign Student Program alumni Bangladesh",
        ],
        "Commonwealth": [
            "Commonwealth scholarship Bangladesh winner UCL",
            "Commonwealth Indian student UK scholarship",
            "Commonwealth Pakistan scholar",
            "site:reddit.com Commonwealth scholarship Bangladesh",
            "linkedin.com Commonwealth scholar Bangladesh",
        ],
        "Chevening": [
            "Chevening Bangladesh scholar Oxford",
            "Chevening Indian student UK experience",
            "Chevening Pakistani winner",
            "site:reddit.com Chevening Bangladesh accepted",
            "linkedin.com Chevening scholar Bangladesh",
        ],
        "Eiffel": [
            "Eiffel scholarship Bangladesh student France",
            "Eiffel Excellence Indian student Paris",
            "site:reddit.com Eiffel scholarship Bangladesh",
            "linkedin.com Eiffel scholar Bangladesh",
        ],
        "RTP": [
            "Research Training Program Bangladesh scholar Australia",
            "Australian RTP Indian student Melbourne",
            "site:reddit.com RTP scholarship Bangladesh",
            "linkedin.com RTP scholar Australia Bangladesh",
        ],
        "Italian MAECI": [
            "Italian government scholarship Bangladesh student",
            "MAECI scholarship Indian student Italy",
            "Politecnico Milano MAECI Bangladesh",
            "site:reddit.com Italian scholarship Bangladesh",
            "linkedin.com MAECI scholar Bangladesh",
        ],
    }

    def scrape_applicant_stories(self, scholarship_full_name, seen_urls=None):
        base = scholarship_full_name.split("(")[0].strip()
        queries = self.SCHOLARSHIP_QUERIES.get(base, [
            f'"{base}" Bangladesh scholar',
            f'"{base}" Indian student',
            f'"{base}" Pakistani winner',
        ])
        results = self.multi_search(queries, max_per_query=4)
        s = self.db.get_scholarship_by_name(base)
        if not s:
            return 0
        seen = set()
        if seen_urls is None:
            seen_urls = set()
        count = 0
        for r in results:
            title = r.get("title", "").strip()
            snippet = r.get("snippet", "").strip()
            url = r.get("url", "").strip().rstrip("/")
            text = (title + " " + snippet).lower()

            # Skip guides and generic pages
            if any(kw in text for kw in ["complete guide", "definitive guide", "step-by-step guide", "how to apply", "application process", "scholarship application", "fully funded", "all you need"]):
                continue

            # Skip already-seen URLs
            if url in seen_urls:
                continue

            # Only keep pages that mention a real person or success story
            if not any(kw in text for kw in ["received", "awarded", "scholar at", "alumnus", "alumna", "my journey", "i got", "accepted to", "selected for", "winner of", "congratulations", "profile of", "meet ", "scholar profile", "my story"]):
                continue

            # Detect country
            country = "South Asia"
            for kw, c in [("bangladesh", "Bangladesh"), ("bangladeshi", "Bangladesh"), ("dhaka", "Bangladesh"), ("buet", "Bangladesh"), ("brac", "Bangladesh"),
                          ("india", "India"), ("indian", "India"), ("iit ", "India"), ("bits ", "India"), ("iiit", "India"),
                          ("pakistan", "Pakistan"), ("pakistani", "Pakistan"), ("lahore", "Pakistan"), ("nust", "Pakistan"),
                          ("sri lanka", "Sri Lanka"), ("nepal", "Nepal")]:
                if kw in text:
                    country = c
                    break

            name = title[:100] if len(title) > 10 else f"{base} Winner"
            key = f"{name[:40]}|{snippet[:60]}"
            if key not in seen:
                seen.add(key)
                seen_urls.add(url)
                self.db.insert_applicant(s["id"], {
                    "name": name,
                    "background": snippet,
                    "source_url": url,
                    "source_type": "real",
                    "country": country,
                })
                count += 1
        return count

    def run_scrape_all(self, progress_callback=None, seen_urls=None):
        def progress(msg):
            self.log(msg)
            if progress_callback:
                progress_callback(msg)
        total = 0
        for name in self.TARGET_SCHOLARSHIPS:
            progress(f"Scraping: {name[:40]}...")
            a = self.scrape_applicant_stories(name, seen_urls)
            total += a
        progress(f"Scraped {total} new applicant records across all scholarships.")
        return total
