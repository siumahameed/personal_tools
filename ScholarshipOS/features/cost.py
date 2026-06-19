HEADERS = [
    "Country",
    "City",
    "University",
    "Tuition (per semester)",
    "Semester Fee (local)",
    "Rent (per month)",
    "Health Insurance (per month)",
    "Living Costs (per month)",
    "Total Yearly",
    "Notes",
]

CITY_COSTS = [
    # Germany
    {
        "country": "Germany",
        "city": "Munich",
        "university": "TUM, LMU",
        "tuition": 0,
        "tuition_currency": "EUR",
        "semester_fee": 152,
        "rent": 600,
        "insurance": 120,
        "living": 1200,
        "blocked_account": 11208,
        "total_yearly_note": "~14,704 EUR (FREE tuition)",
        "notes": "Most expensive city but best universities. Part-time jobs available.",
    },
    {
        "country": "Germany",
        "city": "Berlin",
        "university": "TU Berlin, FU Berlin, HU Berlin",
        "tuition": 0,
        "tuition_currency": "EUR",
        "semester_fee": 330,
        "rent": 500,
        "insurance": 110,
        "living": 1000,
        "blocked_account": 11208,
        "total_yearly_note": "~12,660 EUR (FREE tuition)",
        "notes": "Startup hub. More affordable than Munich. Many English programs.",
    },
    {
        "country": "Germany",
        "city": "Aachen",
        "university": "RWTH Aachen",
        "tuition": 0,
        "tuition_currency": "EUR",
        "semester_fee": 300,
        "rent": 400,
        "insurance": 110,
        "living": 900,
        "blocked_account": 11208,
        "total_yearly_note": "~11,400 EUR (FREE tuition)",
        "notes": "Smaller city, lower cost. Excellent engineering university.",
    },
    {
        "country": "Germany",
        "city": "Bonn",
        "university": "University of Bonn",
        "tuition": 0,
        "tuition_currency": "EUR",
        "semester_fee": 330,
        "rent": 380,
        "insurance": 110,
        "living": 850,
        "blocked_account": 11208,
        "total_yearly_note": "~10,860 EUR (FREE tuition)",
        "notes": "Affordable. Hausdorff Center for Math is world-class.",
    },
    {
        "country": "Germany",
        "city": "Karlsruhe",
        "university": "KIT",
        "tuition": 1500,
        "tuition_currency": "EUR",
        "semester_fee": 190,
        "rent": 420,
        "insurance": 110,
        "living": 900,
        "blocked_account": 11208,
        "total_yearly_note": "~13,800 EUR (3k tuition)",
        "notes": "Non-EU tuition (Baden-Wuerttemberg). Still affordable vs other countries.",
    },
    {
        "country": "Germany",
        "city": "Darmstadt",
        "university": "TU Darmstadt",
        "tuition": 0,
        "tuition_currency": "EUR",
        "semester_fee": 400,
        "rent": 400,
        "insurance": 110,
        "living": 900,
        "blocked_account": 11208,
        "total_yearly_note": "~11,600 EUR (FREE tuition)",
        "notes": "Zero tuition. Good data science program. Moderate living costs.",
    },
    {
        "country": "Germany",
        "city": "Freiburg",
        "university": "University of Freiburg",
        "tuition": 1500,
        "tuition_currency": "EUR",
        "semester_fee": 170,
        "rent": 450,
        "insurance": 110,
        "living": 900,
        "blocked_account": 11208,
        "total_yearly_note": "~13,840 EUR (3k tuition)",
        "notes": "Non-EU tuition (Baden-Wuerttemberg). Beautiful city. Strong AI research.",
    },
    {
        "country": "Germany",
        "city": "Dresden",
        "university": "TU Dresden",
        "tuition": 0,
        "tuition_currency": "EUR",
        "semester_fee": 300,
        "rent": 350,
        "insurance": 100,
        "living": 800,
        "blocked_account": 11208,
        "total_yearly_note": "~10,200 EUR (FREE tuition)",
        "notes": "Most affordable option. Zero tuition. Good research center.",
    },
    {
        "country": "Germany",
        "city": "Goettingen",
        "university": "University of Goettingen",
        "tuition": 0,
        "tuition_currency": "EUR",
        "semester_fee": 400,
        "rent": 370,
        "insurance": 100,
        "living": 800,
        "blocked_account": 11208,
        "total_yearly_note": "~10,400 EUR (FREE tuition)",
        "notes": "Excellent Statistics program. Zero tuition. Very affordable living.",
    },
    {
        "country": "Germany",
        "city": "Hamburg",
        "university": "University of Hamburg",
        "tuition": 0,
        "tuition_currency": "EUR",
        "semester_fee": 335,
        "rent": 500,
        "insurance": 110,
        "living": 950,
        "blocked_account": 11208,
        "total_yearly_note": "~12,070 EUR (FREE tuition)",
        "notes": "Major port city. Zero tuition. Growing AI/Data Science programs.",
    },
    # USA
    {
        "country": "USA",
        "city": "Stanford / Palo Alto",
        "university": "Stanford University",
        "tuition": 28000,
        "tuition_currency": "USD",
        "semester_fee": 500,
        "rent": 1500,
        "insurance": 250,
        "living": 2500,
        "blocked_account": 0,
        "total_yearly_note": "~$83,000 (high, but TA/RA can cover)",
        "notes": "Most expensive; Knight-Hennessy covers FULL cost if awarded",
    },
    {
        "country": "USA",
        "city": "Cambridge / Boston",
        "university": "MIT / Harvard",
        "tuition": 28000,
        "tuition_currency": "USD",
        "semester_fee": 500,
        "rent": 1400,
        "insurance": 250,
        "living": 2400,
        "blocked_account": 0,
        "total_yearly_note": "~$80,000 (without funding)",
        "notes": "Ivy+/MIT; TA/RA can cover tuition + stipend; need strong profile",
    },
    {
        "country": "USA",
        "city": "Pittsburgh",
        "university": "Carnegie Mellon University",
        "tuition": 26000,
        "tuition_currency": "USD",
        "semester_fee": 400,
        "rent": 900,
        "insurance": 200,
        "living": 1700,
        "blocked_account": 0,
        "total_yearly_note": "~$66,000 (some TA/RA available)",
        "notes": "Best ML program globally; TA/RA positions competitive",
    },
    {
        "country": "USA",
        "city": "Berkeley",
        "university": "UC Berkeley",
        "tuition": 12000,
        "tuition_currency": "USD",
        "semester_fee": 800,
        "rent": 1400,
        "insurance": 200,
        "living": 2300,
        "blocked_account": 0,
        "total_yearly_note": "~$54,000 (non-resident tuition)",
        "notes": "Public Ivy; lower tuition than private; good TA/RA opportunities",
    },
    {
        "country": "USA",
        "city": "Atlanta",
        "university": "Georgia Tech",
        "tuition": 8000,
        "tuition_currency": "USD",
        "semester_fee": 600,
        "rent": 900,
        "insurance": 150,
        "living": 1600,
        "blocked_account": 0,
        "total_yearly_note": "~$38,000 (most affordable US option)",
        "notes": "Best value in US; strong data science; good TA/RA availability",
    },
    {
        "country": "USA",
        "city": "Seattle",
        "university": "University of Washington",
        "tuition": 12000,
        "tuition_currency": "USD",
        "semester_fee": 700,
        "rent": 1300,
        "insurance": 200,
        "living": 2200,
        "blocked_account": 0,
        "total_yearly_note": "~$52,000 (non-resident)",
        "notes": "Strong ML research; good TA/RA; Amazon/Microsoft nearby",
    },
    {
        "country": "USA",
        "city": "Ann Arbor",
        "university": "University of Michigan",
        "tuition": 13000,
        "tuition_currency": "USD",
        "semester_fee": 600,
        "rent": 1000,
        "insurance": 180,
        "living": 1800,
        "blocked_account": 0,
        "total_yearly_note": "~$48,000 (non-resident)",
        "notes": "Strong data science; large international community",
    },
]


class CostComparison:
    def __init__(self, profile, sheets_client=None, data_dir=None):
        self.profile = profile
        self.sheets = sheets_client

    def show(self):
        print("\n=== COST COMPARISON: Germany + USA ===")
        print(f"  Based on: Single student budget (non-EU/non-US)")
        print(f"  Note: Germany: ZERO tuition (except BW). USA: high but TA/RA can fund")
        print()

        print("  === GERMANY (EUR/year) ===")
        german = [c for c in CITY_COSTS if c["country"] == "Germany"]
        print(f"  {'City':<15} {'Tuition':<10} {'Rent':<10} {'Living/mo':<12} {'Total/yr':<20}")
        print(f"  {'-'*60}")
        for c in sorted(german, key=lambda x: x["living"]):
            tuition_str = "FREE" if c["tuition"] == 0 else f"{c['tuition']} EUR/sem"
            total = c["tuition"] * 2 + c["semester_fee"] * 2 + c["living"] * 12
            print(f"  {c['city']:<15} {tuition_str:<10} {c['rent']:<10} {c['living']:<12} {total:<12} EUR")
        print()
        print(f"  * DAAD (11,208 EUR/yr): Covers living at most German cities!")
        print(f"  * Erasmus Mundus (~16,800 EUR/yr): Fully covered + savings possible!")
        print()

        print("  === USA (USD/year) ===")
        us = [c for c in CITY_COSTS if c["country"] == "USA"]
        print(f"  {'City':<20} {'Tuition/sem':<14} {'Rent':<10} {'Living/mo':<12} {'Total/yr':<20}")
        print(f"  {'-'*70}")
        for c in sorted(us, key=lambda x: x["living"]):
            total = c["tuition"] * 2 + c["semester_fee"] * 2 + c["living"] * 12
            print(f"  {c['city']:<20} ${c['tuition']:<10} ${c['rent']:<7} ${c['living']:<9} ${total:<9} USD")
        print()
        print(f"  * Fulbright covers FULL tuition + living for US programs!")
        print(f"  * Knight-Hennessy covers FULL Stanford costs (~$90k+/year)!")
        print(f"  * TA/RA positions at US unis often cover tuition + ~$30k stipend")
        print()

        print("  === VERDICT ===")
        print(f"  Germany is MUCH cheaper (FREE tuition). Apply DAAD + Erasmus Mundus = top priority.")
        print(f"  USA needs Fulbright or Knight-Hennessy for full funding. Apply as backup.")
        print()

        return CITY_COSTS
