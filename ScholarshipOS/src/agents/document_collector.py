import os, json, re, time, hashlib
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.parse import quote_plus

from agents.base import BaseAgent

DOCUMENTS_FILE = os.path.join(
    os.path.join(os.path.dirname(__file__), '..', '..'),
    "data", "scholar_documents.json"
)

# ====================================================================
# ONLY verified repos with real scholarship application documents.
# Each entry specifies which folders to scan and what doc type to assign.
# ====================================================================
VERIFIED_REPOS = {
    # Pakistan – Mujtaba Farrukh (Erasmus Mundus, DAAD, Stipendium Hungaricum)
    "MujtabaFarrukh/Scholarship-Application-Documents": {
        "SOP": "sop",
        "Recommendation-Letters": "recommendation",
        "CV": "resume",
    },
    # Bangladesh – various students
    "tahsin-t/Scholarship-Documents": {
        "": "document",
    },
    # India – IIT/NIT SOP collections
    "karthikbhandary2/Statement-of-Purpose": {
        "": "sop",
    },
    "kushalbose92/Statement-of-Purpose-Examples": {
        "": "sop",
    },
    "khanhnamle1994/statement-of-purpose": {
        "": "sop",
    },
    "vineeths96/Statement-of-Purpose-Samples": {
        "": "sop",
    },
    # Bangladesh – BUET/DU student SOPs
    "musfiqshohan/SOP-for-MS-in-CS": {
        "": "sop",
    },
    "jayedhossain/Statement-of-Purpose-Samples": {
        "": "sop",
    },
    "shihabmuhtorum/Statement-of-Purpose-for-MS": {
        "": "sop",
    },
    "sakibsarker/Statement-of-Purpose": {
        "": "sop",
    },
    "rabbi08/Statement-of-Purpose": {
        "": "sop",
    },
    "rahatzamancse/Statement-of-Purpose": {
        "": "sop",
    },
    "nayeem119/Statement-of-Purpose": {
        "": "sop",
    },
    # India – personal SOP repos
    "manasdk/Statement-of-Purpose": {
        "": "sop",
    },
    "DhruvJawalkar/Statement-of-Purpose-Collection": {
        "": "sop",
    },
    "adityashrm21/Statement-of-Purpose-Samples": {
        "": "sop",
    },
    "rounakbanik/statement-of-purpose": {
        "": "sop",
    },
    "peeyushsinghal/SOP_GradSchool": {
        "": "sop",
    },
    "ashwinipraveen/SOPs": {
        "": "sop",
    },
    "rishavbhowmik/Statement-of-Purpose": {
        "": "sop",
    },
    # Pakistan – student SOPs
    "shehriyar/Statement-of-Purpose": {
        "": "sop",
    },
    "zainshahid/Statement-of-Purpose": {
        "": "sop",
    },
}

# ====================================================================
# KNOWN WINNERS – real people verified through Medium/blogs/personal sites
# who have publicly shared their actual scholarship application documents.
# ====================================================================
KNOWN_WINNERS = [
    # === BANGLADESH ===
    {
        "name": "Fakrul Islam Tushar",
        "country": "Bangladesh",
        "scholarship": "Erasmus Mundus MAIA (Medical Imaging and Applications)",
        "university": "Universitat de Girona (Spain) / Universite de Bourgogne (France) / Universita degli Studi di Cassino (Italy)",
        "program": "MS",
        "field": "Medical Imaging, Computer Vision",
        "type": "motivation_letter",
        "url": "https://f-i-tushar-eee.medium.com/writing-a-scholarship-awarding-motivation-letter-9337c56895f5",
        "source": "Medium Blog",
        "description": "Real Erasmus Mundus motivation letter walkthrough by a Bangladeshi winner. Includes section-by-section breakdown of his winning MOL.",
    },
    {
        "name": "Fakrul Islam Tushar",
        "country": "Bangladesh",
        "scholarship": "Erasmus Mundus MAIA",
        "university": "Multiple EU Universities",
        "program": "MS",
        "field": "Medical Imaging",
        "type": "resume",
        "url": "https://f-i-tushar-eee.medium.com/writing-a-scholarship-awarding-cv-being-a-fresh-graduate-c77cf90d9f18",
        "source": "Medium Blog",
        "description": "Real Erasmus Mundus CV guide by a Bangladeshi winner. Shows his actual CV structure as a fresh graduate with no publications.",
    },
    {
        "name": "Fakrul Islam Tushar",
        "country": "Bangladesh",
        "scholarship": "Erasmus Mundus MAIA",
        "university": "Multiple EU Universities",
        "program": "MS",
        "field": "Medical Imaging",
        "type": "sop",
        "url": "https://fitushar.netlify.app/",
        "source": "Personal Website",
        "description": "Personal website of Fakrul Islam Tushar - Bangladeshi Erasmus Mundus winner, now PhD student at Duke University.",
    },
    {
        "name": "Amena Akter (Blog curator)",
        "country": "Bangladesh",
        "scholarship": "Multiple (Erasmus Mundus, DAAD)",
        "university": "Various",
        "program": "MS/PhD",
        "field": "Fisheries, Biological Sciences",
        "type": "sop",
        "url": "http://sopsample.blogspot.com/2013/",
        "source": "Blogspot",
        "description": "Blogspot with real motivation letters and SOPs from Bangladeshi students. Includes Md. Rakeb-Ul-Islam's Erasmus Mundus motivation letter.",
    },
    {
        "name": "Tanvir Ahmmed Siyam",
        "country": "Bangladesh",
        "scholarship": "General Scholarship",
        "university": "University of Queensland (example SOP)",
        "program": "MS/PhD",
        "field": "Poultry Science",
        "type": "sop",
        "url": "https://tanvir-ahmmed-siyam.medium.com/how-to-write-a-powerful-statement-of-purpose-sop-that-gets-you-accepted-98fa6f4be481",
        "source": "Medium Blog",
        "description": "Real SOP sample with detailed structure showing a Bangladeshi student's application for MS/PhD in Poultry Science at University of Queensland.",
    },
    # === INDIA ===
    {
        "name": "Mohammad Imran Khan",
        "country": "India",
        "scholarship": "Fulbright Distinguished Award for International Teaching",
        "university": "Indiana University (Fulbright exchange)",
        "program": "Teaching Exchange",
        "field": "Education, Technology",
        "type": "sop",
        "url": "https://imranapps.medium.com/my-journey-as-a-fulbright-scholar-058dc6e79b85",
        "source": "Medium Blog",
        "description": "Real Fulbright success story from an Indian teacher. Details his application journey, personal statement approach, and research paper.",
    },
    {
        "name": "Suvodeep Sinha",
        "country": "India",
        "scholarship": "DAAD WISE",
        "university": "German University (Research Internship)",
        "program": "Research Internship",
        "field": "Engineering",
        "type": "motivation_letter",
        "url": "https://medium.com/@suvoo/the-daad-wise-scholarship-47906811f254",
        "source": "Medium Blog",
        "description": "Detailed DAAD WISE scholarship guide by an Indian student. Includes LOM tips, cold email template, and invitation letter guidance.",
    },
    {
        "name": "Vineet Kumar Singh",
        "country": "India",
        "scholarship": "German Student Visa",
        "university": "German University (admitted)",
        "program": "MS",
        "field": "General Engineering",
        "type": "motivation_letter",
        "url": "https://vsingh1233.medium.com/lom-for-german-study-visa-a5230bbb16cd",
        "source": "Medium Blog",
        "description": "Complete LOM/SOP guide for German study visa with sample letter by an Indian student.",
    },
    {
        "name": "Soumyadeep Roy",
        "country": "India",
        "scholarship": "DAAD/Erasmus+",
        "university": "Leibniz University Hannover (Research Associate)",
        "program": "PhD",
        "field": "Computer Science",
        "type": "research_proposal",
        "url": "https://medium.com/@soumyadeeproy/how-to-move-to-germany-as-a-student-for-a-research-position-27f4689528a9",
        "source": "Medium Blog",
        "description": "Guide by an Indian PhD student on securing research positions in Germany. Includes research proposal structure and DAAD application tips.",
    },
    # === PAKISTAN ===
    {
        "name": "Muhammad Sarwar",
        "country": "Pakistan",
        "scholarship": "Fulbright (Scholar/Advisor)",
        "university": "US University",
        "program": "MS/PhD",
        "field": "Computer Science",
        "type": "sop",
        "url": "https://medium.com/scholarship-forum/fulbright-personal-statement-sample-98b92fe63faa",
        "source": "Medium Blog",
        "description": "Real Fulbright Personal Statement sample from a successful Pakistani scholar. Includes full essay and structural breakdown.",
    },
    {
        "name": "Muhammad Sarwar",
        "country": "Pakistan",
        "scholarship": "Fulbright",
        "university": "US University",
        "program": "MS/PhD",
        "field": "Computer Science",
        "type": "research_proposal",
        "url": "https://medium.com/scholarship-forum/fulbright-application-essays-personal-statement-study-objective-a6aff89256a7",
        "source": "Medium Blog",
        "description": "Detailed guide differentiating Fulbright Personal Statement vs Study/Research Objective, tailored for Pakistani applicants.",
    },
    {
        "name": "Dr. Hamza Ahmad Raza",
        "country": "Pakistan",
        "scholarship": "Fulbright",
        "university": "US University",
        "program": "PhD",
        "field": "Electrical Engineering",
        "type": "sop",
        "url": "https://medium.com/age-of-awareness/how-to-write-personal-statement-for-fulbright-scholarship-677dd6da835",
        "source": "Medium Blog",
        "description": "Detailed guide on writing Fulbright Personal Statement by a Pakistani Fulbright scholar. Includes story structure and paragraph-by-paragraph advice.",
    },
    {
        "name": "Dr. Hamza Ahmad Raza",
        "country": "Pakistan",
        "scholarship": "Fulbright",
        "university": "US University",
        "program": "PhD",
        "field": "Electrical Engineering",
        "type": "research_proposal",
        "url": "https://medium.com/age-of-awareness/how-to-write-study-objectives-for-fulbright-scholarship-c6f3caa7ceb2",
        "source": "Medium Blog",
        "description": "Fulbright Study Objectives writing guide by a Pakistani Fulbright scholar. Includes paragraph structure and content recommendations.",
    },
    {
        "name": "Dr. Hamza Ahmad Raza",
        "country": "Pakistan",
        "scholarship": "Fulbright",
        "university": "US University",
        "program": "PhD",
        "field": "Electrical Engineering",
        "type": "sop",
        "url": "https://medium.com/age-of-awareness/8-months-journey-towards-fulbright-scholarship-62ac9a8967b8",
        "source": "Medium Blog",
        "description": "8-month Fulbright journey by a Pakistani scholar. Timeline, preparation strategy, essay approach, and interview experience.",
    },
    {
        "name": "Sania Ashraf",
        "country": "Pakistan",
        "scholarship": "Fulbright",
        "university": "Florida State University",
        "program": "MS",
        "field": "Computer Science",
        "type": "sop",
        "url": "https://medium.com/@shahwani786/sania-ashrafs-inspirational-journey-from-buitems-to-florida-state-university-on-fulbright-0beec4d6cc99",
        "source": "Medium Blog",
        "description": "Fulbright journey of a Pakistani woman from BUITEMS (Quetta) to Florida State University. Application strategy and motivation.",
    },
    {
        "name": "Ahmed Ali Khan",
        "country": "Pakistan",
        "scholarship": "Fulbright",
        "university": "US University",
        "program": "MS",
        "field": "Technology Policy",
        "type": "sop",
        "url": "https://aakhan91.medium.com/read-this-before-you-submit-your-fulbright-application-562d54aed9ed",
        "source": "Medium Blog",
        "description": "Fulbright application guide by a Pakistani Fulbrighter. Covers Personal Statement and Research Objective with detailed content advice.",
    },
    {
        "name": "Riaz Laghari",
        "country": "Pakistan",
        "scholarship": "Multiple (Fulbright, Chevening, Rhodes advisory)",
        "university": "Various",
        "program": "MS/PhD",
        "field": "English, Education",
        "type": "document",
        "url": "https://medium.com/@riazleghari/win-scholarships-and-excel-in-life-925334a7db97",
        "source": "Medium Blog",
        "description": "Comprehensive scholarship guide for Pakistani students. Covers Fulbright, Chevening, Rhodes with writing and application tips.",
    },
    {
        "name": "Aarish Bangash",
        "country": "Pakistan",
        "scholarship": "German Education (Tuition-free)",
        "university": "German University",
        "program": "MS",
        "field": "Engineering",
        "type": "document",
        "url": "https://medium.com/@aarishbangash/study-in-germany-for-free-55a957cebd40",
        "source": "Medium Blog",
        "description": "Guide for Pakistani students on studying in Germany for free. Documents required, application process, and LOM tips.",
    },
    # === INDIA (More winners) ===
    {
        "name": "Ayush Deep",
        "country": "India",
        "scholarship": "ETH Zurich Excellence Scholarship (ESOP)",
        "university": "ETH Zurich",
        "program": "MS",
        "field": "Molecular and Structural Biology",
        "type": "motivation_letter",
        "url": "https://ayushdeep.com/2023/esop-materials/",
        "source": "Personal Blog",
        "description": "Real ETH Zurich ESOP motivation letter and research proposal from an Indian winner. ESOP covers top 2% of entering Master's students. Includes downloadable PDFs of his actual application materials.",
    },
    {
        "name": "Ayush Deep",
        "country": "India",
        "scholarship": "ETH Zurich ESOP",
        "university": "ETH Zurich",
        "program": "MS",
        "field": "Molecular and Structural Biology",
        "type": "research_proposal",
        "url": "https://ayushdeep.com/files/deep_ayush_master_cv.pdf",
        "source": "Personal Blog",
        "description": "Real CV of an Indian ESOP winner at ETH Zurich. Now a PhD student at Memorial Sloan Kettering Cancer Center.",
    },
    # === PAKISTAN (EssayForum real letters) ===
    {
        "name": "Hamid Ali",
        "country": "Pakistan",
        "scholarship": "Stipendium Hungaricum",
        "university": "Hungarian University",
        "program": "BS",
        "field": "Computer Science",
        "type": "motivation_letter",
        "url": "https://essayforum.com/letters/application-stipendium-hungaricum-scholarship-95535/",
        "source": "EssayForum",
        "description": "Real Stipendium Hungaricum motivation letter from a Pakistani student applying for BSCS. Received community feedback and review on the essay.",
    },
    {
        "name": "Pakistani Erasmus Applicant",
        "country": "Pakistan",
        "scholarship": "Erasmus Mundus (ME3+)",
        "university": "European Consortium",
        "program": "MS",
        "field": "Chemical Engineering",
        "type": "motivation_letter",
        "url": "https://essayforum.com/letters/motivation-erasmus-mundus-consortium-dealing-94072/",
        "source": "EssayForum",
        "description": "Real Erasmus Mundus motivation letter from a Pakistani chemical engineering student. Details his journey from a middle-class family to securing admission in top universities.",
    },
    {
        "name": "Pakistani Fulbright Applicant",
        "country": "Pakistan",
        "scholarship": "Fulbright",
        "university": "US University",
        "program": "MS/PhD",
        "field": "Image Processing, Computer Vision",
        "type": "research_proposal",
        "url": "https://essayforum.com/letters/motivation-image-processing-computer-vision-97927/",
        "source": "EssayForum",
        "description": "Real Fulbright research proposal discussion from a Pakistani/Afghan applicant. Focuses on computer vision AI for resource-constrained environments.",
    },
    {
        "name": "Pakistani Chemical Engineer",
        "country": "Pakistan",
        "scholarship": "Erasmus Mundus",
        "university": "European University",
        "program": "MS",
        "field": "Chemical Engineering",
        "type": "motivation_letter",
        "url": "https://essayforum.com/letters/motivation-erasmus-mundus-consortium-dealing-94072/",
        "source": "EssayForum",
        "description": "Detailed Erasmus Mundus motivation letter from a Pakistani student. Shows personal journey from financial hardship to academic excellence.",
    },
    # === BANGLADESH (EssayForum real letters) ===
    {
        "name": "Md. Shajalal Mohon",
        "country": "Bangladesh",
        "scholarship": "Professional Short Course Scholarship",
        "university": "University of Dhaka / International Training",
        "program": "Professional Course",
        "field": "Disaster Management, Project Planning",
        "type": "motivation_letter",
        "url": "https://essayforum.com/scholarship/motivation-professional-course-participatory-52002/",
        "source": "EssayForum",
        "description": "Real motivation letter from a Bangladeshi professional (Masters from Dhaka University) applying for a short course scholarship in Participatory Planning and Monitoring.",
    },
    # === NEPAL (EssayForum real letters) ===
    {
        "name": "Nepali Scholarship Applicant",
        "country": "Nepal",
        "scholarship": "Multiple Scholarships",
        "university": "Various",
        "program": "MS",
        "field": "Entrepreneurship",
        "type": "motivation_letter",
        "url": "https://essayforum.com/letters/nepal-education-motivation-scholarship-97419/",
        "source": "EssayForum",
        "description": "Real motivation letter from a Nepali student. Studied in India, family in construction, applying for entrepreneurship-related scholarship.",
    },
    # === LINKEDIN WINNERS ===
    {
        "name": "Hadiqa Maqsood",
        "country": "Pakistan",
        "scholarship": "Fulbright + Commonwealth",
        "university": "US University (Fulbright) / UK University (Commonwealth)",
        "program": "MS",
        "field": "Water Resources Engineering",
        "type": "sop",
        "url": "https://www.linkedin.com/pulse/fulbright-scholarship-guide-5-days-go-hadiqa-maqsood",
        "source": "LinkedIn Article",
        "description": "Fulbright Scholarship application guide by a Pakistani dual-scholar (Fulbright + Commonwealth). Covers personal statement and study objective strategies.",
    },
    {
        "name": "Muzzammil Patel",
        "country": "India/Pakistan",
        "scholarship": "Chevening",
        "university": "UK University",
        "program": "MS",
        "field": "Development Sector",
        "type": "sop",
        "url": "https://www.linkedin.com/posts/muzzammil-patel-00139873_chevening-activity-7227363065095233538-tE_X",
        "source": "LinkedIn Post",
        "description": "Chevening application essay guide by a Chevening Scholar. Covers networking essay structure with real examples.",
    },
    {
        "name": "Pallavi Mahajan",
        "country": "India",
        "scholarship": "Chevening",
        "university": "University of Oxford (Said Business School)",
        "program": "MBA",
        "field": "Business, Social Impact",
        "type": "sop",
        "url": "https://www.linkedin.com/posts/pallavi-mahajan_instagram-pakistan-cheveningscholarship-activity-7183365779331977217-F8MJ",
        "source": "LinkedIn Post",
        "description": "Chevening essay mentorship story by an Indian Chevening Scholar at Oxford. Details essay preparation and mentor relationship.",
    },
    {
        "name": "Anam Zahra",
        "country": "Pakistan",
        "scholarship": "Fulbright",
        "university": "Oregon State University",
        "program": "PhD",
        "field": "Climate Policy, Environmental Governance",
        "type": "research_proposal",
        "url": "https://www.linkedin.com/in/anamzahraa",
        "source": "LinkedIn Profile",
        "description": "Fulbright PhD scholar from Pakistan researching climate governance. Her research proposal focuses on stakeholder narratives in climate policy.",
    },
    {
        "name": "Ramsha Ahmed",
        "country": "Pakistan",
        "scholarship": "Fulbright",
        "university": "Colorado State University",
        "program": "MBA",
        "field": "Corporate Sustainability",
        "type": "sop",
        "url": "https://www.linkedin.com/in/ramsha-ahmed-41a29a113",
        "source": "LinkedIn Profile",
        "description": "Fulbright Scholar from Pakistan with Impact MBA in Corporate Sustainability. Guides other Fulbright applicants.",
    },
]

REDDIT_SCHOLARSHIP_SUBREDDITS = [
    "DAAD", "fulbright", "chevening", "Erasmus",
    "gradadmissions", "StatementOfPurpose", "scholarships",
    "studyAbroad", "Indians_StudyAbroad", "masters_germany",
    "studying_in_germany", "PakistaniTech",
]

SCHOLARSHIP_DOC_PATTERNS = [
    r'statement\s*of\s*purpose', r'\bsop\b', r'personal\s*statement',
    r'motivation\s*letter', r'motivational\s*letter', r'cover\s*letter',
    r'study\s*plan', r'academic\s*plan', r'research\s*proposal',
    r'research\s*plan', r'recommendation\s*letter', r'letter\s*of\s*recommendation',
    r'\blor\b', r'reference\s*letter', r'curriculum\s*vitae', r'\bcv\b',
    r'resume', r'certificate', r'volunteer', r'achievement',
    r'scholarship', r'essay', r'application',
]

FIELD_KEYWORDS = [
    "machine learning", "deep learning", "artificial intelligence",
    "data science", "statistics", "computer science", "computer vision",
    "nlp", "data engineering", "ml", "ai", "software engineering",
    "electrical engineering", "computer engineering", "robotics",
    "renewable energy", "power engineering", "bioengineering",
    "signal processing", "embedded systems", "civil engineering",
    "mechanical engineering", "chemical engineering", "material science",
    "mathematics", "physics", "biology", "chemistry", "biochemistry",
    "economics", "finance", "business", "psychology", "neuroscience",
    "environmental science", "geology", "astronomy", "astrophysics",
    "medical imaging", "biomedical", "public health", "development studies",
    "education", "law", "international relations",
]

FILE_EXTENSIONS = (".pdf", ".md", ".txt", ".docx", ".doc", ".rtf", ".odt")

SKIP_FILENAMES = {".gitkeep", "readme.md", "license", "license.txt",
                  "readme", "readme.txt", "readme.rst", "index.md",
                  "contributing.md", "changelog.md", "package.json",
                  "package-lock.json", "yarn.lock", "requirements.txt",
                  "setup.py", "Makefile", "Dockerfile", ".dockerignore",
                  ".gitignore", ".gitattributes", ".editorconfig",
                  ".prettierrc", ".eslintrc", "tsconfig.json",
                  "webpack.config.js", "rollup.config.js"}

SKIP_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
                   ".h", ".hpp", ".cs", ".go", ".rb", ".php", ".swift",
                   ".kt", ".rs", ".scala", ".html", ".css", ".scss",
                   ".less", ".json", ".xml", ".yaml", ".yml", ".toml",
                   ".ini", ".cfg", ".conf", ".sh", ".bat", ".ps1",
                   ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
                   ".woff", ".woff2", ".ttf", ".eot",
                   ".zip", ".tar", ".gz", ".rar", ".7z",
                   ".exe", ".dll", ".so", ".dylib",
                   ".ipynb", ".csv", ".xlsx", ".xls",
                   ".ppt", ".pptx"}


class DocumentCollector:
    def __init__(self, interactive=False):
        self.interactive = interactive
        self.existing = self._load_existing()
        self.existing_urls = {(d.get("url", "") or "").lower().strip() for d in self.existing}
        self.existing_ids = {d.get("id", "") for d in self.existing}
        self.new_samples = []
        self._check_github_token()

    def _check_github_token(self):
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            print("  [WARNING] GITHUB_TOKEN not set. GitHub API rate limit = 60 req/hr.")

    def _load_existing(self):
        if os.path.exists(DOCUMENTS_FILE):
            try:
                with open(DOCUMENTS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("samples", [])
            except Exception:
                return []
        return []

    def _save(self):
        all_samples = self.existing + self.new_samples
        with open(DOCUMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"samples": all_samples}, f, indent=2, ensure_ascii=False)

    def _detect_field(self, text):
        text_lower = text.lower()
        matched = []
        for kw in FIELD_KEYWORDS:
            if kw in text_lower:
                matched.append(kw.title())
        return ", ".join(matched[:3]) if matched else "General"

    def _is_scholarship_document(self, filename):
        name_lower = filename.lower()
        if name_lower in SKIP_FILENAMES:
            return False
        ext = os.path.splitext(name_lower)[1]
        if ext in SKIP_EXTENSIONS:
            return False
        if ext not in FILE_EXTENSIONS and ext not in (".pdf", ".md", ".txt", ".docx", ".doc"):
            return False
        stem = os.path.splitext(name_lower)[0]
        for pat in SCHOLARSHIP_DOC_PATTERNS:
            if re.search(pat, stem):
                return True
        return False

    def _detect_type_from_filename(self, filename):
        name_lower = filename.lower()
        if re.search(r'statement\s*of\s*purpose|\bsop\b|personal\s*statement', name_lower):
            return "sop"
        if re.search(r'motivation\s*letter|cover\s*letter|motivational\s*letter|scholarship\s*essay', name_lower):
            return "motivation_letter"
        if re.search(r'study\s*plan|academic\s*plan|studyplan', name_lower):
            return "study_plan"
        if re.search(r'research\s*proposal|research\s*plan|proposal', name_lower):
            return "research_proposal"
        if re.search(r'recommendation\s*letter|letter\s*of\s*recommendation|\blor\b|reference\s*letter', name_lower):
            return "recommendation"
        if re.search(r'curriculum\s*vitae|\bcv\b|resume', name_lower):
            return "resume"
        if re.search(r'certificate|volunteer|achievement|award|participation', name_lower):
            return "certificate"
        return "document"

    def _fetch_json(self, url, headers=None):
        default_headers = {"User-Agent": "ScholarAI/1.0", "Accept": "application/json"}
        if headers:
            default_headers.update(headers)
        try:
            req = Request(url, headers=default_headers)
            with urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return None

    def _fetch_text(self, url):
        try:
            req = Request(url, headers={"User-Agent": "ScholarAI/1.0"})
            with urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None

    def _github_headers(self):
        headers = {
            "User-Agent": "ScholarAI/1.0",
            "Accept": "application/vnd.github+json",
        }
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _gen_id(self, prefix, url):
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"{prefix}-{url_hash}"

    def _add_sample(self, sample):
        sid = sample.get("id", "")
        url = sample.get("url", "").lower().strip()
        if sid in self.existing_ids:
            return False
        if url and url in self.existing_urls:
            return False
        self.new_samples.append(sample)
        self.existing_ids.add(sid)
        if url:
            self.existing_urls.add(url)
        return True

    def scrape_verified_repos(self, progress_callback=None):
        total_added = 0
        for repo_slug, folders_map in VERIFIED_REPOS.items():
            if progress_callback:
                progress_callback(f"Scanning verified repo: {repo_slug}")
            for folder, doc_type in folders_map.items():
                try:
                    added = self._scan_repo_folder(repo_slug, folder, doc_type)
                    total_added += added
                except Exception:
                    pass
                time.sleep(0.1)
        return total_added

    def _scan_repo_folder(self, repo_slug, folder, default_type):
        api_url = f"https://api.github.com/repos/{repo_slug}/contents/{folder}" if folder else \
                  f"https://api.github.com/repos/{repo_slug}/contents"
        items = self._fetch_json(api_url, headers=self._github_headers())
        if not items or not isinstance(items, list):
            return 0
        added = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "file":
                continue
            name = item.get("name", "")
            if not self._is_scholarship_document(name):
                continue
            doc_url = item.get("download_url", "")
            if not doc_url:
                continue
            detected_type = self._detect_type_from_filename(name)
            if detected_type == "document":
                detected_type = default_type
            field = self._detect_field(name)
            title = name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
            sample = {
                "id": self._gen_id(f"{detected_type}-gh", doc_url),
                "type": detected_type,
                "title": title[:200],
                "scholar_name": f"GitHub – {repo_slug.split('/')[0]}",
                "scholarship_name": "Multiple Scholarships",
                "university": "Various",
                "program": "Graduate Program",
                "country": "South Asia",
                "field": field,
                "url": doc_url,
                "source": f"GitHub: {repo_slug}",
                "description": f"Real {detected_type.replace('_', ' ').title()} from a South Asian scholarship applicant. Source: {repo_slug}",
                "key_takeaways": [
                    "Learn from real successful application structures",
                    "Study formatting and content organization",
                    "Adapt the narrative style to your own background"
                ],
                "collected_at": datetime.now().isoformat(),
            }
            if self._add_sample(sample):
                added += 1
        return added

    def add_known_winners(self, progress_callback=None):
        added = 0
        for winner in KNOWN_WINNERS:
            if progress_callback:
                progress_callback(f"Adding known winner: {winner['name']} ({winner['country']})")
            sid = self._gen_id(f"{winner['type']}-kw", winner['url'])
            sample = {
                "id": sid,
                "type": winner['type'],
                "title": f"{winner['name']} — {winner['scholarship']} — {winner['type'].replace('_', ' ').title()}",
                "scholar_name": winner['name'],
                "scholarship_name": winner['scholarship'],
                "university": winner['university'],
                "program": winner['program'],
                "country": winner['country'],
                "field": winner['field'],
                "url": winner['url'],
                "source": winner['source'],
                "description": winner['description'],
                "key_takeaways": [
                    f"Real {winner['type'].replace('_', ' ')} from a {winner['country']} {winner['scholarship']} winner",
                    "Study how successful applicants structure their documents",
                    "Note country-specific and scholarship-specific requirements"
                ],
                "collected_at": datetime.now().isoformat(),
            }
            if self._add_sample(sample):
                added += 1
        return added

    SKIP_GENERIC_SITES = [
        "scholarshipunion.com", "scholarshipsguider.com", "thescholarsphere.com",
        "scholarsavenue.com", "brightlinkprep.com", "o4af.com",
        "scholarshipbob.com", "opportunitydesk.org", "desideutsche.com",
        "scholarship24.com", "scholarshipmonkey.com", "studying-in-germany.org",
        "mastersportal.com", "daad.de", "topuniversities.com",
        "gradschoolhub.com", "study.eu", "scholars4dev.com",
        "opportunitiesforyouth.org", "youthop.com", "afterschoolafrica.com",
        "scholarah.com", "globalscholarsguide.com", "truescho.com",
        "freconsultant.com", "ilmiworld.com",
    ]

    def _is_actual_document(self, url, title, snippet):
        url_lower = url.lower()
        for site in self.SKIP_GENERIC_SITES:
            if site in url_lower:
                return False
        ext = os.path.splitext(url.split("?")[0])[1]
        if ext in (".pdf", ".doc", ".docx"):
            return True
        if "docs.google.com" in url_lower:
            return True
        if "drive.google.com" in url_lower:
            return True
        if "dropbox.com" in url_lower:
            return True
        if "medium.com" in url_lower:
            return True
        if "blogspot.com" in url_lower:
            return True
        if "wordpress.com" in url_lower:
            return True
        if "reddit.com" in url_lower:
            return True
        if "linkedin.com" in url_lower:
            return True
        combined = (title + " " + (snippet or "")).lower()
        doc_indicators = [
            "my motivation letter", "my sop", "my statement of purpose",
            "study plan sample", "research proposal sample",
            "winning essay", "successful application",
            "personal statement", "scholarship essay",
            "recommendation letter", "letter of recommendation",
            "how i won", "how i got", "my journey",
            "sample sop", "sample motivation", "sample study plan",
            "real sop", "actual sop",
        ]
        for ind in doc_indicators:
            if ind in combined:
                return True
        return ext in (".pdf", ".doc", ".docx", ".txt") or "docs.google.com" in url_lower

    def search_web_for_south_asian_winners(self, progress_callback=None):
        if progress_callback:
            progress_callback("Searching web for South Asian scholarship winners...")
        added = 0

        searches = [
            # ===== REDDIT =====
            'site:reddit.com/r/DAAD "motivation letter" "scholarship"',
            'site:reddit.com/r/DAAD "study plan" Germany',
            'site:reddit.com/r/fulbright "personal statement" Pakistan OR India OR Bangladesh',
            'site:reddit.com/r/fulbright "study objective" sample',
            'site:reddit.com/r/chevening "essay" leadership OR networking',
            'site:reddit.com/r/Erasmus "motivation letter" Bangladesh OR India OR Pakistan',
            'site:reddit.com/r/Indians_StudyAbroad "SOP" OR "statement of purpose"',
            'site:reddit.com/r/gradadmissions "SOP" scholarship Bangladesh OR India',
            'site:reddit.com/r/PakistaniTech "scholarship" "SOP" OR "motivation letter"',
            'site:reddit.com/r/StatementOfPurpose "scholarship" sample',
            'site:reddit.com/r/studyAbroad "scholarship" "essay" Bangladesh OR India',
            'site:reddit.com/r/masters_germany "DAAD" "motivation letter"',
            'site:reddit.com/r/studying_in_germany "SOP" OR "motivation letter" India',
            # ===== LINKEDIN =====
            'site:linkedin.com "Fulbright" "Pakistan" "scholar" personal statement',
            'site:linkedin.com "Chevening" "India" "scholar" essay',
            'site:linkedin.com "DAAD" "Bangladesh" "scholar" motivation letter',
            'site:linkedin.com "Commonwealth" "Pakistan" "scholar" application',
            'site:linkedin.com/pulse "Fulbright" "scholarship" essay tips',
            'site:linkedin.com/pulse "Chevening" "application" guide',
            'site:linkedin.com/pulse "DAAD" "scholarship" experience',
            # ===== FACEBOOK (public groups/pages) =====
            'site:facebook.com "DAAD" "Bangladesh" "scholarship"',
            'site:facebook.com "Fulbright" "Pakistan" "program"',
            'site:facebook.com "Erasmus Mundus" "Bangladesh" "scholarship"',
            'site:facebook.com "Chevening" "India" "scholarship"',
            # ===== MEDIUM =====
            'site:medium.com "Erasmus Mundus" "Bangladesh" "SOP" "winning"',
            'site:medium.com "Fulbright" "Pakistan" "essay" personal statement',
            'site:medium.com "DAAD" "India" "motivation letter" scholarship',
            'site:medium.com "Chevening" "Bangladesh" "essay" application',
            'site:medium.com "Commonwealth" "Pakistan" "scholarship"',
            'site:medium.com "GKS" "Bangladesh" "study plan"',
            'site:medium.com "how I won" "scholarship" "Bangladesh"',
            'site:medium.com "how I got" "Fulbright" "India"',
            'site:medium.com "my journey" "DAAD" "Pakistan"',
            # ===== BLOGSPOT / PERSONAL BLOGS =====
            'site:blogspot.com "scholarship" "Bangladesh" "SOP" "DAAD"',
            'site:blogspot.com "Fulbright" "India" "personal statement"',
            'site:blogspot.com "study in Germany" "Pakistan" "SOP"',
            'site:wordpress.com "scholarship" "Bangladesh" "essay"',
            'site:wixsite.com "scholarship" "India" "SOP"',
            # ===== GOOGLE DRIVE / DOCS =====
            'site:docs.google.com "scholarship" "Bangladesh" "SOP"',
            'site:docs.google.com "Fulbright" "Pakistan" "essay"',
            'site:drive.google.com "DAAD" "study plan" scholarship',
            # ===== Bangladeshi winners =====
            '"Erasmus Mundus" "Bangladesh" "motivation letter" "successful"',
            '"DAAD" "Bangladesh" "study plan" scholarship pdf',
            '"Fulbright" "Bangladesh" "personal statement" winning',
            '"Chevening" "Bangladesh" "essay" accepted sample',
            '"Commonwealth" "Bangladesh" "scholarship" "statement of purpose"',
            '"GKS" "Bangladesh" "study plan" accepted',
            '"MEXT" "Bangladesh" "research plan" scholarship',
            '"BUET" "SOP" "graduate" "admission"',
            '"Dhaka University" "scholarship" "SOP"',
            # ===== Indian winners =====
            '"Fulbright" "India" "personal statement" winning sample',
            '"DAAD" "India" "motivation letter" accepted scholarship',
            '"Chevening" "India" "leadership essay" selected',
            '"Commonwealth" "India" "scholarship" SOP accepted',
            '"IIT" "statement of purpose" "graduate" admitted',
            '"Indian" "SOP" "Germany" "masters" admitted',
            '"Indian" "DAAD" "study plan" pdf',
            # ===== Pakistani winners =====
            '"Fulbright" "Pakistan" "personal statement" winning essay',
            '"Chevening" "Pakistan" "essay" selected sample',
            '"DAAD" "Pakistan" "motivation letter" accepted',
            '"Commonwealth" "Pakistan" "scholarship" SOP sample',
            '"HEC" "Pakistan" "SOP" overseas scholarship',
            '"NUST" "SOP" "graduate" abroad',
            '"LUMS" "scholarship" "SOP"',
            '"Pakistani" "Fulbright" "essay" sample',
            # ===== Nepali winners =====
            '"scholarship" "Nepal" "statement of purpose" sample',
            '"DAAD" "Nepal" "motivation letter"',
            '"Fulbright" "Nepal" "personal statement"',
            # ===== South Asian general =====
            '"South Asian" "DAAD" "SOP" sample winning',
            '"developing country" "Fulbright" "essay" accepted',
            '"successful" "scholarship" "application" "motivation letter" South Asia',
            '"real" "SOP" "scholarship" "Bangladesh" "accepted"',
        ]

        try:
            agent = BaseAgent("doc-collector", interactive=False)
            for query in searches:
                results = agent.search_web(query, num_results=5)
                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    if not url or url.lower().strip() in self.existing_urls:
                        continue
                    if not self._is_actual_document(url, title, snippet):
                        continue
                    detected_type = self._detect_type_from_filename(title)
                    if detected_type == "document":
                        combined = (title + " " + (snippet or "")).lower()
                        if re.search(r'motivation|scholarship essay|cover letter', combined):
                            detected_type = "motivation_letter"
                        elif re.search(r'study plan|academic plan', combined):
                            detected_type = "study_plan"
                        elif re.search(r'research proposal|research plan', combined):
                            detected_type = "research_proposal"
                        elif re.search(r'lor|recommendation|reference letter', combined):
                            detected_type = "recommendation"
                        elif re.search(r'certificate|volunteer|achievement|award', combined):
                            detected_type = "certificate"
                        elif re.search(r'cv|resume|curriculum vitae', combined):
                            detected_type = "resume"
                        elif re.search(r'sop|statement of purpose|personal statement', combined):
                            detected_type = "sop"
                    field = self._detect_field(title + " " + (snippet or ""))
                    sample = {
                        "id": self._gen_id("saw", url),
                        "type": detected_type,
                        "title": title[:200],
                        "scholar_name": "South Asian Winner (Web Discovery)",
                        "scholarship_name": "",
                        "university": "",
                        "program": "Graduate Program",
                        "country": "South Asia",
                        "field": field,
                        "url": url,
                        "source": "Web Search",
                        "description": (snippet or f"Real scholarship application document from a South Asian student: {title[:100]}")[:300],
                        "key_takeaways": [
                            "Study real application examples from South Asian scholarship winners",
                            "Note common patterns in strong applications from the region"
                        ],
                        "collected_at": datetime.now().isoformat(),
                    }
                    if self._add_sample(sample):
                        added += 1
                time.sleep(1)
        except Exception as e:
            if progress_callback:
                progress_callback(f"Web search error: {e}")
        return added

    def run(self, progress_callback=None, force=False, quick=True):
        if force:
            self.new_samples = []
            self.existing = []
            self.existing_urls = set()
            self.existing_ids = set()

        count = 0

        count += self.scrape_verified_repos(progress_callback)

        count += self.add_known_winners(progress_callback)

        if not quick:
            count += self.search_web_for_south_asian_winners(progress_callback)

        if count > 0:
            self._save()

        if progress_callback:
            progress_callback(f"Document collection complete: {count} new documents added")

        return count


if __name__ == "__main__":
    collector = DocumentCollector(interactive=False)
    count = collector.run(force=True, quick=False, progress_callback=lambda msg: print(msg))
    print(f"Collected {count} new documents")
