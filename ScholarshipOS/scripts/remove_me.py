"""Remove Middle Eastern countries from scholarships and professors."""
import json, os, sys

_script_root_rm = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, _script_root_rm)
sys.path.insert(0, os.path.join(_script_root_rm, 'src'))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ME = {'UAE','Saudi Arabia','Qatar','Israel','Oman','Egypt','Turkey'}

for fname in ("core_scholarships.json", "core_professors.json"):
    path = os.path.join(DATA_DIR, fname)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    removed = [d for d in data if d.get("country") in ME]
    kept = [d for d in data if d.get("country") not in ME]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(kept, f, indent=2, ensure_ascii=False)
    print(f"[{fname}] Removed {len(removed)} entries")
    for r in removed:
        print(f"  - {r['name']} ({r['country']})")
    print(f"  Total remaining: {len(kept)}")
