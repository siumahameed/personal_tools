import json
import os


HEADERS = ["Category", "Item", "Required For", "Status", "Notes"]

GENERAL_DOCS = [
    ["Academic", "Bachelor's Degree Certificate (original + translated)", "All universities & DAAD", "Not Started", "Must be notarized German translation"],
    ["Academic", "Academic Transcripts (all semesters)", "All universities & DAAD", "Not Started", "Must be notarized German translation"],
    ["Academic", "GPA/CGPA Certificate", "All universities & DAAD", "Not Started", "From Dhaka College"],
    ["Academic", "Course Descriptions / Module Handbook", "Many German unis", "Not Started", "For credit evaluation"],
    ["Language", "IELTS Academic (6.5+) or TOEFL (88+)", "All English-taught programs", "Not Started", "Book test date"],
    ["Language", "German Language Certificate (A1-A2 recommended)", "DAAD + daily life", "Not Started", "DAAD prefers some German knowledge"],
    ["Test", "GRE General Test", "Most US universities (Stanford, MIT, CMU, etc.)", "Not Started", "Required for most US MSc programs; aim for 320+ (quant 165+)"],
    ["Test", "TOEFL (95+) or IELTS (7.0+)", "US universities (higher than German requirements)", "Not Started", "US schools typically require TOEFL 100 / IELTS 7.0+"],
    ["Documents", "CV / Resume (Europass format)", "All applications", "Not Started", "Max 2 pages, German style"],
    ["Documents", "Motivation Letter / Statement of Purpose", "All applications", "Not Started", "Tailor per program"],
    ["Documents", "Research Proposal / Study Plan", "DAAD + some PhD-prep programs", "Not Started", "Max 5 pages for DAAD"],
    ["Documents", "Letters of Recommendation (2-3)", "DAAD + most universities", "Not Started", "From Statistics professors"],
    ["Documents", "Passport Copy", "All applications", "Not Started", "Valid for >2 years"],
    ["Financial", "Blocked Account Setup (~11,208 EUR)", "Student visa (Germany)", "Not Started", "Required for visa"],
    ["Financial", "Proof of Financial Resources", "Visa + some applications", "Not Started", "Blocked account + scholarship proof"],
    ["Visa", "Student Visa Application (Germany)", "Before travel", "Not Started", "6-12 weeks processing"],
    ["Visa", "Health Insurance (German public)", "Visa + enrollment", "Not Started", "~120 EUR/month"],
    ["Academic", "GRE Test (recommended)", "TUM + some competitive programs", "Not Started", "Not mandatory but helps"],
]


class DocumentChecklist:
    HEADERS = ["Category", "Item", "Required For", "Status", "Notes"]

    def __init__(self, profile, sheets_client=None, data_dir=None):
        self.profile = profile
        self.sheets = sheets_client
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "data"
        )
        self.checklist_file = os.path.join(self.data_dir, "checklist.json")
        self.items = self._load()

    def _load(self):
        if os.path.exists(self.checklist_file):
            with open(self.checklist_file, "r") as f:
                return json.load(f)
        return [list(item) for item in GENERAL_DOCS]

    def _save(self):
        with open(self.checklist_file, "w") as f:
            json.dump(self.items, f, indent=2, ensure_ascii=False)

    def show(self):
        print("\n=== DOCUMENT CHECKLIST ===")
        categories = {}
        for item in self.items:
            cat = item[0]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        idx = 1
        for cat, items in categories.items():
            print(f"\n  [{cat}]")
            done = sum(1 for i in items if i[3] == "Completed")
            total = len(items)
            print(f"  Progress: {done}/{total}")
            for item in items:
                status_icon = "✓" if item[3] == "Completed" else "○"
                print(f"    [{idx}] {status_icon} {item[1]}")
                print(f"       For: {item[2]} | Status: {item[3]}")
                if item[4]:
                    print(f"       Note: {item[4]}")
                idx += 1

        self._sync_sheets()

    def update(self, index, status, note=""):
        if 0 <= index < len(self.items):
            self.items[index][3] = status
            if note:
                self.items[index][4] = note
            self._save()

    def run(self):
        self.show()
        print("\n  Options:")
        print("   1. Mark item as Completed")
        print("   2. Add note to item")
        print("   3. Exit")
        choice = input("  Choose (1-3): ").strip()

        if choice in ("1", "2"):
            idx = int(input("  Item number (1-{}): ".format(len(self.items))).strip()) - 1
            if 0 <= idx < len(self.items):
                if choice == "1":
                    self.update(idx, "Completed")
                    print(f"  ✓ Marked '{self.items[idx][1]}' as Completed!")
                else:
                    note = input("  Note: ").strip()
                    self.update(idx, self.items[idx][3], note)
                    print(f"  Note added!")
                self.show()

    def _sync_sheets(self):
        if not self.sheets:
            return
        headers = HEADERS
        rows = [item[:len(headers)] for item in self.items]
        self.sheets.sync_table("Checklist", headers, rows)
