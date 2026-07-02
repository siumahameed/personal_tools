from datetime import datetime, timedelta
import json
import os


class TimelineGenerator:
    def __init__(self, profile, data_dir=None):
        self.profile = profile
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "data"
        )

    @staticmethod
    def _month_offset(date, months):
        target_month = date.month - 1 + months
        target_year = date.year + target_month // 12
        target_month = target_month % 12 + 1
        import calendar
        last_day = calendar.monthrange(target_year, target_month)[1]
        target_day = min(date.day, last_day)
        return date.replace(year=target_year, month=target_month, day=target_day)

    def generate(self):
        print("\n=== TIMELINE & ROADMAP ===")
        now = datetime.now()
        year = now.year
        six_months = self._month_offset(now, 6)

        milestones = [
            {
                "phase": "Now - Preparation",
                "period": f"{now.strftime('%B %Y')}",
                "tasks": [
                    "Research universities and programs (use ScholarAI agents)",
                    "Start IELTS/TOEFL preparation",
                    "Prepare academic documents (transcripts, certificates)",
                    "Build your portfolio (Kaggle, GitHub projects)",
                    "Connect with professors on LinkedIn",
                ],
                "priority": "High",
            },
            {
                "phase": "6 Months Before",
                "period": f"~{six_months.strftime('%B %Y')}",
                "tasks": [
                    "Take IELTS/TOEFL exam (target: IELTS 6.5+/TOEFL 88+)",
                    "Prepare CV/Resume (German format)",
                    "Draft Motivation Letter / SOP",
                    "Request Letters of Recommendation from professors",
                    "Begin DAAD scholarship application",
                ],
                "priority": "High",
            },
            {
                "phase": "Application Season (Germany + USA)",
                "period": "~April - July",
                "tasks": [
                    "Submit DAAD scholarship application (deadline varies: ~Aug-Sep)",
                    "Apply to Erasmus Mundus programs (deadline: Oct-Feb)",
                    "Submit German university applications via uni-assist",
                    "Prepare Fulbright application (US Embassy Dhaka deadline varies)",
                    "Apply to US universities (Stanford, MIT, CMU, etc. - deadlines Oct-Dec)",
                    "Prepare for possible interviews",
                    "Apply for Deutschlandstipendium (if enrolled)",
                ],
                "priority": "Critical",
            },
            {
                "phase": "GERMANY: DAAD (Primary Target)",
                "period": "~August - September",
                "tasks": [
                    "COMPLETE DAAD application with all documents",
                    "Motivation letter (max 2 pages)",
                    "Research proposal / study plan",
                    "Letters of recommendation (2)",
                    "Academic transcripts (translated + notarized)",
                    "CV (Europass format recommended)",
                    "Language certificate (German A1-A2 recommended)",
                ],
                "priority": "CRITICAL",
            },
            {
                "phase": "GERMANY: Erasmus Mundus",
                "period": "~October - February",
                "tasks": [
                    "Choose 3 Erasmus Mundus programs",
                    "Complete online application for each",
                    "Prepare joint motivation letter + program-specific SOP",
                    "Submit transcripts, CV, recommendations",
                    "Apply early (rolling admissions for some programs)",
                ],
                "priority": "CRITICAL",
            },
            {
                "phase": "USA: Fulbright + University Applications",
                "period": "~October - February",
                "tasks": [
                    "Complete Fulbright application (US Embassy Dhaka)",
                    "Apply to US universities (Fall intake: deadlines Oct-Dec)",
                    "Take GRE (required by most US programs)",
                    "Prepare TOEFL/IELTS (target 95+/7.0 for US schools)",
                    "Request Letters of Recommendation (3 for US)",
                    "Write tailored SOP for each US university",
                    "Apply for Knight-Hennessy (Stanford) if applying to Stanford",
                ],
                "priority": "CRITICAL",
            },
            {
                "phase": "After Admission (Germany or USA)",
                "period": "~August - October (following year)",
                "tasks": [
                    "Accept best offer and enroll",
                    "Germany: Apply for student visa (6-12 weeks), Blocked account (11,208 EUR)",
                    "USA: Apply for F-1 visa (3-6 months), Financial documents",
                    "Health insurance enrollment (Germany: public, USA: university plan)",
                    "Find accommodation (Germany: Studentenwerk, USA: on-campus/off-campus)",
                    "Book flights, plan arrival, orientation week",
                ],
                "priority": "High",
            },
        ]

        print(f"\n  Timeline generated for: {self.profile['name']}")
        print(f"  Target: {', '.join(self.profile['target_countries'])} | {', '.join(self.profile['target_fields'])}")
        print(f"  Current: {self.profile['current_education']} (GPA: {self.profile['gpa']})")
        print()

        for m in milestones:
            print(f"  [{m['priority']}] {m['phase']} ({m['period']})")
            for t in m['tasks']:
                print(f"     - {t}")
            print()

        self._save(milestones)
        return milestones

    def _save(self, data):
        path = os.path.join(self.data_dir, "timeline.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Timeline saved to data/timeline.json")
