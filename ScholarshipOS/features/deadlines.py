from datetime import datetime, date
import json
import os


class DeadlineTracker:
    def __init__(self, profile):
        self.profile = profile
        self.alerts = []

    def calculate(self, scholarships_data, universities_data):
        print("\n=== DEADLINE COUNTDOWN & ALERTS ===")
        today = date.today()
        results = []

        print(f"  Today's date: {today.strftime('%B %d, %Y')}")
        print()

        for s in scholarships_data:
            dl_str = s.get("deadline_end") or s.get("deadline", "")
            if not dl_str or dl_str in ("Check", "Unknown", "TBD", "Check website", "Varies", "N/A"):
                continue

            dl = self._parse_date(dl_str)
            if not dl:
                continue

            remaining = (dl - today).days
            status = self._get_status(remaining)
            urgency = self._get_urgency(remaining)

            results.append({
                "name": s.get("name", "Unknown"),
                "type": "scholarship",
                "deadline": dl_str,
                "deadline_date": dl.isoformat(),
                "remaining_days": remaining,
                "status": status,
                "urgency": urgency,
                "country": s.get("country", "Unknown"),
                "amount": s.get("amount", ""),
            })

            if 0 <= remaining <= 30:
                self.alerts.append(results[-1])
                print(f"  ⚠️ ALERT: {s.get('name')} deadline in {remaining}d ({dl_str})")

        for u in universities_data:
            deadlines_to_check = []
            if u.get("deadline_winter"):
                deadlines_to_check.append((u.get("deadline_winter"), "Winter Intake"))
            if u.get("deadline_summer"):
                deadlines_to_check.append((u.get("deadline_summer"), "Summer Intake"))
            if u.get("deadline"):
                deadlines_to_check.append((u.get("deadline"), "Deadline"))

            for dl_str, label in deadlines_to_check:
                if not dl_str or dl_str in ("Check", "Unknown", "TBD", "Check website", "Varies", "N/A"):
                    continue

                for raw_dl in dl_str.split(";"):
                    raw_dl = raw_dl.strip()
                    dl = self._parse_date(raw_dl)
                    if not dl:
                        continue

                    remaining = (dl - today).days
                    status = self._get_status(remaining)
                    urgency = self._get_urgency(remaining)

                    results.append({
                        "name": f"{u.get('name', 'Unknown')} ({label})",
                        "type": "university",
                        "deadline": raw_dl,
                        "deadline_date": dl.isoformat(),
                        "remaining_days": remaining,
                        "status": status,
                        "urgency": urgency,
                        "country": u.get("country", "Unknown"),
                        "program": u.get("program", ""),
                    })

                    if 0 <= remaining <= 30:
                        self.alerts.append(results[-1])
                        print(f"  ⚠️ ALERT: {u.get('name')} ({label}) deadline in {remaining}d ({raw_dl})")

        results.sort(key=lambda x: x["remaining_days"] if x["remaining_days"] >= 0 else 9999)

        print(f"\n  {'='*60}")
        print(f"  UPCOMING DEADLINES (sorted by urgency)")
        print(f"  {'='*60}")

        for r in results:
            if r["remaining_days"] < -365:
                continue
            d = r["remaining_days"]
            if d < 0:
                label = f"PAST DUE ({abs(d)} days ago)"
                icon = "❌"
            elif d == 0:
                label = "DUE TODAY!"
                icon = "🔥"
            elif d <= 7:
                label = f"Due in {d}d 🔥"
                icon = "💥"
            elif d <= 30:
                label = f"Due in {d}d ⚠️"
                icon = "❗"
            elif d <= 90:
                label = f"Due in {d}d"
                icon = "🕒"
            else:
                label = f"Due in {d}d"
                icon = "📅"

            prefix = "Scholarship" if r["type"] == "scholarship" else "University"
            print(f"  {icon} {prefix}: {r['name']}")
            print(f"     Deadline: {r['deadline']} | {label}")
            print()

        print(f"\n  Total deadlines tracked: {len(results)}")
        print(f"  Immediate alerts (<=30d): {len(self.alerts)}")
        print()

        self.save_alerts()
        self._save_for_dashboard(results)
        return results

    def _parse_date(self, date_str):
        if not date_str:
            return None
        s = str(date_str).strip()
        
        # Clean parenthesis comments
        if "(" in s:
            s = s.split("(")[0].strip()

        # Handle split representations, e.g. "August/September" -> "September"
        if "/" in s and not s.replace("/", "").isdigit():
            parts = s.split("/")
            s = parts[-1].strip()
            
        current_year = datetime.now().year
        
        # 1. Try standard full dates
        formats = [
            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", 
            "%B %d, %Y", "%d %B %Y", "%b %d, %Y", "%d %b %Y"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue

        # 2. Try dates missing a year (e.g., "September 1" or "Nov 3")
        for fmt in ["%B %d", "%d %B", "%b %d", "%d %b"]:
            try:
                dt = datetime.strptime(f"{s}, {current_year}", f"{fmt}, %Y")
                dl_date = dt.date()
                if dl_date < date.today():
                    dl_date = date(dl_date.year + 1, dl_date.month, dl_date.day)
                return dl_date
            except ValueError:
                continue

        # 3. Try Month Year (e.g. "October 2026")
        for fmt in ["%B %Y", "%b %Y"]:
            try:
                dt = datetime.strptime(s, fmt)
                return date(dt.year, dt.month, 28)
            except ValueError:
                continue

        # 4. Try Month only (missing year)
        for fmt in ["%B", "%b"]:
            try:
                dt = datetime.strptime(f"{s} {current_year}", f"{fmt} %Y")
                dl_date = date(dt.year, dt.month, 28)
                if dl_date < date.today():
                    dl_date = date(dl_date.year + 1, dl_date.month, dl_date.day)
                return dl_date
            except ValueError:
                continue

        # 5. Try Year only
        try:
            return date(int(s), 12, 15)
        except ValueError:
            pass

        return None

    def _get_status(self, days):
        if days < 0:
            return "past_due"
        elif days == 0:
            return "due_today"
        elif days <= 7:
            return "critical"
        elif days <= 30:
            return "warning"
        elif days <= 90:
            return "upcoming"
        else:
            return "normal"

    def _get_urgency(self, days):
        if days < 0:
            return "OVERDUE"
        elif days <= 7:
            return "IMMEDIATE"
        elif days <= 30:
            return "URGENT"
        elif days <= 90:
            return "SOON"
        else:
            return "FAR"

    def save_alerts(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "deadline_alerts.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.alerts, f, indent=2, ensure_ascii=False)

    def _save_for_dashboard(self, results):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "deadlines.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
