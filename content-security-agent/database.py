import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "content_security.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS content_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            user_group TEXT DEFAULT 'general',
            source TEXT DEFAULT 'other',
            risk_level TEXT NOT NULL,
            risk_score REAL NOT NULL,
            summary TEXT,
            strategy TEXT,
            tags TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            event_time TEXT NOT NULL,
            notify_before_hours INTEGER DEFAULT 6,
            notified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            risk_profile TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER,
            title TEXT,
            content TEXT,
            sent_at TEXT NOT NULL,
            success INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            level TEXT DEFAULT 'info',
            source TEXT DEFAULT 'system',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            condition TEXT NOT NULL,
            action TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            enabled INTEGER DEFAULT 1,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rule_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT,
            action TEXT,
            result TEXT,
            detail TEXT,
            executed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_funnels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stage TEXT NOT NULL,
            user_count INTEGER NOT NULL,
            conversion_rate REAL NOT NULL,
            snapshot_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

    from rules import _init_rules_table
    _init_rules_table()


def save_analysis(
    content: str,
    user_group: str,
    source: str,
    risk_level: str,
    risk_score: float,
    summary: str,
    strategy: str,
    tags: list,
) -> int:
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO content_analyses (content, user_group, source, risk_level, risk_score, summary, strategy, tags, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (content, user_group, source, risk_level, risk_score, summary, strategy, json.dumps(tags), datetime.now().isoformat()),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def save_schedule(title: str, description: Optional[str], event_time: str, notify_before_hours: int) -> int:
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO schedules (title, description, event_time, notify_before_hours, notified, created_at)
           VALUES (?, ?, ?, ?, 0, ?)""",
        (title, description, event_time, notify_before_hours, datetime.now().isoformat()),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_pending_schedules() -> List[dict]:
    now = datetime.now()
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM schedules WHERE notified = 0 ORDER BY event_time ASC"""
    ).fetchall()
    conn.close()

    pending = []
    for row in rows:
        event_time = datetime.fromisoformat(row["event_time"])
        hours_until = (event_time - now).total_seconds() / 3600
        if 0 < hours_until <= row["notify_before_hours"]:
            pending.append(dict(row))
    return pending


def mark_notified(schedule_id: int):
    conn = get_db()
    conn.execute("UPDATE schedules SET notified = 1 WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()


def log_notification(schedule_id: int, title: str, content: str, success: bool = True):
    conn = get_db()
    conn.execute(
        """INSERT INTO notification_log (schedule_id, title, content, sent_at, success)
           VALUES (?, ?, ?, ?, ?)""",
        (schedule_id, title, content, datetime.now().isoformat(), 1 if success else 0),
    )
    conn.commit()
    conn.close()


def get_dashboard_stats() -> dict:
    conn = get_db()

    total = conn.execute("SELECT COUNT(*) as c FROM content_analyses").fetchone()["c"]

    risk_dist = {}
    for row in conn.execute(
        "SELECT risk_level, COUNT(*) as c FROM content_analyses GROUP BY risk_level"
    ).fetchall():
        risk_dist[row["risk_level"]] = row["c"]

    recent_alerts = [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM content_analyses ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
    ]

    upcoming_schedules = [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM schedules WHERE notified = 0 ORDER BY event_time ASC LIMIT 10"
        ).fetchall()
    ]

    user_group_risks = [
        dict(row)
        for row in conn.execute(
            """SELECT user_group, risk_level, COUNT(*) as c, AVG(risk_score) as avg_score
               FROM content_analyses GROUP BY user_group, risk_level
               ORDER BY avg_score DESC"""
        ).fetchall()
    ]

    conn.close()
    return {
        "total_analyses": total,
        "risk_distribution": risk_dist,
        "recent_alerts": recent_alerts,
        "upcoming_schedules": upcoming_schedules,
        "user_group_risks": user_group_risks,
    }


def get_all_schedules() -> List[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM schedules ORDER BY event_time ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_schedule(schedule_id: int) -> bool:
    conn = get_db()
    cursor = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_all_alerts() -> List[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT 50").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_alert(title: str, content: str, level: str = "info", source: str = "system") -> int:
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO alerts (title, content, level, source, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (title, content, level, source, datetime.now().isoformat()),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id