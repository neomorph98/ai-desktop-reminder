"""本地存储：SQLite。v1 不接真实日历，先把提醒存在本机。"""
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminders.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                type        TEXT,
                title       TEXT,
                start_time  TEXT,
                time_text   TEXT,
                location    TEXT,
                source_text TEXT,
                created_at  TEXT,
                done        INTEGER DEFAULT 0
            )"""
        )
        # 迁移：老版本的库可能没有 time_text 列
        cols = [r[1] for r in c.execute("PRAGMA table_info(reminders)").fetchall()]
        if "time_text" not in cols:
            c.execute("ALTER TABLE reminders ADD COLUMN time_text TEXT")


def add_reminder(type_, title, start_time, time_text, location, source_text):
    with _conn() as c:
        c.execute(
            "INSERT INTO reminders (type,title,start_time,time_text,location,source_text,created_at,done)"
            " VALUES (?,?,?,?,?,?,?,0)",
            (type_, title, start_time, time_text, location, source_text,
             datetime.now().isoformat(timespec="seconds")),
        )


def upcoming(limit=10):
    """未完成的提醒，有时间的排前面、按时间升序。"""
    with _conn() as c:
        cur = c.execute(
            "SELECT id,type,title,start_time,time_text,location,done FROM reminders"
            " WHERE done=0 ORDER BY (start_time IS NULL), start_time LIMIT ?",
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def mark_done(rid):
    with _conn() as c:
        c.execute("UPDATE reminders SET done=1 WHERE id=?", (rid,))
