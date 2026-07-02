import os
import json
from datetime import datetime


TEMPLATES = {
    "initial_contact": {
        "name": "Initial Contact - MSc Interest",
        "subject": "Prospective MSc Applicant - Interest in {research_area} Research",
        "body": """Dear Prof. {professor_name},

My name is {your_name}, and I am a final-year undergraduate student in Statistics at Dhaka College, Bangladesh. I am writing to express my strong interest in pursuing an MSc in {program_name} at {university}.

I have been following your research on {research_interest} with great interest. Specifically, your work on {specific_paper_or_topic} aligns closely with my academic interests in {your_interest}.

My background in Statistics has given me strong foundations in {skills}, and I have been actively building my Machine Learning skills through {projects_or_courses}.

I would be honored to have the opportunity to work under your supervision. Could we schedule a brief call to discuss potential research directions?

I have attached my CV and academic transcripts for your reference.

Thank you for your time and consideration.

Best regards,
{your_name}
{your_email}
BSc in Statistics, Dhaka College
LinkedIn: {linkedin_url}""",
    },
    "research_inquiry": {
        "name": "Research Inquiry - PhD/MSc Position",
        "subject": "Inquiry about MSc Research Opportunities in {research_area}",
        "body": """Dear Prof. {professor_name},

I hope this email finds you well. I am {your_name}, a Statistics undergraduate from Dhaka College, Bangladesh, planning to apply for MSc programs starting {year}.

I am deeply interested in {research_area}, and your research group's recent work on {specific_topic} particularly resonates with my academic aspirations. Having read your paper "{paper_title}," I was inspired by {specific_aspect}.

My academic training in Statistics has equipped me with {skills}, and I have completed projects in {projects}. I am particularly drawn to your work because it bridges theoretical foundations with practical applications.

Would you be open to discussing potential MSc research opportunities in your group starting {year}? I would greatly appreciate any guidance on the application process or prerequisites for joining your lab.

I have attached my CV and would be happy to provide any additional information.

Thank you for your time.

Warm regards,
{your_name}
{your_email}""",
    },
    "short_inquiry": {
        "name": "Short Inquiry - Quick Intro",
        "subject": "MSc Application Inquiry - {research_area} ({university})",
        "body": """Dear Prof. {professor_name},

My name is {your_name}, a final-year Statistics student at Dhaka College, Bangladesh.

I am planning to apply for the MSc in {program_name} at {university} and am very interested in your research on {research_interest}.

Would you be available for a brief conversation about your research directions and whether there might be a good fit for collaboration?

I have attached my CV for your reference.

Thank you.

Best,
{your_name}
{your_email}""",
    },
    "follow_up": {
        "name": "Follow Up - After No Reply",
        "subject": "Re: Prospective MSc Applicant - {research_area}",
        "body": """Dear Prof. {professor_name},

I am following up on my previous email sent on {previous_date}. I understand you are very busy, so I wanted to respectfully remind you of my inquiry about MSc research opportunities in {research_area} at {university}.

I remain very interested in your research group's work, particularly {specific_topic}. Since my last email, I have {new_development}.

I have attached my CV and would be grateful for any opportunity to discuss potential supervision.

Thank you for your consideration.

Best regards,
{your_name}
{your_email}""",
    },
}

DEFAULT_VARS = {
    "your_name": "Sium Ahameed Bhuyan",
    "your_email": "your.email@example.com",
    "your_phone": "",
    "linkedin_url": "https://www.linkedin.com/in/sium11",
    "profile": "BSc in Statistics, Dhaka College (GPA: 3.20/4.00)",
    "skills": "Statistics, Probability Theory, Regression Analysis, Python, R, SQL, Machine Learning fundamentals",
    "projects_or_courses": "self-study in Machine Learning (Andrew Ng's course), LinkedIn Data Analytics certification, Kaggle competitions",
    "your_interest": "Machine Learning, Data Science, and Statistical Learning Theory",
    "new_development": "completed additional coursework in Python for Data Science and started working on a research proposal for DAAD scholarship",
    "year": "2026",
}


class EmailDraftGenerator:
    def __init__(self, profile):
        self.profile = profile

    def generate(self, professor, template_key="initial_contact", interactive=True):
        if interactive:
            print("\n=== EMAIL DRAFT GENERATOR ===")
            print(f"  Generating email draft for: {professor.get('name', 'Professor')}")
            print(f"  University: {professor.get('university', 'Unknown')}")
            print()
            print("  Available templates:")
            templates_list = list(TEMPLATES.items())
            for i, (key, tpl) in enumerate(templates_list):
                print(f"    {i+1}. {tpl['name']}")
            print()
            choice = input("  Choose template (1-{}): ".format(len(templates_list))).strip()
            try:
                idx = int(choice) - 1
                template_key = list(TEMPLATES.keys())[idx]
            except (ValueError, IndexError):
                print("  Using default: initial_contact")
                template_key = "initial_contact"

        template = TEMPLATES[template_key]

        vars = dict(DEFAULT_VARS)
        vars["professor_name"] = self._format_name(professor.get("name", "Professor"))
        vars["university"] = professor.get("university", "Unknown")
        vars["program_name"] = professor.get("supervisor_for", professor.get("supervisor_for", "MSc in related field")).split(" - ")[0] if " - " in str(professor.get("supervisor_for", "")) else professor.get("supervisor_for", "MSc program")
        vars["research_area"] = self._extract_research_area(professor)
        vars["research_interest"] = professor.get("interests", "Machine Learning")[:100]
        vars["specific_paper_or_topic"] = professor.get("papers", "your recent publications").split(";")[0] if ";" in str(professor.get("papers", "")) else str(professor.get("papers", "your recent work"))[:100]
        vars["specific_topic"] = professor.get("interests", "Machine Learning").split(",")[0] if "," in str(professor.get("interests", "")) else str(professor.get("interests", "Machine Learning"))[:60]
        vars["paper_title"] = professor.get("papers", "your recent paper").split(";")[0] if ";" in str(professor.get("papers", "")) else str(professor.get("papers", "your recent paper"))[:80]
        vars["specific_aspect"] = "the novel methodology and potential applications"
        vars["previous_date"] = (datetime.now().strftime("%B %d"))

        subject = template["subject"].format(**vars)
        body = template["body"].format(**vars)

        if interactive:
            print(f"\n  {'='*60}")
            print(f"  SUBJECT: {subject}")
            print(f"  TO: {professor.get('email', 'professor@university.edu')}")
            print(f"  {'='*60}")
            print(f"\n{body}")
            print(f"\n  {'='*60}")
            print()
            save = input("  Save this draft? (yes/no): ").strip().lower()
            if save == "yes":
                filename = f"email_draft_{professor.get('name', 'professor').replace(' ', '_').replace('.', '')}.txt"
                path = os.path.join(os.path.dirname(__file__), "..", "..", "data", filename)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"TO: {professor.get('email', '')}\n")
                    f.write(f"SUBJECT: {subject}\n")
                    f.write(f"\n{body}\n")
                print(f"  Saved to data/{filename}")
            else:
                print("  Not saved.")

        return {"subject": subject, "body": body, "to": professor.get("email", "")}

    def _format_name(self, name):
        name = str(name).replace("Prof. ", "").replace("Dr. ", "")
        parts = name.split()
        return "Dr. " + " ".join(parts[:2]) if len(parts) >= 2 else "Dr. " + name

    def _extract_research_area(self, prof):
        interests = str(prof.get("interests", ""))
        if interests and interests != "Check":
            return interests.split(",")[0].strip()[:60]
        papers = str(prof.get("papers", ""))
        if papers and papers != "Check":
            return papers.split(";")[0].strip()[:60] if ";" in papers else papers[:60]
        return "Machine Learning"

    def interactive(self, professors_data):
        print("\n=== EMAIL DRAFT GENERATOR ===")
        print(f"  Available professors with known emails:")

        with_email = [p for p in professors_data
                     if p.get("email") and "@" in str(p["email"]) and str(p["email"]) != "Check profile"]

        if not with_email:
            print("  No professors with emails found in current data.")
            print("  Run Professor Research Agent first or provide professor data.")
            return

        for i, p in enumerate(with_email):
            print(f"    {i+1}. {p.get('name', 'Unknown')} @ {p.get('university', 'Unknown')}")
            print(f"       {p.get('email', '')} | {p.get('interests', '')[:60]}...")
            print()

        choice = input(f"  Choose professor (1-{len(with_email)}): ").strip()
        try:
            idx = int(choice) - 1
            professor = with_email[idx]
        except (ValueError, IndexError):
            print("  Invalid choice.")
            return

        self.generate(professor)
