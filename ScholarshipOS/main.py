#!/usr/bin/env python3
"""
ScholarAI Agent
===============
Your autonomous scholarship & admission tracking system.

Usage:
  python main.py          -> Launch CLI menu
  python main.py --web    -> Launch web dashboard directly
  python main.py --scan   -> Run full scan and save results

Target: Germany | Full-ride scholarships | ML/AI/Data Science/Statistics
"""

import sys
import os
import argparse

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
try:
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

ROOT_DIR = os.path.dirname(__file__)

def get_sheets_client():
    creds_path = os.path.join(ROOT_DIR, "credentials.json")
    if os.path.exists(creds_path):
        from config import SHEETS_CONFIG
        from src.storage.sheets import GoogleSheetsClient
        return GoogleSheetsClient(creds_path, SHEETS_CONFIG["spreadsheet_id"])
    return None


def main():
    parser = argparse.ArgumentParser(description="ScholarAI Agent")
    parser.add_argument("--web", action="store_true", help="Launch web dashboard")
    parser.add_argument("--scan", action="store_true", help="Run full research scan")
    args = parser.parse_args()

    sheets = get_sheets_client()

    if args.web:
        print("Starting Web Dashboard...")
        os.chdir(ROOT_DIR)
        import uvicorn
        import atexit
        lock_file = os.path.join(ROOT_DIR, ".dashboard.lock")
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except Exception:
                pass
        try:
            with open(lock_file, "w") as f:
                f.write(str(os.getpid()))
            import threading, webbrowser
            def open_browser():
                import time
                time.sleep(1.5)
                webbrowser.open("http://localhost:5000")
            threading.Thread(target=open_browser, daemon=True).start()
            def cleanup_lock():
                if os.path.exists(lock_file):
                    os.remove(lock_file)
            atexit.register(cleanup_lock)
        except Exception:
            pass
        reload_mode = os.environ.get("SCHOLARAI_ENV", "development") == "development"
        uvicorn.run("src.dashboard.app:app", host="0.0.0.0", port=5000, reload=reload_mode)
    elif args.scan:
        from src.orchestrator import Orchestrator
        orch = Orchestrator(sheets, interactive=False)
        orch.show_welcome()
        orch.run_all()
    else:
        from src.orchestrator import Orchestrator
        orch = Orchestrator(sheets)
        orch.show_welcome()
        orch.menu()


if __name__ == "__main__":
    main()
