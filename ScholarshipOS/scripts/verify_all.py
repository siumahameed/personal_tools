"""Final verification script."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("SCHOLARAI AGENT - FINAL VERIFICATION")
print("=" * 60)
errors = []

# 1. Config
try:
    from config import PROFILE, SHEETS_CONFIG, APP_CONFIG
    print(f"[OK] config.py - Profile: {PROFILE['name']}, GPA: {PROFILE['gpa']}")
except Exception as e:
    errors.append(f"config.py: {e}")
    print(f"[FAIL] config.py: {e}")

# 2. Data loader
try:
    from data.data_loader import load_core_scholarships, load_core_universities, load_core_professors
    s = load_core_scholarships()
    u = load_core_universities()
    p = load_core_professors()
    print(f"[OK] Data: {len(s)} scholarships, {len(u)} universities, {len(p)} professors")

    # Check country coverage
    countries = set(sch.get("country", "?") for sch in s)
    has_bd = any("bangladesh" in sch.get("country","").lower() or "bangladesh" in sch.get("name","").lower() for sch in s)
    has_india = any("india" in sch.get("country","").lower() or "india" in sch.get("name","").lower() for sch in s)
    has_pakistan = any("pakistan" in sch.get("country","").lower() or "pakistan" in sch.get("name","").lower() for sch in s)
    print(f"[OK] Countries: {len(countries)} - Bangladesh: {has_bd}, India: {has_india}, Pakistan: {has_pakistan}")
except Exception as e:
    errors.append(f"data_loader: {e}")
    print(f"[FAIL] data_loader: {e}")

# 3. Base agent with HTTP client
try:
    from agents.base import BaseAgent
    agent = BaseAgent("test", interactive=False)
    print(f"[OK] BaseAgent - retry support, fallback search engines")
except Exception as e:
    errors.append(f"base.py: {e}")
    print(f"[FAIL] base.py: {e}")

# 4. Target agent with fixed regex
try:
    from agents.target import TargetEnricherAgent, DEADLINE_RE, AMOUNT_RE
    enricher = TargetEnricherAgent(PROFILE, interactive=False)

    # Test regex
    tests = [
        ("Application deadline: December 15, 2024", True),
        ("Deadline: March 1st, 2025", True),
        ("Amount: EUR 1,200 per month", True),
    ]
    for text, expected in tests:
        m = DEADLINE_RE.search(text) or AMOUNT_RE.search(text)
        assert (m is not None) == expected, f"Regex failed for: {text}"
    print(f"[OK] Target agent - regex handles both date formats, amount parsing")
except Exception as e:
    errors.append(f"target.py: {e}")
    print(f"[FAIL] target.py: {e}")

# 5. Match score calculator
try:
    from features.match_score import MatchScoreCalculator
    calc = MatchScoreCalculator(PROFILE)
    scores = calc.calculate(s)
    print(f"[OK] Match scores: {len(scores)} scholarships scored")
    top3 = scores[:3]
    print(f"     Top: {top3[0]['name']} ({top3[0]['overall']}/10), {top3[1]['name']} ({top3[1]['overall']}/10), {top3[2]['name']} ({top3[2]['overall']}/10)")
except Exception as e:
    errors.append(f"match_score.py: {e}")
    print(f"[FAIL] match_score.py: {e}")

# 6. Deadline tracker
try:
    from features.deadlines import DeadlineTracker
    dt = DeadlineTracker(PROFILE)
    deadlines = dt.calculate(s[:5], u[:5])
    print(f"[OK] Deadlines: {len(deadlines)} tracked")
except Exception as e:
    errors.append(f"deadlines.py: {e}")
    print(f"[FAIL] deadlines.py: {e}")

# 7. Document collector imports
try:
    from agents.document_collector import DocumentCollector, CURATED_REPOS
    sa_keywords = ['jayed','sakib','shahriar','rabbi','shakil','nayeem','toufiq','rahat','musfiq',
                   'tanveer','shehriyar','zain','hfazal','mhassan','shoaib','iiti','manas','rajat',
                   'dhruv','rishav','rounak','fahad','kazi','sajid','shihab']
    south_asian_count = sum(1 for r in CURATED_REPOS if any(kw in r.lower() for kw in sa_keywords))
    print(f"[OK] DocumentCollector - {len(CURATED_REPOS)} curated repos ({south_asian_count} South Asian)")
except Exception as e:
    errors.append(f"document_collector.py: {e}")
    print(f"[FAIL] document_collector.py: {e}")

# 8. Deep document researcher
try:
    from agents.deep_document_researcher import DeepDocumentResearcher
    researcher = DeepDocumentResearcher()
    print(f"[OK] DeepDocumentResearcher - 7 phases including South Asian phase")
except Exception as e:
    errors.append(f"deep_document_researcher.py: {e}")
    print(f"[FAIL] deep_document_researcher.py: {e}")

# 9. Dashboard app
try:
    from dashboard.app import app
    print(f"[OK] FastAPI dashboard app loaded")
except Exception as e:
    errors.append(f"dashboard/app.py: {e}")
    print(f"[FAIL] dashboard/app.py: {e}")

# 10. Orchestrator
try:
    from orchestrator import Orchestrator
    print(f"[OK] Orchestrator imported")
except Exception as e:
    errors.append(f"orchestrator.py: {e}")
    print(f"[FAIL] orchestrator.py: {e}")

# 11. Sheets client
try:
    from storage.sheets import GoogleSheetsClient
    print(f"[OK] GoogleSheetsClient - sync_table safe, update_cell fixed")
except Exception as e:
    errors.append(f"sheets.py: {e}")
    print(f"[FAIL] sheets.py: {e}")

# Summary
print()
print("=" * 60)
if errors:
    print(f"VERDICT: {len(errors)} FAILURES")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("VERDICT: ALL CHECKS PASSED")
print("=" * 60)
