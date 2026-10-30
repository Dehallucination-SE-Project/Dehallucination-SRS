"""SQLite-backed human review queue for reports that require review."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_REVIEW_DB = Path(os.environ.get("REVIEW_DB_PATH", "review_queue.db"))


class ReviewNotFoundError(ValueError):
    """Raised when a requested review item does not exist."""


class ReviewAlreadyCompletedError(ValueError):
    """Raised when a review item has already received a decision."""


class ReviewQueue:
    """Persist pending review items and reviewer decisions."""

    def __init__(self, db_path: str | Path = DEFAULT_REVIEW_DB) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS review_items (
                    request_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
                    submitted_at TEXT NOT NULL,
                    reviewer TEXT,
                    comment TEXT,
                    reviewed_at TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_review_items_status ON review_items(status, submitted_at)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _validate_request_id(request_id: str) -> str:
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id must be a non-empty string")
        return request_id.strip()

    def add_pending(self, request_id: str) -> dict[str, Any]:
        request_id = self._validate_request_id(request_id)
        submitted_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO review_items (request_id, status, submitted_at) VALUES (?, 'pending', ?)",
                (request_id, submitted_at),
            )
            row = connection.execute(
                "SELECT * FROM review_items WHERE request_id = ?", (request_id,)
            ).fetchone()
        return dict(row)

    def get(self, request_id: str) -> dict[str, Any] | None:
        request_id = self._validate_request_id(request_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM review_items WHERE request_id = ?", (request_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_pending(self, limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer between 1 and 500")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM review_items WHERE status = 'pending' ORDER BY submitted_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def record_decision(
        self,
        request_id: str,
        *,
        decision: str,
        reviewer: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        request_id = self._validate_request_id(request_id)
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be 'approved' or 'rejected'")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError("reviewer must be a non-empty string")
        if comment is not None and not isinstance(comment, str):
            raise ValueError("comment must be a string or None")
        if comment is not None and len(comment) > 2000:
            raise ValueError("comment must be at most 2000 characters")

        reviewed_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE review_items
                   SET status = ?, reviewer = ?, comment = ?, reviewed_at = ?
                   WHERE request_id = ? AND status = 'pending'""",
                (decision, reviewer.strip(), comment, reviewed_at, request_id),
            )
            if cursor.rowcount == 0:
                exists = connection.execute(
                    "SELECT status FROM review_items WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                if exists is None:
                    raise ReviewNotFoundError("Review item not found")
                raise ReviewAlreadyCompletedError("Review item already has a decision")
            row = connection.execute(
                "SELECT * FROM review_items WHERE request_id = ?", (request_id,)
            ).fetchone()
        return dict(row)
