"""My Doc Generator: hybrid template + AI-powered document generation for scholarships."""
import sys, os, json, re
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from groq import Groq
except ImportError:
    Groq = None

from config import PROFILE
from data.data_loader import load_core_scholarships

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
MY_DOCS_FILE = os.path.join(DATA_DIR, "my_docs.json")
FOLLOWED_FILE = os.path.join(DATA_DIR, "followed.json")

PORTFOLIO = {
    "name": "Sium Ahameed Bhuyan",
    "email": "siumahameed2003@gmail.com",
    "phone": "+880-1700-000000",
    "education": "BSc in Statistics (Graduated), Dhaka College",
    "gpa": "3.20/4.00",
    "country": "Bangladesh",
    "location": "Dhaka, Bangladesh",
    "languages": "English (Fluent), Bengali (Native)",
    "linkedin": "https://www.linkedin.com/in/sium11",
    "github": "https://github.com/siumahameed",
    "kaggle": "https://www.kaggle.com/siumahameedbhuiyain",
    "skills": {
        "Machine Learning": ["Scikit-learn", "NLTK", "Classification", "Regression", "NLP"],
        "Deep Learning": ["Neural Networks", "TensorFlow basics"],
        "Data Analysis": ["Pandas", "NumPy", "SciPy", "SQL", "SPSS"],
        "Visualization": ["Matplotlib", "Seaborn", "Plotly"],
        "Development": ["Python", "FastAPI", "Git", "Jupyter", "VS Code", "Cursor"],
        "Statistics": ["Probability Theory", "Inference", "Experimental Design", "Regression Analysis", "Statistical Modeling"],
    },
    "proficiency": {"Python": "78%", "ML": "85%", "DL": "60%", "Data Analysis": "88%", "Statistics": "95%", "SQL": "90%"},
    "projects": [
        {"title": "Rock and Mine Prediction for Sonar", "type": "ML", "tech": "Logistic Regression, Scikit-learn", "desc": "Predict mines vs rocks from sonar radar data"},
        {"title": "Spam SMS Detection", "type": "ML", "tech": "NLP, Text Classification, Scikit-learn", "desc": "Detect spam messages using text classification"},
        {"title": "Ad Click Prediction", "type": "ML", "tech": "Classification, Scikit-learn", "desc": "Predict user ad clicks for better targeting"},
        {"title": "Energy Consumption Prediction", "type": "ML", "tech": "Regression, Data Analysis", "desc": "Forecast energy consumption using regression models"},
        {"title": "Loan Prediction", "type": "ML", "tech": "Classification, Finance", "desc": "Predict loan approval status from applicant data"},
        {"title": "Heart Disease Prediction", "type": "ML", "tech": "Classification, Healthcare", "desc": "Predict heart disease risk from medical data"},
        {"title": "BD Cricket Analysis", "type": "EDA", "tech": "Pandas, Matplotlib", "desc": "Bangladesh cricket statistics analysis"},
        {"title": "BD Road Accident Analysis", "type": "EDA", "tech": "Pandas, Matplotlib", "desc": "Road accident pattern analysis in Bangladesh"},
        {"title": "BD Temperature & Rain Analysis", "type": "EDA", "tech": "Pandas, Matplotlib", "desc": "Temperature and rainfall patterns in Bangladesh"},
        {"title": "Diwali Sales Analysis", "type": "EDA", "tech": "Pandas, Matplotlib", "desc": "Customer purchasing patterns during Diwali"},
        {"title": "IPL Data Analysis", "type": "EDA", "tech": "Pandas, Visualization", "desc": "IPL cricket data team and player insights"},
        {"title": "Shop Data Analysis", "type": "EDA", "tech": "Pandas, Tableau", "desc": "US retail shop sales and customer behavior"},
        {"title": "Lego Data Analysis", "type": "EDA", "tech": "Pandas, Visualization", "desc": "Lego product sets and themes analysis"},
        {"title": "AgriTech", "type": "App", "tech": "Node.js, AI, Tailwind CSS", "desc": "AI agri-advisory for Bangladeshi farmers — Bengali chatbot, crop recs, disease detection"},
        {"title": "VocabPro", "type": "App", "tech": "FastAPI, PostgreSQL, WhatsApp API", "desc": "SaaS: 10 daily English vocab with Bengali meanings via WhatsApp/email"},
        {"title": "StatWise", "type": "App", "tech": "FastAPI, scikit-learn, pandas, PostgreSQL", "desc": "Automated statistical reporting for SMEs — upload data, get analysis + PDF reports"},
    ],
    "achievements": [
        "Math Olympiad participant",
        "Volunteer for Bangladesh",
        "Social Business project involvement",
        "36+ data science and ML projects completed",
        "1000+ hours of practice in ML/Data Science",
    ],
    "target_fields": ["Machine Learning", "Data Science", "Artificial Intelligence", "Deep Learning", "Statistics", "Data Analytics"],
    "graduation_year": 2025,
}

DOCUMENT_TEMPLATES = {
    "sop": {
        "label": "Statement of Purpose",
        "sections": ["Opening & Personal Introduction", "Academic Background & Foundations", "Technical Journey & Projects", "Why This Scholarship & Program", "Future Vision & Impact"],
        "description": "A compelling narrative connecting your background to the scholarship's mission",
    },
    "cv": {
        "label": "Curriculum Vitae",
        "sections": ["Education", "Technical Skills", "Projects", "Achievements & Leadership", "Languages & Certifications"],
        "description": "Academic CV highlighting stats background and ML projects",
    },
    "study_plan": {
        "label": "Study Plan",
        "sections": ["Educational Background & Motivation", "Academic Interests & Goals", "Why This Country & University", "Coursework & Research Plan", "Career Aspirations & Contribution to Home Country"],
        "description": "A detailed academic plan required by DAAD, GKS, MEXT, CSC, and other government scholarships",
    },
    "research_proposal": {
        "label": "Research Proposal",
        "sections": ["Problem Statement & Context", "Literature Review & Gap", "Research Questions & Objectives", "Methodology & Data", "Timeline & Expected Outcomes"],
        "description": "A focused proposal linking Bangladesh development challenges to your field",
    },
    "lor_request": {
        "label": "Recommendation Letter Request",
        "sections": ["Introduction & Context", "Your Qualifications", "Why This Recommender", "Scholarship Details & Deadline", "Documents Attached & Next Steps"],
        "description": "Professional email draft requesting a recommendation letter",
    },
    "diversity_statement": {
        "label": "Diversity Statement",
        "sections": ["Personal Background & Perspective", "Overcoming Challenges", "Contributing to Diversity", "Future Impact & Inclusion"],
        "description": "A personal statement highlighting your unique background as a Bangladeshi student and how your perspective enriches the academic community",
    },
    "motivation_letter": {
        "label": "Motivation Letter",
        "sections": ["Personal Motivation & Calling", "Why This Program & University", "Experiences That Define You", "Future Vision & Contribution", "Closing & Commitment"],
        "description": "A compelling personal argument for why you deserve the scholarship, required by DAAD EPOS, Erasmus Mundus, Stipendium Hungaricum",
    },
    "scholarship_essay": {
        "label": "Scholarship-Specific Essay",
        "sections": ["Personal Motivation & Goals", "Why You Deserve This Award", "Academic & Leadership Journey", "How This Scholarship Fits Your Path", "Vision for the Future"],
        "description": "A tailored essay addressing the specific prompts of a given scholarship",
    },
    "personal_history": {
        "label": "Personal History Statement",
        "sections": ["Early Life & Upbringing", "Educational Journey & Hardships", "Key Influences & Turning Points", "Resilience & Growth", "Aspirations & Community Impact"],
        "description": "A reflective narrative about your life story, challenges overcome, and how they shaped your goals",
    },
}

SYSTEM_PROMPT = """You are a scholarship application document expert. Your task is to generate professional, compelling, and personalized scholarship application documents.

USER PROFILE:
Name: {name}
Email: {email}
Phone: {phone}
Education: {education}
GPA: {gpa} (on 4.0 scale)
Country: {country}
Location: {location}
Languages: {languages}
LinkedIn: {linkedin}
GitHub: {github}
Skills: {skills_summary}
Projects: {projects_summary}
Achievements: {achievements}
Target Fields: {target_fields}

CRITICAL RULES — YOU MUST FOLLOW THESE EXACTLY:
1. Write in FIRST PERSON for SOP, CV, Research Proposal
2. Be specific — reference actual projects, skills, and achievements from the profile above
3. Keep tone professional but authentic — show genuine motivation
4. Connect every document to BANGLADESH DEVELOPMENT for development-focused scholarships
5. For CV: use Europass-style structure, max 2 pages equivalent
6. For Research Proposal: focus on a concrete problem in Bangladesh, propose ML/Stats solution
7. For LOR Request: write as if the student is asking a Statistics professor who knows them well
8. For Study Plan: describe specific courses you want to take at target universities, research areas to explore, and how each connects to Bangladesh development. Be concrete about 2-3 courses/research topics.
9. NEVER use placeholder text like [insert], [Your Name], [your], [email], [phone], [Professor's Name], [University], [details], [etc]. Use actual data from the profile. If a detail is missing from the profile, omit it entirely rather than using a placeholder.
9. Each document should be 500-1500 words unless specified otherwise
10. Tailor the content specifically to the scholarship's mission and criteria
11. The user has ALREADY COMPLETED their BSc (graduated in 2025). They are a GRADUATE seeking MSc admission. Do NOT refer to them as "currently pursuing", "current student", "3rd year", "third-year", "undergraduate", or "currently studying". Use past tense for the BSc degree.
12. Use the actual phone number and email from the profile. Do NOT invent or use placeholder phone numbers.
13. For the CV: include the actual email (siumahameed2003@gmail.com) and phone (+880-1700-000000) at the top.
14. Do NOT mention expected graduation dates — the degree is already completed.
15. Do NOT invent any information not present in the profile."""


def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if not api_key:
        try:
            import dotenv
            dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
            api_key = os.environ.get("GROQ_API_KEY")
        except Exception:
            pass
    if not api_key:
        return None
    try:
        return Groq(api_key=api_key)
    except Exception:
        return None


def get_followed_scholarships():
    if not os.path.exists(FOLLOWED_FILE):
        return []
    with open(FOLLOWED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    names = data.get("scholarships", [])

    all_scholarships = load_core_scholarships()
    name_map = {}
    for s in all_scholarships:
        name_map[s["name"].lower().strip()] = s

    result = []
    for n in names:
        key = n.lower().strip()
        if key in name_map:
            result.append(name_map[key])
        else:
            result.append({"name": n, "country": "", "provider": "", "coverage_type": "", "coverage": "", "match": 0, "strategy": "", "fields": "", "nationality": "", "academics": "", "degree": ""})
    return result


def _build_scholarship_context(scholarship):
    return f"""SCHOLARSHIP DETAILS:
Name: {scholarship.get('name', 'N/A')}
Provider: {scholarship.get('provider', 'N/A')}
Country: {scholarship.get('country', 'N/A')}
Coverage: {scholarship.get('coverage_type', 'N/A')} - {scholarship.get('coverage', 'N/A')}
Degree Level: {scholarship.get('degree', 'N/A')}
Target Fields: {scholarship.get('fields', 'N/A')}
Eligibility: {scholarship.get('nationality', 'N/A')}
Academic Requirements: {scholarship.get('academics', 'N/A')}
Required Documents: {scholarship.get('documents', 'N/A')}
Application Fee: {scholarship.get('fee', 'N/A')}
Language: {scholarship.get('lang_app', 'N/A')}
English Test: {scholarship.get('english_test', 'N/A')}
GRE: {scholarship.get('gre', 'N/A')}
Deadline: {scholarship.get('deadline_start', 'N/A')} - {scholarship.get('deadline_end', 'N/A')}
Duration: {scholarship.get('duration', 'N/A')}
Interview: {scholarship.get('interview', 'N/A')}
Competition: {scholarship.get('competition', 'N/A')}
Strategy: {scholarship.get('strategy', 'N/A')}
Match Score: {scholarship.get('match', 'N/A')}"""


def _build_doc_prompt(doc_type, scholarship, regenerate_section=None):
    sch_context = _build_scholarship_context(scholarship)
    template = DOCUMENT_TEMPLATES[doc_type]

    skills_summary = "; ".join(f"{k}: {', '.join(v)}" for k, v in PORTFOLIO["skills"].items())
    projects_summary = "; ".join(f"{p['title']} ({p['type']}, {p['tech']})" for p in PORTFOLIO["projects"])
    achievements = "; ".join(PORTFOLIO["achievements"])

    system = SYSTEM_PROMPT.format(
        name=PORTFOLIO["name"],
        email=PORTFOLIO["email"],
        phone=PORTFOLIO["phone"],
        education=PORTFOLIO["education"],
        gpa=PORTFOLIO["gpa"],
        country=PORTFOLIO["country"],
        location=PORTFOLIO["location"],
        languages=PORTFOLIO["languages"],
        linkedin=PORTFOLIO["linkedin"],
        github=PORTFOLIO["github"],
        skills_summary=skills_summary,
        projects_summary=projects_summary,
        achievements=achievements,
        target_fields=", ".join(PORTFOLIO["target_fields"]),
    )

    section_instruction = ""
    if regenerate_section:
        section_instruction = f"\n\nREGENERATE ONLY THIS SECTION: {regenerate_section}. Replace just this section with improved content."

    user_prompt = f"""Generate a {template['label']} for the following scholarship.

{sch_context}

DOCUMENT TYPE: {template['label']}
REQUIRED SECTIONS: {', '.join(template['sections'])}
DESCRIPTION: {template['description']}

{section_instruction}

Write the complete {template['label']} document. Format with section headers using markdown (## Section Name)."""

    return system, user_prompt


PLACEHOLDER_PATTERNS = [
    r'\[insert[^\]]*\]',
    r'\[your[^\]]*\]',
    r'\[Your[^\]]*\]',
    r'\[email[^\]]*\]',
    r'\[phone[^\]]*\]',
    r'\[Professor[^\]]*\]',
    r'\[professor[^\]]*\]',
    r'\[University[^\]]*\]',
    r'\[university[^\]]*\]',
    r'\[specific[^\]]*\]',
    r'\[add[^\]]*\]',
    r'\[provide[^\]]*\]',
    r'\[please[^\]]*\]',
    r'\[name[^\]]*\]',
    r'\[Name[^\]]*\]',
    r'\[address[^\]]*\]',
    r'\[Contact[^\]]*\]',
    r'\[contact[^\]]*\]',
    r'\[detail[^\]]*\]',
    r'\[Detail[^\]]*\]',
    r'\[fill[^\]]*\]',
]


def _clean_placeholders(content):
    for pattern in PLACEHOLDER_PATTERNS:
        content = re.sub(pattern, '', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r' \(currently[^)]*\)', '', content, flags=re.IGNORECASE)
    return content.strip()


class MyDocGenerator:
    def __init__(self):
        self.client = get_groq_client()
        self.models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "qwen/qwen3-32b"]

    def is_available(self):
        return self.client is not None

    def generate_doc(self, scholarship, doc_type, regenerate_section=None):
        if not self.client:
            return {"error": "Groq API not configured. Add GROQ_API_KEY to .env"}

        system, user = _build_doc_prompt(doc_type, scholarship, regenerate_section)

        last_error = None
        for model in self.models:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=0.7,
                    max_tokens=4096,
                )
                content = response.choices[0].message.content
                content = _clean_placeholders(content)
                return {"content": content, "generated_at": datetime.now().isoformat(), "model": model}
            except Exception as e:
                last_error = str(e)
                if "rate_limit" not in str(e).lower():
                    break
        return {"error": last_error or "All models failed"}

    def generate_all(self, scholarship, skip_existing=True):
        existing = self.get_scholarship_docs(scholarship.get("name", ""))
        result = {}
        for doc_type in DOCUMENT_TEMPLATES:
            if skip_existing and doc_type in existing and "content" in existing[doc_type] and existing[doc_type]["content"]:
                result[doc_type] = existing[doc_type]
            else:
                result[doc_type] = self.generate_doc(scholarship, doc_type)
        return result

    def generate_for_followed(self, followed_list=None):
        if followed_list is None:
            followed_list = get_followed_scholarships()

        results = {}
        for sch in followed_list:
            name = sch["name"]
            results[name] = self.generate_all(sch)

        self._save(results)
        return results

    def regenerate_section(self, scholarship_name, doc_type, section_name):
        all_scholarships = load_core_scholarships()
        sch = None
        for s in all_scholarships:
            if s["name"].lower().strip() == scholarship_name.lower().strip():
                sch = s
                break
        if not sch:
            return {"error": f"Scholarship '{scholarship_name}' not found"}

        result = self.generate_doc(sch, doc_type, regenerate_section=section_name)
        current = self._load()
        if scholarship_name in current and doc_type in current[scholarship_name]:
            current[scholarship_name][doc_type] = result
        self._save(current)
        return result

    def _load(self):
        if os.path.exists(MY_DOCS_FILE):
            with open(MY_DOCS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self, data):
        existing = self._load()
        for sch_name, doc_types in data.items():
            if sch_name not in existing:
                existing[sch_name] = {}
            for doc_type, content in doc_types.items():
                if "content" in content and content["content"]:
                    existing[sch_name][doc_type] = content
                elif doc_type not in existing[sch_name] or "content" not in existing[sch_name].get(doc_type, {}):
                    existing[sch_name][doc_type] = content
        with open(MY_DOCS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

    def get_all_docs(self):
        return self._load()

    def get_scholarship_docs(self, scholarship_name):
        docs = self._load()
        return docs.get(scholarship_name, {})


def get_supported_types():
    return [{"id": k, "label": v["label"], "sections": v["sections"]} for k, v in DOCUMENT_TEMPLATES.items()]
