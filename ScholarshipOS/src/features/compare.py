import json
import os


class ComparisonEngine:
    def __init__(self, profile):
        self.profile = profile

    def compare_scholarships(self, scholarships_data, names):
        selected = [s for s in scholarships_data if s.get("name") in names]
        if len(selected) < 2:
            print("  Need at least 2 scholarships to compare.")
            return {}
        self._render_table(selected)

        scores = self._score_all(selected)
        self._recommend(scores)
        return {"selected": selected, "scores": scores}

    def compare_universities(self, universities_data, names):
        selected = [u for u in universities_data if u.get("name") in names]
        if len(selected) < 2:
            print("  Need at least 2 universities to compare.")
            return {}
        self._render_table(selected)

        scores = self._score_all(selected, is_uni=True)
        self._recommend(scores)
        return {"selected": selected, "scores": scores}

    def interactive(self, scholarships_data, universities_data):
        print("\n=== SIDE-BY-SIDE COMPARISON ===")
        print("  1. Compare Scholarships")
        print("  2. Compare Universities")
        choice = input("  Choose (1-2): ").strip()

        if choice == "1":
            items = scholarships_data
            key = "name"
        elif choice == "2":
            items = universities_data
            key = "name"
        else:
            print("  Invalid choice.")
            return

        print(f"\n  Available items:")
        for i, item in enumerate(items):
            country = item.get("country", "")
            flag = "\U0001f1e9\U0001f1ea" if "germany" in country.lower() else "\U0001f1fa\U0001f1f8"
            print(f"    {i+1}. {flag} {item.get(key, 'Unknown')}")

        print()
        indices = input("  Enter numbers to compare (comma-separated, e.g. 1,2,3): ").strip()
        try:
            idxs = [int(x.strip()) - 1 for x in indices.split(",")]
            selected = [items[i] for i in idxs]
            names = [s.get(key) for s in selected]
        except (ValueError, IndexError):
            print("  Invalid selection.")
            return

        if choice == "1":
            return self.compare_scholarships(scholarships_data, names)
        else:
            return self.compare_universities(universities_data, names)

    def _render_table(self, items):
        key_fields = ["name", "country", "amount", "deadline", "duration",
                      "university", "program", "location", "fee", "living_cost",
                      "gre_required", "min_gpa", "toefl_required"]
        print(f"\n  {'='*80}")
        print(f"  SIDE-BY-SIDE COMPARISON")
        print(f"  {'='*80}")

        for field in key_fields:
            values = []
            for item in items:
                v = str(item.get(field, "\u2014"))
                if v == "Check" or v == "Unknown" or v == "":
                    v = "\u2014"
                values.append(v)
            if any(v != "\u2014" for v in values):
                label = field.replace("_", " ").title()
                print(f"\n  {label}:")
                for i, item in enumerate(items):
                    print(f"    [{i+1}] {values[i]}")

        print(f"\n  {'='*80}")

    def _score_all(self, items, is_uni=False):
        scores = {}
        for item in items:
            s = self._score_item(item, is_uni)
            scores[item.get("name", "Unknown")] = s
        return scores

    def _score_item(self, item, is_uni=False):
        score = 0
        details = []

        fee_key = "app_fee" if is_uni else "fee"
        fee_val = item.get(fee_key, "")
        fee_str = str(fee_val)
        digits_only = "".join(c for c in fee_str if c.isdigit() or c == ".")
        if digits_only and digits_only.replace(".", "").isdigit():
            val = float(digits_only)
            if is_uni:
                if val < 30000:
                    score += 3
                    details.append(f"Low fees: ${val:,.0f}")
                elif val < 50000:
                    score += 1
                    details.append(f"Moderate fees: ${val:,.0f}")
            else:
                if val > 30000:
                    score += 3
                    details.append(f"High amount: ${val:,.0f}/yr")
                elif val > 15000:
                    score += 1
                    details.append(f"Moderate amount: ${val:,.0f}/yr")

        amount = item.get("amount", "")
        if isinstance(amount, str) and any(c.isdigit() for c in amount):
            score += 2
            details.append(f"Monetary value: {amount}")

        dl_str = item.get("deadline", "") or item.get("deadline_end", "")
        if dl_str and dl_str not in ("Check", "Unknown", "TBD"):
            score += 1
            details.append(f"Deadline known: {dl_str}")

        gre = item.get("gre", "")
        if isinstance(gre, str):
            gre_lower = gre.lower()
            if gre_lower in ("not required", "no"):
                score += 1
                details.append("No GRE required")
            elif gre_lower in ("optional", "recommended"):
                score += 2
                details.append("GRE optional")

        gpa = item.get("min_gpa", "")
        if is_uni:
            score += 1
            details.append(f"GPA required: {gpa}")

        details_str = "; ".join(details) if details else "Standard option"
        return {
            "total": score,
            "details": details_str,
        }

    def _recommend(self, scores):
        if not scores:
            return
        best = max(scores, key=lambda k: scores[k]["total"])
        print(f"\n  *** RECOMMENDATION: {best}")
        print(f"     Best overall score: {scores[best]['total']} points")
        print(f"     Key strengths: {scores[best]['details']}")
        print()
