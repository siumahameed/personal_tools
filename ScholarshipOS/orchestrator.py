import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import PROFILE, SHEETS_CONFIG
from data.data_loader import load_core_scholarships, load_core_universities, load_core_professors
from agents.scholarship import ScholarshipAgent
from agents.university import UniversityAgent
from agents.professor import ProfessorAgent
from agents.target import TargetEnricherAgent
from features.timeline import TimelineGenerator
from features.tracker import ApplicationTracker
from features.checklist import DocumentChecklist
from features.match_score import MatchScoreCalculator
from features.cost import CostComparison
from features.email_drafts import EmailDraftGenerator
from features.deadlines import DeadlineTracker
from features.compare import ComparisonEngine


class Orchestrator:
    def __init__(self, sheets_client=None, interactive=True):
        self.sheets = sheets_client
        self.scholarship_agent = ScholarshipAgent(sheets_client, interactive)
        self.university_agent = UniversityAgent(sheets_client, interactive)
        self.professor_agent = ProfessorAgent(sheets_client, interactive)
        self.target_enricher = TargetEnricherAgent(PROFILE, sheets_client, interactive)
        self.tracker = ApplicationTracker(sheets_client)
        self.checklist = DocumentChecklist(PROFILE, sheets_client)
        self.matcher = MatchScoreCalculator(PROFILE)
        self.cost_comp = CostComparison(PROFILE, sheets_client)
        self.timeline_gen = TimelineGenerator(PROFILE)
        self.email_gen = EmailDraftGenerator(PROFILE)
        self.deadline_tracker = DeadlineTracker(PROFILE)
        self.comparison = ComparisonEngine(PROFILE)
        self._core_scholarships = None
        self._core_universities = None
        self._core_professors = None

    def _get_scholarships(self):
        if self._core_scholarships is None:
            self._core_scholarships = load_core_scholarships()
        return self._core_scholarships

    def _get_universities(self):
        if self._core_universities is None:
            self._core_universities = load_core_universities()
        return self._core_universities

    def _get_professors(self):
        if self._core_professors is None:
            self._core_professors = load_core_professors()
        return self._core_professors

    def show_welcome(self):
        print("=" * 60)
        print("  ScholarAI Agent")
        print("  Autonomous Scholarship & Admission Research System")
        print("=" * 60)
        print(f"\n  Welcome, {PROFILE['name']}!")
        print(f"  Target: {', '.join(PROFILE['target_countries'])}")
        print(f"  Fields: {', '.join(PROFILE['target_fields'])}")
        print(f"  Current: {PROFILE['current_education']} (GPA: {PROFILE['gpa']})")
        print(f"\n  Top priorities: DAAD, Erasmus Mundus, Fulbright, Knight-Hennessy")
        print(f"  Strategy: Germany first (FREE tuition + DAAD/Erasmus), USA backup (Fulbright/KH)")
        print()

    def menu(self):
        while True:
            print("\n" + "=" * 60)
            print("  MAIN MENU")
            print("=" * 60)
            print("  1. Research Scholarships")
            print("  2. Research Universities")
            print("  3. Research Professors")
            print("  4. Run ALL Agents (Full Scan)")
            print("  5. View Timeline & Roadmap")
            print("  6. Application Tracker")
            print("  7. Document Checklist")
            print("  8. Scholarship Match Scores")
            print("  9. Cost Comparison")
            print("  10. Email Draft Generator")
            print("  11. Deadline Countdown & Alerts")
            print("  12. Side-by-Side Comparison")
            print("  13. Launch Web Dashboard")
            print("  0. Exit")
            print()

            choice = input("  Choose (0-13): ").strip()

            if choice == "1":
                self.scholarship_agent.run()
            elif choice == "2":
                self.university_agent.run()
            elif choice == "3":
                self.professor_agent.run()
            elif choice == "4":
                self.run_all()
            elif choice == "5":
                self.timeline_gen.generate()
            elif choice == "6":
                self.tracker.run()
            elif choice == "7":
                self.checklist.run()
            elif choice == "8":
                self.matcher.get_recommendations()
            elif choice == "9":
                self.cost_comp.show()
            elif choice == "10":
                self.run_email_drafts()
            elif choice == "11":
                self.run_deadlines()
            elif choice == "12":
                self.run_comparison()
            elif choice == "13":
                self.launch_dashboard()
            elif choice == "0":
                print("\n  Good luck with your applications, Sium!")
                break

    def run_all(self):
        print("\n" + "=" * 60)
        print("  FULL SYSTEM SCAN")
        print("=" * 60)

        proceed = input("\n  This will run all agents and features. Continue? (yes/no): ").strip().lower()
        if proceed != "yes":
            print("  Cancelled.")
            return

        self.scholarship_agent.run()
        self.university_agent.run()
        self.professor_agent.run()
        self.target_enricher.enrich()
        self.matcher.get_recommendations()
        self.cost_comp.show()
        self.timeline_gen.generate()

        print("\n  Collecting new document samples from GitHub...")
        from agents.document_collector import DocumentCollector
        dc = DocumentCollector(interactive=False)
        new_docs = dc.run()
        print(f"  ✓ {new_docs} new document samples collected")

        print("\n  ✓ Full scan complete! Check the dashboard for all results.")

    def run_email_drafts(self):
        all_profs = self._get_professors()
        self.email_gen.interactive(all_profs)

    def run_deadlines(self):
        self.deadline_tracker.calculate(self._get_scholarships(), self._get_universities())

    def run_comparison(self):
        self.comparison.interactive(
            self._get_scholarships(),
            self._get_universities(),
        )

    def launch_dashboard(self):
        print("\n  Launching Web Dashboard...")
        print("  Opening http://localhost:5000 in your browser...")
        import subprocess
        subprocess.Popen(["python", os.path.join(os.path.dirname(__file__), "dashboard", "app.py")],
                        shell=True)


if __name__ == "__main__":
    orch = Orchestrator()
    orch.show_welcome()
    orch.menu()
