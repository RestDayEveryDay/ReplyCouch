"""SQLite 历史记录存储。"""

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "replycoach.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                scenario TEXT NOT NULL,
                my_persona TEXT NOT NULL,
                their_persona TEXT NOT NULL,
                received TEXT NOT NULL,
                intent TEXT NOT NULL DEFAULT '',
                result TEXT NOT NULL,
                has_image INTEGER NOT NULL DEFAULT 0
            )"""
        )
        try:
            c.execute("ALTER TABLE history ADD COLUMN has_image INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        c.execute(
            """CREATE TABLE IF NOT EXISTS archives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                scenario TEXT NOT NULL,
                my_persona TEXT NOT NULL,
                their_persona TEXT NOT NULL,
                my_detail TEXT NOT NULL DEFAULT '',
                their_detail TEXT NOT NULL DEFAULT '',
                relation_stage TEXT NOT NULL DEFAULT '',
                chat_history TEXT NOT NULL DEFAULT '',
                my_gender TEXT NOT NULL DEFAULT '',
                their_gender TEXT NOT NULL DEFAULT '',
                relation_text TEXT NOT NULL DEFAULT ''
            )"""
        )
        for col in ("my_gender", "their_gender", "relation_text"):  # 旧库迁移：补新列
            try:
                c.execute(f"ALTER TABLE archives ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass
        try:  # 隐藏标记：藏起来但不删
            c.execute("ALTER TABLE archives ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        for col in ("my_sliders", "their_sliders"):  # 性格滑轨值（JSON 文本）
            try:
                c.execute(f"ALTER TABLE archives ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass


def add(scenario, my_persona, their_persona, received, intent, result, has_image=False):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO history (created_at, scenario, my_persona, their_persona, received, intent, result, has_image)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                time.strftime("%Y-%m-%d %H:%M:%S"),
                scenario,
                my_persona,
                their_persona,
                received,
                intent,
                json.dumps(result, ensure_ascii=False),
                1 if has_image else 0,
            ),
        )
        return cur.lastrowid


def list_all(limit=30):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["result"] = json.loads(item["result"])
        items.append(item)
    return items


def delete(history_id):
    with _conn() as c:
        cur = c.execute("DELETE FROM history WHERE id = ?", (history_id,))
        return cur.rowcount > 0


def clear():
    with _conn() as c:
        c.execute("DELETE FROM history")


# ---- 聊天归档 ----

def add_archive(name, scenario, my_persona, their_persona, my_detail, their_detail,
                relation_stage, chat_history, my_gender="", their_gender="", relation_text="",
                my_sliders="", their_sliders=""):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO archives (name, created_at, scenario, my_persona, their_persona, my_detail, their_detail, relation_stage, chat_history, my_gender, their_gender, relation_text, my_sliders, their_sliders)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, time.strftime("%Y-%m-%d %H:%M:%S"), scenario, my_persona, their_persona,
             my_detail, their_detail, relation_stage, chat_history, my_gender, their_gender, relation_text,
             my_sliders, their_sliders),
        )
        return cur.lastrowid


def update_archive(archive_id, **fields):
    """更新档案的任意列（用于累积聊天记录、修改画像等）。"""
    allowed = {"name", "scenario", "my_persona", "their_persona", "my_detail",
               "their_detail", "relation_stage", "chat_history", "my_gender", "their_gender",
               "relation_text", "hidden", "my_sliders", "their_sliders"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return False
    cols = ", ".join(f"{k} = ?" for k in sets)
    with _conn() as c:
        cur = c.execute(f"UPDATE archives SET {cols} WHERE id = ?", (*sets.values(), archive_id))
        return cur.rowcount > 0


def get_archive(archive_id):
    with _conn() as c:
        row = c.execute("SELECT * FROM archives WHERE id = ?", (archive_id,)).fetchone()
    return dict(row) if row else None


def list_archives(hidden=False):
    """默认只返回可见档案；hidden=True 时只返回被隐藏的档案。"""
    flag = 1 if hidden else 0
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM archives WHERE COALESCE(hidden, 0) = ? ORDER BY id DESC", (flag,)
        ).fetchall()
    return [dict(row) for row in rows]


def delete_archive(archive_id):
    with _conn() as c:
        cur = c.execute("DELETE FROM archives WHERE id = ?", (archive_id,))
        return cur.rowcount > 0
