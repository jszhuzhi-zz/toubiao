"""SQLite database layer for tender storage."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS tenders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    source      TEXT NOT NULL,
    source_url  TEXT,
    publish_date TEXT,
    deadline    TEXT,
    budget      TEXT,
    region      TEXT,
    category    TEXT,
    matched_keywords TEXT,
    raw_content TEXT,
    fetched_at  TEXT NOT NULL,
    UNIQUE(title, source)
);

CREATE INDEX IF NOT EXISTS idx_publish_date ON tenders(publish_date DESC);
CREATE INDEX IF NOT EXISTS idx_source ON tenders(source);
CREATE INDEX IF NOT EXISTS idx_fetched_at ON tenders(fetched_at DESC);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def insert_tender(
    title: str,
    source: str,
    source_url: Optional[str] = None,
    publish_date: Optional[str] = None,
    deadline: Optional[str] = None,
    budget: Optional[str] = None,
    region: Optional[str] = None,
    category: Optional[str] = None,
    matched_keywords: Optional[list[str]] = None,
    raw_content: Optional[str] = None,
) -> bool:
    """Insert a tender record. Returns True if inserted, False if duplicate."""
    fetched_at = datetime.now().isoformat()
    kw_str = ",".join(matched_keywords) if matched_keywords else None

    with get_conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO tenders
                    (title, source, source_url, publish_date, deadline,
                     budget, region, category, matched_keywords, raw_content, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (title, source, source_url, publish_date, deadline,
                 budget, region, category, kw_str, raw_content, fetched_at),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def query_tenders(
    keyword: Optional[str] = None,
    source: Optional[str] = None,
    region: Optional[str] = None,
    days: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[sqlite3.Row]:
    """Query tenders with optional filters."""
    conditions = []
    params = []

    if keyword:
        conditions.append("(title LIKE ? OR matched_keywords LIKE ? OR raw_content LIKE ?)")
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])

    if source:
        conditions.append("source = ?")
        params.append(source)

    if region:
        conditions.append("region LIKE ?")
        params.append(f"%{region}%")

    if days:
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)
        conditions.append("fetched_at >= ?")
        params.append(cutoff.isoformat())

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.extend([limit, offset])

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM tenders
            {where}
            ORDER BY publish_date DESC, fetched_at DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
    return rows


def count_tenders(keyword: Optional[str] = None, days: Optional[int] = None) -> int:
    conditions = []
    params = []

    if keyword:
        conditions.append("(title LIKE ? OR matched_keywords LIKE ?)")
        kw = f"%{keyword}%"
        params.extend([kw, kw])

    if days:
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        conditions.append("fetched_at >= ?")
        params.append(cutoff.isoformat())

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    with get_conn() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM tenders {where}", params).fetchone()[0]


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
        by_source = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM tenders GROUP BY source ORDER BY cnt DESC"
        ).fetchall()
        recent = conn.execute(
            "SELECT COUNT(*) FROM tenders WHERE fetched_at >= date('now', '-7 days')"
        ).fetchone()[0]
    return {
        "total": total,
        "recent_7d": recent,
        "by_source": [(r["source"], r["cnt"]) for r in by_source],
    }
