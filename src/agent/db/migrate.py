from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection


def _sqlite_columns(conn: Connection, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _table_exists(conn: Connection, table: str) -> bool:
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table},
    ).fetchone()
    return row is not None


def apply_sqlite_migrations(conn: Connection) -> None:
    """Bring older local SQLite files in line with the current ORM schema."""
    if not _table_exists(conn, "feedback_events"):
        return

    columns = _sqlite_columns(conn, "feedback_events")
    if "thread_id" not in columns:
        conn.execute(text("ALTER TABLE feedback_events ADD COLUMN thread_id VARCHAR(36)"))
    if "category" not in columns:
        conn.execute(text("ALTER TABLE feedback_events ADD COLUMN category VARCHAR(50)"))

    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_feedback_events_thread_id "
            "ON feedback_events (thread_id)"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_feedback_events_category "
            "ON feedback_events (category)"
        )
    )
