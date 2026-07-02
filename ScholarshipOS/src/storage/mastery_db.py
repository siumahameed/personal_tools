import sqlite3
import os
import json
import threading
from datetime import datetime


class MasteryDB:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'mastery.db')
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.init_tables()

    def init_tables(self):
        with self.lock:
            c = self.conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS scholarships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    country TEXT,
                    provider TEXT,
                    coverage_type TEXT,
                    coverage_details TEXT,
                    amount TEXT,
                    currency TEXT,
                    degree_level TEXT,
                    target_fields TEXT,
                    eligibility_nationality TEXT,
                    eligibility_academics TEXT,
                    eligibility_experience TEXT,
                    required_documents TEXT,
                    application_fee TEXT,
                    application_language TEXT,
                    english_test_required TEXT,
                    gre_required TEXT,
                    deadline_start TEXT,
                    deadline_end TEXT,
                    duration TEXT,
                    interview_required TEXT,
                    competitiveness TEXT,
                    application_portal TEXT,
                    official_url TEXT,
                    notification_date TEXT,
                    match_score INTEGER DEFAULT 50,
                    strategy_notes TEXT,
                    last_updated TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS scholarship_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scholarship_id INTEGER NOT NULL,
                    step_number INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    timeline TEXT,
                    tips TEXT,
                    is_critical INTEGER DEFAULT 0,
                    FOREIGN KEY (scholarship_id) REFERENCES scholarships(id)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS successful_applicants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scholarship_id INTEGER NOT NULL,
                    name TEXT,
                    background TEXT,
                    country TEXT,
                    field_of_study TEXT,
                    work_experience TEXT,
                    publications TEXT,
                    test_scores TEXT,
                    application_strategy TEXT,
                    what_worked TEXT,
                    advice TEXT,
                    source_url TEXT,
                    source_type TEXT DEFAULT 'seed',
                    FOREIGN KEY (scholarship_id) REFERENCES scholarships(id)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS tips_and_tricks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scholarship_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    tip TEXT NOT NULL,
                    priority TEXT DEFAULT 'medium',
                    FOREIGN KEY (scholarship_id) REFERENCES scholarships(id)
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS scholarship_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scholarship_slug TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    snippet TEXT,
                    news_type TEXT DEFAULT 'news',
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS checklist_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scholarship_id INTEGER NOT NULL,
                    step_id INTEGER NOT NULL,
                    completed INTEGER DEFAULT 0,
                    completed_at TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (scholarship_id) REFERENCES scholarships(id),
                    FOREIGN KEY (step_id) REFERENCES scholarship_steps(id),
                    UNIQUE(scholarship_id, step_id)
                )
            """)
            self.conn.commit()

    def get_all_scholarships(self):
        with self.lock:
            c = self.conn.cursor()
            c.execute("""
                SELECT s.*,
                    (SELECT COUNT(*) FROM scholarship_steps WHERE scholarship_id = s.id) as total_steps,
                    (SELECT COUNT(*) FROM checklist_progress cp JOIN scholarship_steps ss ON cp.step_id = ss.id WHERE ss.scholarship_id = s.id AND cp.completed = 1) as completed_steps
                FROM scholarships s ORDER BY s.match_score DESC
            """)
            rows = c.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["total_steps"] = d.get("total_steps", 0) or 0
                d["completed_steps"] = d.get("completed_steps", 0) or 0
                result.append(d)
            return result

    def get_scholarship(self, slug):
        with self.lock:
            c = self.conn.cursor()
            c.execute("SELECT * FROM scholarships WHERE slug = ?", (slug,))
            row = c.fetchone()
            if not row:
                return None
            scholarship = dict(row)
            c.execute("SELECT * FROM scholarship_steps WHERE scholarship_id = ? ORDER BY step_number", (scholarship["id"],))
            scholarship["steps"] = [dict(r) for r in c.fetchall()]
            c.execute("SELECT * FROM successful_applicants WHERE scholarship_id = ?", (scholarship["id"],))
            scholarship["applicants"] = [dict(r) for r in c.fetchall()]
            c.execute("SELECT * FROM tips_and_tricks WHERE scholarship_id = ? ORDER BY priority", (scholarship["id"],))
            scholarship["tips"] = [dict(r) for r in c.fetchall()]
            return scholarship

    def get_checklist(self, scholarship_id):
        with self.lock:
            c = self.conn.cursor()
            c.execute("""
                SELECT ss.*, COALESCE(cp.completed, 0) as completed, cp.completed_at, cp.notes
                FROM scholarship_steps ss
                LEFT JOIN checklist_progress cp ON cp.step_id = ss.id AND cp.scholarship_id = ss.scholarship_id
                WHERE ss.scholarship_id = ?
                ORDER BY ss.step_number
            """, (scholarship_id,))
            return [dict(r) for r in c.fetchall()]

    def update_checklist_item(self, scholarship_id, step_id, completed, notes=None):
        with self.lock:
            c = self.conn.cursor()
            existing = c.execute(
                "SELECT id FROM checklist_progress WHERE scholarship_id = ? AND step_id = ?",
                (scholarship_id, step_id)
            ).fetchone()
            if existing:
                if completed:
                    c.execute("""
                        UPDATE checklist_progress SET completed = ?, completed_at = ?, notes = COALESCE(?, notes)
                        WHERE id = ?
                    """, (1 if completed else 0, datetime.now().isoformat() if completed else None, notes, existing["id"]))
                else:
                    c.execute("UPDATE checklist_progress SET completed = 0, completed_at = NULL WHERE id = ?", (existing["id"],))
            else:
                c.execute("""
                    INSERT INTO checklist_progress (scholarship_id, step_id, completed, completed_at, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (scholarship_id, step_id, 1 if completed else 0, datetime.now().isoformat() if completed else None, notes))
            self.conn.commit()
            return True

    def upsert_scholarship(self, data):
        with self.lock:
            c = self.conn.cursor()
            existing = c.execute("SELECT id FROM scholarships WHERE slug = ?", (data["slug"],)).fetchone()
            data["last_updated"] = datetime.now().isoformat()
            columns = ", ".join(data.keys())
            placeholders = ", ".join("?" for _ in data)
            updates = ", ".join(f"{k} = excluded.{k}" for k in data.keys() if k != "slug")
            sql = f"""
                INSERT INTO scholarships ({columns}) VALUES ({placeholders})
                ON CONFLICT(slug) DO UPDATE SET {updates}
            """
            c.execute(sql, list(data.values()))
            self.conn.commit()
            return c.lastrowid or existing["id"]

    def insert_steps(self, scholarship_id, steps):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM scholarship_steps WHERE scholarship_id = ?", (scholarship_id,))
            for step in steps:
                c.execute("""
                    INSERT INTO scholarship_steps (scholarship_id, step_number, phase, title, description, timeline, tips, is_critical)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    scholarship_id, step["step_number"], step["phase"], step["title"],
                    step.get("description", ""), step.get("timeline", ""),
                    step.get("tips", ""), step.get("is_critical", 0)
                ))
            self.conn.commit()

    def insert_applicant(self, scholarship_id, applicant):
        with self.lock:
            c = self.conn.cursor()
            c.execute("""
                INSERT INTO successful_applicants (scholarship_id, name, background, country, field_of_study,
                    work_experience, publications, test_scores, application_strategy, what_worked, advice, source_url, source_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scholarship_id, applicant.get("name", ""), applicant.get("background", ""),
                applicant.get("country", ""), applicant.get("field_of_study", ""),
                applicant.get("work_experience", ""), applicant.get("publications", ""),
                applicant.get("test_scores", ""), applicant.get("application_strategy", ""),
                applicant.get("what_worked", ""), applicant.get("advice", ""),
                applicant.get("source_url", ""), applicant.get("source_type", "seed")
            ))
            self.conn.commit()

    def insert_tip(self, scholarship_id, tip):
        with self.lock:
            c = self.conn.cursor()
            c.execute("""
                INSERT INTO tips_and_tricks (scholarship_id, category, tip, priority)
                VALUES (?, ?, ?, ?)
            """, (scholarship_id, tip["category"], tip["tip"], tip.get("priority", "medium")))
            self.conn.commit()

    def clear_applicants(self, scholarship_id):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM successful_applicants WHERE scholarship_id = ?", (scholarship_id,))
            self.conn.commit()

    def clear_tips(self, scholarship_id):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM tips_and_tricks WHERE scholarship_id = ?", (scholarship_id,))
            self.conn.commit()

    def get_scholarship_by_name(self, name):
        with self.lock:
            c = self.conn.cursor()
            c.execute("SELECT * FROM scholarships WHERE name LIKE ?", (f"%{name}%",))
            row = c.fetchone()
            return dict(row) if row else None

    def get_scholarship_id_by_name(self, name):
        with self.lock:
            c = self.conn.cursor()
            c.execute("SELECT id FROM scholarships WHERE name LIKE ?", (f"%{name}%",))
            row = c.fetchone()
            return row["id"] if row else None

    def update_applicant(self, applicant_id, data):
        with self.lock:
            c = self.conn.cursor()
            fields = ["test_scores", "work_experience", "publications", "application_strategy", "what_worked", "advice"]
            updates = []
            values = []
            for f in fields:
                if f in data and data[f]:
                    updates.append(f"{f} = ?")
                    values.append(data[f])
            if updates:
                sql = f"UPDATE successful_applicants SET {', '.join(updates)} WHERE id = ?"
                values.append(applicant_id)
                c.execute(sql, values)
                self.conn.commit()

    def insert_news(self, slug, title, url, news_type="news", snippet=""):
        with self.lock:
            c = self.conn.cursor()
            c.execute("""
                INSERT INTO scholarship_news (scholarship_slug, title, url, snippet, news_type)
                VALUES (?, ?, ?, ?, ?)
            """, (slug, title[:300], url, snippet[:500], news_type))
            self.conn.commit()

    def get_news(self, slug, limit=10):
        with self.lock:
            c = self.conn.cursor()
            c.execute("""
                SELECT * FROM scholarship_news
                WHERE scholarship_slug = ?
                ORDER BY date_added DESC
                LIMIT ?
            """, (slug, limit))
            return [dict(r) for r in c.fetchall()]

    def clear_news(self, slug):
        with self.lock:
            c = self.conn.cursor()
            c.execute("DELETE FROM scholarship_news WHERE scholarship_slug = ?", (slug,))
            self.conn.commit()

    def update_scholarship_field(self, slug, field, value):
        with self.lock:
            c = self.conn.cursor()
            c.execute(f"UPDATE scholarships SET {field} = ?, last_updated = ? WHERE slug = ?",
                      (value, datetime.now().isoformat(), slug))
            self.conn.commit()

    def close(self):
        with self.lock:
            self.conn.close()
