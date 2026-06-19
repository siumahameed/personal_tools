#!/usr/bin/env python3
"""Extract all hardcoded data from Python files to JSON files."""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def save(name, data):
    path = os.path.join(DATA_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(data)} items to {path}")

def main():
    from agents.scholarship import CORE_SCHOLARSHIPS
    from agents.university import ALL_UNIVERSITIES
    from agents.professor import ALL_PROFESSORS

    save("core_scholarships", CORE_SCHOLARSHIPS)
    save("core_universities", ALL_UNIVERSITIES)
    save("core_professors", ALL_PROFESSORS)

if __name__ == "__main__":
    main()
