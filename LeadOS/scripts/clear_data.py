"""Clear all prospect / job / draft / research data from the database.

Keeps user_profile so the user doesn't have to re-enter their details.
Safe to run while the server is running (SQLite handles concurrent access).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "app" / "data" / "ggh.db"
TABLES_TO_CLEAR = ["prospects", "outreach_drafts", "scrape_sessions", "research_leads", "jobs"]
TABLES_TO_KEEP = ["user_profile", "alembic_version"]


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    print("=" * 60)
    print("BEFORE")
    print("=" * 60)
    all_tables = TABLES_TO_CLEAR + TABLES_TO_KEEP
    counts_before = {}
    for tbl in all_tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            counts_before[tbl] = cur.fetchone()[0]
            print(f"  {tbl:25s} {counts_before[tbl]:>5d} rows")
        except sqlite3.OperationalError as e:
            counts_before[tbl] = None
            print(f"  {tbl:25s}     (table does not exist)")

    print()
    print("=" * 60)
    print("CLEARING")
    print("=" * 60)
    for tbl in TABLES_TO_CLEAR:
        try:
            cur.execute(f"DELETE FROM {tbl}")
            deleted = cur.rowcount
            print(f"  [OK] Cleared {tbl:25s} ({deleted} rows deleted)")
        except sqlite3.OperationalError as e:
            print(f"  [SKIP] {tbl:25s} ({e})")

    try:
        cur.execute("DELETE FROM sqlite_sequence")
        print(f"  [OK] Reset autoincrement counters")
    except sqlite3.OperationalError:
        print(f"  [SKIP] sqlite_sequence (not present in this DB)")

    con.commit()

    print()
    print("=" * 60)
    print("AFTER")
    print("=" * 60)
    for tbl in all_tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            n = cur.fetchone()[0]
            print(f"  {tbl:25s} {n:>5d} rows")
        except sqlite3.OperationalError:
            print(f"  {tbl:25s}     (table does not exist)")

    con.close()
    print()
    print("[DONE] Database cleared. Server is still running.")
    print("  Refresh the dashboard to see 0s, then run the pipelines.")


if __name__ == "__main__":
    main()
