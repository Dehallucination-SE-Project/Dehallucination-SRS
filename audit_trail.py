
"""SQLite-backed audit trail for verification requests and results."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_DB_PATH = Path(
    os.environ.get("AUDIT_DB_PATH", "audit_trail.db")
)


def _utc_now() -> str:
    """Return the current UTC time as an ISO 8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


class AuditTrail:
    """Persist and retrieve audit events in a relational SQLite database."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = str(db_path)
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        """Create the audit table when it does not already exist."""
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_audit_events_request_id
                ON audit_events(request_id)
                """
            )

    def record_event(
        self,
        request_id: str,
        action: str,
        actor: str = "system",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate and persist a single audit event."""
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id must be a non-empty string")

        if not isinstance(action, str) or not action.strip():
            raise ValueError("action must be a non-empty string")

        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("actor must be a non-empty string")

        if details is None:
            details = {}

        if not isinstance(details, dict):
            raise TypeError("details must be a dictionary")

        try:
            details_json = json.dumps(details, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("details must be JSON serializable") from exc

        event = {
            "event_id": str(uuid4()),
            "request_id": request_id.strip(),
            "actor": actor.strip(),
            "action": action.strip(),
            "timestamp": _utc_now(),
            "details": json.loads(details_json),
        }

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    event_id, request_id, actor, action, timestamp, details
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event["event_id"],
                    event["request_id"],
                    event["actor"],
                    event["action"],
                    event["timestamp"],
                    details_json,
                ),
            )

        return event

    def record_request_accepted(
        self,
        request_id: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record that a verification request was accepted."""
        return self.record_event(
            request_id=request_id,
            action="request_accepted",
            details=details,
        )

    def record_final_result(
        self,
        request_id: str,
        result: dict[str, Any],
        actor: str = "system",
    ) -> dict[str, Any]:
        """Record a final result supplied by the verification pipeline."""
        if not isinstance(result, dict):
            raise TypeError("result must be a dictionary")

        return self.record_event(
            request_id=request_id,
            action="verification_completed",
            actor=actor,
            details={"result": result},
        )

    def get_events(self, request_id: str) -> list[dict[str, Any]]:
        """Return audit events for one request, in chronological order."""
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id must be a non-empty string")

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, request_id, actor, action, timestamp, details
                FROM audit_events
                WHERE request_id = ?
                ORDER BY timestamp ASC, rowid ASC
                """,
                (request_id.strip(),),
            ).fetchall()

        return [
            {
                "event_id": row["event_id"],
                "request_id": row["request_id"],
                "actor": row["actor"],
                "action": row["action"],
                "timestamp": row["timestamp"],
                "details": json.loads(row["details"]),
            }
            for row in rows
        ]
