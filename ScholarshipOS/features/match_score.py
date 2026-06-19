import re

HEADERS = [
    "Scholarship / Program",
    "Academic Match",
    "Profile Fit",
    "Competition Level",
    "German Relevance",
    "Overall Score",
    "Recommendation",
]

SCHOLARSHIP_SCORES = [
    {
        "name": "DAAD Scholarship",
        "academic_match": 8,
        "profile_fit": 7,
        "competition": 6,
        "german_relevance": 10,
        "overall": 0,
        "recommendation": "PRIMARY TARGET: Highest priority. Apply regardless of other results.",
        "notes": "Your Statistics background + GPA 3.20 is competitive. Strong motivation letter and research proposal critical.",
    },
    {
        "name": "Erasmus Mundus Joint Masters",
        "academic_match": 9,
        "profile_fit": 8,
        "competition": 5,
        "german_relevance": 7,
        "overall": 0,
        "recommendation": "PRIMARY TARGET: Excellent fit for your interdisciplinary interests.",
        "notes": "Multiple European universities. Joint programs in Data Science and AI. Less competition than DAAD?",
    },
    {
        "name": "KAAD Scholarship",
        "academic_match": 7,
        "profile_fit": 7,
        "competition": 7,
        "german_relevance": 9,
        "overall": 0,
        "recommendation": "GOOD FIT: Bangladesh is eligible. Apply if comfortable.",
        "notes": "Bangladesh is a developing country - KAAD specifically targets your region.",
    },
    {
        "name": "Heinrich Boll Foundation",
        "academic_match": 7,
        "profile_fit": 6,
        "competition": 5,
        "german_relevance": 9,
        "overall": 0,
        "recommendation": "WORTH APPLYING: If you have environmental/social engagement.",
        "notes": "Preference for green politics. Your volunteer work at Volunteer for Bangladesh helps.",
    },
    {
        "name": "Deutschlandstipendium",
        "academic_match": 7,
        "profile_fit": 6,
        "competition": 5,
        "german_relevance": 10,
        "overall": 0,
        "recommendation": "APPLY AFTER ADMISSION: Requires enrollment at German university first.",
        "notes": "Not a full scholarship but good supplement. 300 EUR/month.",
    },
    {
        "name": "Konrad Adenauer Foundation",
        "academic_match": 7,
        "profile_fit": 5,
        "competition": 5,
        "german_relevance": 9,
        "overall": 0,
        "recommendation": "CONSIDER: If you have political/social engagement background.",
        "notes": "More political orientation required. Your Math Olympiad involvement helps.",
    },
    # USA scholarships
    {
        "name": "Fulbright Program (Bangladesh-specific)",
        "academic_match": 8,
        "profile_fit": 8,
        "competition": 6,
        "german_relevance": 0,
        "overall": 0,
        "recommendation": "USA #1 TARGET: Excellent fit for Bangladeshi students. Full-ride.",
        "notes": "Bangladesh-specific Fulbright through US Embassy Dhaka. Your Stats background + GPA 3.20 is competitive.",
    },
    {
        "name": "Knight-Hennessy Scholars (Stanford)",
        "academic_match": 7,
        "profile_fit": 6,
        "competition": 4,
        "german_relevance": 0,
        "overall": 0,
        "recommendation": "REACH: Only for Stanford. Extremely competitive but full-ride.",
        "notes": "Leadership-focused. Need exceptional profile. Apply only if you have strong leadership experience.",
    },
    {
        "name": "US University TA/RA Funding",
        "academic_match": 7,
        "profile_fit": 6,
        "competition": 6,
        "german_relevance": 0,
        "overall": 0,
        "recommendation": "BACKUP: Many US unis offer TA/RA for MSc. Focus on Georgia Tech, UW, UIUC.",
        "notes": "Apply to programs with guaranteed TA/RA. Georgia Tech is most affordable option.",
    },
]


class MatchScoreCalculator:
    def __init__(self, profile):
        self.profile = profile

    def calculate(self, scholarships=None):
        print("\n=== SCHOLARSHIP MATCH SCORES ===")
        edu = self.profile.get('current_education', 'N/A')
        gpa = self.profile.get('gpa', 'N/A')
        fields = self.profile.get('target_fields', [])
        print(f"  Based on your profile: {edu} (GPA: {gpa})")
        if fields:
            print(f"  Target: {', '.join(fields)}")
        print()

        scored = []
        seen_names = set()

        # 1. Process static list first (giving them high priority/curated details)
        for s in SCHOLARSHIP_SCORES:
            name_lower = s["name"].lower()
            if name_lower in seen_names:
                continue
            seen_names.add(name_lower)
            
            relevance = s.get("german_relevance", 5)
            if relevance == 0:
                relevance = 5
                
            overall = (
                s["academic_match"] * 0.3
                + s["profile_fit"] * 0.25
                + s["competition"] * 0.2
                + relevance * 0.25
            )
            s["overall"] = round(overall, 1)
            scored.append(s)

        # 2. Process database scholarships dynamically
        if scholarships:
            for s in scholarships:
                name = s.get("name")
                if not name:
                    continue
                name_lower = name.lower()
                if name_lower in seen_names:
                    # Let the static curated entry take precedence
                    continue
                seen_names.add(name_lower)

                # Degree Level Match
                degree = str(s.get("degree") or "").lower()
                is_msc = any(d in degree for d in ["msc", "ms ", "master", "mphil", "ms/phd", "msc/phd"])
                is_phd = any(d in degree for d in ["phd", "doctoral", "ph.d"])
                is_bachelor = any(d in degree for d in ["ba", "bs", "bsc"])
                if is_msc or (is_msc and is_phd):
                    degree_bonus = 1.0
                elif is_phd and not is_msc:
                    degree_bonus = 0.5
                elif is_bachelor:
                    degree_bonus = 0.0
                else:
                    degree_bonus = 0.8

                # Academic Match
                academic_match = 6
                fields_str = str(s.get("fields") or s.get("target_fields") or "").lower()
                matches_field = any(f.lower() in fields_str for f in self.profile.get("target_fields", []))
                if matches_field:
                    academic_match = 8
                    if "statistics" in fields_str or "machine learning" in fields_str or "data science" in fields_str:
                        academic_match = 9

                # Profile Fit (GPA check)
                profile_fit = 7
                gpa_req = str(s.get("academics") or s.get("eligibility_academics") or "").lower()
                gpa_matches = re.findall(r"(?:gpa|cgpa)\s*(?::|of)?\s*([23]\.\d+)", gpa_req)
                if gpa_matches:
                    try:
                        required_gpa = float(gpa_matches[0])
                        user_gpa = float(self.profile.get("gpa", "0.0"))
                        if user_gpa >= required_gpa:
                            profile_fit = 9
                        else:
                            profile_fit = 4
                    except ValueError:
                        pass

                # Competition Level
                coverage = str(s.get("coverage_type") or s.get("coverage") or "").lower()
                if "full" in coverage or "ride" in coverage:
                    competition = 5 # full ride is high competition
                else:
                    competition = 7 # partial is lower competition

                # Country relevance
                country = s.get("country", "Germany")
                country_relevance = 5 # default
                if country in self.profile.get("target_countries", []):
                    country_relevance = 9

                overall = (
                    academic_match * 0.3
                    + profile_fit * 0.25
                    + competition * 0.2
                    + country_relevance * 0.25
                ) * degree_bonus

                # Determine recommendation text
                if overall >= 8.0:
                    rec = f"EXCELLENT TARGET: Top match in {country}. Full coverage fit."
                elif overall >= 7.0:
                    rec = f"GOOD FIT: Competitive match for {country}. Apply."
                else:
                    rec = f"CONSIDER: Moderate fit. Keep as backup."

                # Notes summary
                notes = f"Target fields match your Statistics background. Country is {country}."
                if "full" in coverage or "ride" in coverage:
                    notes += " Full-ride funding option."
                else:
                    notes += " Partial or tuition waiver."
                notes += f" Degree: {degree}."
                if not is_msc and is_phd:
                    notes += " PhD-only — lower priority for MSc seekers."

                scored.append({
                    "name": name,
                    "academic_match": academic_match,
                    "profile_fit": profile_fit,
                    "competition": competition,
                    "german_relevance": country_relevance, # keep key for compatibility
                    "overall": round(overall, 1),
                    "recommendation": rec,
                    "notes": notes
                })

        scored.sort(key=lambda x: x["overall"], reverse=True)

        for i, s in enumerate(scored[:10]):
            filled = int(s["overall"])
            bar = "#" * filled + "-" * (10 - filled)
            print(f"  {i+1}. {s['name']}")
            print(f"     Score: {s['overall']}/10  [{bar}]")
            print(f"     {s['recommendation']}")
            print(f"     {s['notes']}")
            print()

        return scored

    def get_recommendations(self):
        scored = self.calculate()
        print("  === TOP RECOMMENDATIONS (Score >= 7) ===")
        top = [s for s in scored if s["overall"] >= 7]
        for s in top:
            print(f"    - [{s['overall']}/10] {s['name']}")
        return top
