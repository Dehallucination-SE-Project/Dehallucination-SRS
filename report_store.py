
"""SQLite-backed storage and retrieval for verification reports."""

import json
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DB = Path("verification_reports.db")


class ReportStore:
    """Persist generated verification reports by request ID."""

    def __init__(
        self,
        db_path: str | Path = DEFAULT_REPORT_DB,
    ) -> None:
        self.db_path = str(db_path)

        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS verification_reports (
                    request_id TEXT PRIMARY KEY,
                    report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    )
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def save_report(
        self,
        request_id: str,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        """Save a report; reject duplicate request IDs."""
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id must be a non-empty string")

        if not isinstance(report, dict):
            raise TypeError("report must be a dictionary")

        try:
            report_json = json.dumps(
                report,
                ensure_ascii=False,
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "report must contain valid JSON-compatible data"
            ) from exc

        request_id = request_id.strip()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO verification_reports (
                    request_id, report_json
                )
                VALUES (?, ?)
                """,
                (request_id, report_json),
            )

            if cursor.rowcount == 0:
                raise ValueError(
                    "a report already exists for this request_id"
                )

            row = connection.execute(
                """
                SELECT created_at
                FROM verification_reports
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()

        return {
            "request_id": request_id,
            "created_at": row["created_at"],
            "report": json.loads(report_json),
        }

    def get_report(
        self,
        request_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve a report by request ID, or return None if absent."""
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id must be a non-empty string")

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT request_id, report_json, created_at
                FROM verification_reports
                WHERE request_id = ?
                """,
                (request_id.strip(),),
            ).fetchone()

        if row is None:
            return None

        return {
            "request_id": row["request_id"],
            "created_at": row["created_at"],
            "report": json.loads(row["report_json"]),
        }
