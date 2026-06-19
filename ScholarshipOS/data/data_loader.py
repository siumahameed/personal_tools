"""Load data from JSON files with fallback to Python imports."""
import os
import json
import sys

DATA_DIR = os.path.dirname(__file__)

def _load_json(filename):
    path = os.path.join(DATA_DIR, f"{filename}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Error loading {path}: {e}")
    return None

def load_core_scholarships():
    data = _load_json("core_scholarships")
    if data is not None:
        return data
    from agents.scholarship import CORE_SCHOLARSHIPS
    return CORE_SCHOLARSHIPS

def load_core_universities():
    data = _load_json("core_universities")
    if data is not None:
        return data
    from agents.university import ALL_UNIVERSITIES
    return ALL_UNIVERSITIES

def load_core_professors():
    data = _load_json("core_professors")
    if data is not None:
        return data
    from agents.professor import ALL_PROFESSORS
    return ALL_PROFESSORS
