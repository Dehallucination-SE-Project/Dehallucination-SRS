"""Report ownership migration and persistence checks."""

import sqlite3

from report_store import ReportStore


def test_existing_report_database_gets_nullable_owner_column(tmp_path):
    db_path = tmp_path / "legacy-reports.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE verification_reports (
                request_id TEXT PRIMARY KEY,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
            )
            """
        )
        connection.execute(
            "INSERT INTO verification_reports (request_id, report_json) VALUES (?, ?)",
            ("legacy-request", '{"claim_count":0}'),
        )

    store = ReportStore(db_path)

    assert store.get_report_owner("legacy-request") is None
    assert store.get_report("legacy-request")["report"] == {"claim_count": 0}


def test_report_owner_is_persisted_with_report(tmp_path):
    store = ReportStore(tmp_path / "reports.db")

    store.save_report(
        "request-1",
        {"claim_count": 1},
        owner_subject="developer-1",
    )

    assert store.get_report_owner("request-1") == "developer-1"
