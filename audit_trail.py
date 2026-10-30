"""SQLite-backed audit trail with configurable request-retention cleanup."""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

DEFAULT_DB_PATH = Path(os.environ.get("AUDIT_DB_PATH", "audit_trail.db"))
DEFAULT_RETENTION_DAYS = 90


def _utc_now() -> str:
    """Return the current UTC time as an ISO 8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _validate_retention_days(value: Any) -> int:
    """Validate a positive integer retention period."""
    if isinstance(value, bool):
        raise ValueError("retention_days must be a positive integer")
    try:
        days = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("retention_days must be a positive integer") from exc
    if days <= 0 or str(value).strip() not in (str(days), f"+{days}"):
        raise ValueError("retention_days must be a positive integer")
    return days


class AuditTrail:
    """Persist audit events and purge events exceeding a configurable age.

    AUDIT_RETENTION_DAYS controls the retention window and defaults to 90 days.
    The SRS requires configurable retention but does not specify a duration;
    deployments should set this environment variable to their approved policy.
    Expired audit records are purged when the store is initialized, and callers
    can invoke ``purge_expired_events`` again for scheduled/manual maintenance.
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        retention_days: int | None = None,
        *,
        purge_on_start: bool = True,
    ) -> None:
        self.db_path = str(db_path)
        configured_days = (
            os.environ.get("AUDIT_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS))
            if retention_days is None
            else retention_days
        )
        self.retention_days = _validate_retention_days(configured_days)
        self._initialize_database()
        if purge_on_start:
            self.purge_expired_events()

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
                CREATE INDEX IF NOT EXISTS idx_audit_events_request_id
                ON audit_events(request_id)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp
                ON audit_events(timestamp)
                """
            )

    def purge_expired_events(
        self,
        retention_days: int | None = None,
        *,
        now: datetime | None = None,
    ) -> int:
        """Delete events older than the retention window and return count.

        The boundary is exclusive: records whose timestamp equals the cutoff
        are retained. ``now`` is injectable to make policy tests deterministic.
        """
        days = self.retention_days if retention_days is None else _validate_retention_days(retention_days)
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        cutoff = (current.astimezone(timezone.utc) - timedelta(days=days)).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM audit_events WHERE timestamp < ?",
                (cutoff,),
            )
            return cursor.rowcount

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
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event["event_id"], event["request_id"], event["actor"],
                 event["action"], event["timestamp"], details_json),
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
