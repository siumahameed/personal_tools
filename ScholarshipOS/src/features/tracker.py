import json
import os
from datetime import datetime


HEADERS = [
    "Item Type",
    "Name",
    "University",
    "Status",
    "Deadline",
    "Date Applied",
    "Date Accepted",
    "Notes",
]


class ApplicationTracker:
    def __init__(self, sheets_client=None, data_dir=None):
        self.sheets = sheets_client
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "data"
        )
        self.tracker_file = os.path.join(self.data_dir, "tracker.json")
        self.applications = self._load()

    def _load(self):
        if os.path.exists(self.tracker_file):
            with open(self.tracker_file, "r") as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.tracker_file, "w") as f:
            json.dump(self.applications, f, indent=2, ensure_ascii=False)

    def add(self, item_type, name, university, deadline, notes=""):
        app = {
            "item_type": item_type,
            "name": name,
            "university": university,
            "status": "Not Started",
            "deadline": deadline,
            "date_applied": "",
            "date_accepted": "",
            "notes": notes,
            "created_at": datetime.now().isoformat(),
        }
        self.applications.append(app)
        self._save()
        self._sync_sheets()
        print(f"  Added to tracker: {item_type} - {name}")

    def update_status(self, index, status, date_accepted=""):
        if 0 <= index < len(self.applications):
            self.applications[index]["status"] = status
            self.applications[index]["date_applied"] = datetime.now().strftime("%Y-%m-%d")
            if date_accepted:
                self.applications[index]["date_accepted"] = date_accepted
            self._save()
            self._sync_sheets()

    def show(self):
        print("\n=== APPLICATION TRACKER ===")
        if not self.applications:
            print("  No applications tracked yet. Run scholarship/uni agents first.")
            return

        for i, app in enumerate(self.applications):
            status_icon = {
                "Not Started": "O",
                "Applied": "~",
                "Interview": "!",
                "Accepted": "✓",
                "Rejected": "✗",
                "Deferred": "→",
            }.get(app["status"], "?")
            print(f"  [{status_icon}] {i+1}. {app['name']}")
            print(f"       Type: {app['item_type']} | Uni: {app['university']}")
            print(f"       Status: {app['status']} | Deadline: {app['deadline']}")
            if app["notes"]:
                print(f"       Notes: {app['notes']}")
            print()

    def run(self):
        self.show()

        print("\n  Options:")
        print("   1. Add new application")
        print("   2. Update status")
        print("   3. Exit")
        choice = input("  Choose (1-3): ").strip()

        if choice == "1":
            item_type = input("  Type (scholarship/university): ").strip()
            name = input("  Name: ").strip()
            uni = input("  University: ").strip()
            deadline = input("  Deadline (YYYY-MM-DD): ").strip()
            notes = input("  Notes (optional): ").strip()
            self.add(item_type, name, uni, deadline, notes)
        elif choice == "2":
            idx = int(input("  Index number: ").strip()) - 1
            print("  Status options: Applied, Interview, Accepted, Rejected")
            status = input("  New status: ").strip()
            date_acc = ""
            if status.lower() == "accepted":
                date_acc = input("  Date accepted (YYYY-MM-DD): ").strip()
            self.update_status(idx, status, date_acc)

    def _sync_sheets(self):
        if not self.sheets:
            return
        rows = [[
            a["item_type"],
            a["name"],
            a["university"],
            a["status"],
            a["deadline"],
            a["date_applied"],
            a["date_accepted"],
            a["notes"],
        ] for a in self.applications]
        self.sheets.sync_table("Tracker", HEADERS, rows)
