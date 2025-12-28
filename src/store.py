import hashlib
import logging
import sqlite3
from pathlib import Path
from datetime import datetime

LOGGER = logging.getLogger(__name__)


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            url_hash TEXT NOT NULL UNIQUE,
            title TEXT,
            author TEXT,
            published TEXT,
            summary TEXT,
            content TEXT,
            tags TEXT,
            source TEXT,
            matched_keywords TEXT,
            included INTEGER DEFAULT 0,
            filter_reason TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_created ON articles(created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_included ON articles(included)"
    )
    conn.commit()
    return conn


def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def insert_article(conn: sqlite3.Connection, record: dict) -> bool:
    url_hash = hash_url(record["url"])
    try:
        conn.execute(
            """
            INSERT INTO articles (
                url, url_hash, title, author, published, summary, content, tags, source,
                matched_keywords, included, filter_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["url"],
                url_hash,
                record.get("title", ""),
                record.get("author", ""),
                record.get("published"),
                record.get("summary", ""),
                record.get("content", ""),
                ",".join(record.get("tags", [])),
                record.get("source", ""),
                ",".join(record.get("matched_keywords", [])),
                1 if record.get("included") else 0,
                record.get("filter_reason", ""),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        LOGGER.info("Duplicate article skipped: %s", record["url"])
        return False


def fetch_recent(conn: sqlite3.Connection, days: int) -> list[dict]:
    cursor = conn.execute(
        """
        SELECT url, title, author, published, summary, content, tags, source, matched_keywords
        FROM articles
        WHERE included = 1
        AND datetime(created_at) >= datetime('now', ?)
        ORDER BY datetime(created_at) DESC
        """,
        (f"-{days} days",),
    )
    rows = cursor.fetchall()
    records = []
    for row in rows:
        records.append(
            {
                "url": row[0],
                "title": row[1],
                "author": row[2],
                "published": row[3],
                "summary": row[4],
                "content": row[5],
                "tags": row[6].split(",") if row[6] else [],
                "source": row[7],
                "matched_keywords": row[8].split(",") if row[8] else [],
            }
        )
    return records


def stats_recent(conn: sqlite3.Connection, days: int) -> dict:
    total_cursor = conn.execute(
        """
        SELECT COUNT(*) FROM articles
        WHERE datetime(created_at) >= datetime('now', ?)
        """,
        (f"-{days} days",),
    )
    total = total_cursor.fetchone()[0]

    included_cursor = conn.execute(
        """
        SELECT COUNT(*) FROM articles
        WHERE included = 1 AND datetime(created_at) >= datetime('now', ?)
        """,
        (f"-{days} days",),
    )
    included = included_cursor.fetchone()[0]

    reason_cursor = conn.execute(
        """
        SELECT filter_reason, COUNT(*)
        FROM articles
        WHERE included = 0 AND datetime(created_at) >= datetime('now', ?)
        GROUP BY filter_reason
        ORDER BY COUNT(*) DESC
        """,
        (f"-{days} days",),
    )
    reasons = {row[0] or "unknown": row[1] for row in reason_cursor.fetchall()}

    keyword_cursor = conn.execute(
        """
        SELECT matched_keywords FROM articles
        WHERE included = 1 AND datetime(created_at) >= datetime('now', ?)
        """,
        (f"-{days} days",),
    )
    keywords: dict[str, int] = {}
    for (keyword_str,) in keyword_cursor.fetchall():
        if not keyword_str:
            continue
        for keyword in keyword_str.split(","):
            keywords[keyword] = keywords.get(keyword, 0) + 1

    return {
        "total": total,
        "included": included,
        "excluded": total - included,
        "reasons": reasons,
        "keywords": dict(sorted(keywords.items(), key=lambda item: item[1], reverse=True)),
    }
