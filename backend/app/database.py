from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import get_settings


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS feedback_items (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        related_id TEXT NOT NULL,
        expected_behavior TEXT,
        actual_behavior TEXT,
        raw_content TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        submitted_at TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_feedback_items_status ON feedback_items(status)",
    "CREATE INDEX IF NOT EXISTS idx_feedback_items_related_id ON feedback_items(related_id)",
    "CREATE INDEX IF NOT EXISTS idx_feedback_items_created_at ON feedback_items(created_at)",
    """
    CREATE TABLE IF NOT EXISTS draft_batches (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        primary_related_id TEXT,
        related_id_count INTEGER NOT NULL DEFAULT 0,
        integration_error TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_draft_batches_status ON draft_batches(status)",
    "CREATE INDEX IF NOT EXISTS idx_draft_batches_primary_related_id ON draft_batches(primary_related_id)",
    """
    CREATE TABLE IF NOT EXISTS draft_batch_items (
        id TEXT PRIMARY KEY,
        batch_id TEXT NOT NULL,
        feedback_item_id TEXT NOT NULL UNIQUE,
        FOREIGN KEY(batch_id) REFERENCES draft_batches(id),
        FOREIGN KEY(feedback_item_id) REFERENCES feedback_items(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS drafts (
        id TEXT PRIMARY KEY,
        batch_id TEXT NOT NULL,
        title TEXT NOT NULL,
        body_markdown TEXT NOT NULL,
        related_id_summary TEXT NOT NULL,
        status TEXT NOT NULL,
        ai_model TEXT,
        prompt_snapshot TEXT,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(batch_id) REFERENCES draft_batches(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_drafts_batch_id ON drafts(batch_id)",
    "CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status)",
    """
    CREATE TABLE IF NOT EXISTS submissions (
        id TEXT PRIMARY KEY,
        draft_id TEXT NOT NULL,
        github_issue_number INTEGER NOT NULL,
        github_issue_url TEXT NOT NULL,
        related_id TEXT NOT NULL,
        github_state TEXT,
        labels_snapshot TEXT,
        response_status INTEGER NOT NULL,
        submitted_at TEXT NOT NULL,
        error_summary TEXT,
        FOREIGN KEY(draft_id) REFERENCES drafts(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_submissions_related_id ON submissions(related_id)",
    "CREATE INDEX IF NOT EXISTS idx_submissions_submitted_at ON submissions(submitted_at)",
    "CREATE INDEX IF NOT EXISTS idx_submissions_github_issue_number ON submissions(github_issue_number)",
)


def _database_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if database_url.startswith(prefix):
        return Path(database_url[len(prefix) :]).expanduser().resolve()
    return Path(database_url).expanduser().resolve()


def get_connection() -> sqlite3.Connection:
    database_path = _database_path(get_settings().database_url)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()


@contextmanager
def connection_context() -> sqlite3.Connection:
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
