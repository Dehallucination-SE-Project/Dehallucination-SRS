from datetime import datetime, timezone
import sqlite3

import pytest

from audit_trail import AuditTrail

UTC = timezone.utc


def test_purge_expired_events_removes_old_records_and_keeps_newer(tmp_path):
    db_path = tmp_path / "audit.db"
    trail = AuditTrail(db_path, retention_days=30)
    trail.record_request_accepted("old-request")
    trail.record_request_accepted("new-request")
    trail.record_request_accepted("cutoff-request")

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE audit_events SET timestamp = ? WHERE request_id = ?",
            ("2025-11-30T00:00:00+00:00", "old-request"),
        )
        connection.execute(
            "UPDATE audit_events SET timestamp = ? WHERE request_id = ?",
            ("2025-12-15T00:00:00+00:00", "new-request"),
        )
        connection.execute(
            "UPDATE audit_events SET timestamp = ? WHERE request_id = ?",
            ("2025-12-02T00:00:00+00:00", "cutoff-request"),
        )

    deleted = trail.purge_expired_events(
        now=datetime(2026, 1, 1, tzinfo=UTC)
    )

    assert deleted == 1
    assert trail.get_events("old-request") == []
    assert len(trail.get_events("new-request")) == 1
    assert len(trail.get_events("cutoff-request")) == 1


def test_startup_purge_uses_configured_retention_days(tmp_path):
    db_path = tmp_path / "audit.db"
    initial = AuditTrail(db_path, retention_days=30)
    initial.record_request_accepted("expiring")
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE audit_events SET timestamp = ? WHERE request_id = ?",
            ("2020-01-01T00:00:00+00:00", "expiring"),
        )

    restarted = AuditTrail(db_path, retention_days=30)

    assert restarted.get_events("expiring") == []


def test_retention_days_can_be_configured_with_environment_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "17")

    trail = AuditTrail(tmp_path / "audit.db", purge_on_start=False)

    assert trail.retention_days == 17


@pytest.mark.parametrize("retention_days", [0, -1, True, "not-a-number"])
def test_invalid_explicit_retention_period_is_rejected(tmp_path, retention_days):
    with pytest.raises(ValueError):
        AuditTrail(tmp_path / "audit.db", retention_days=retention_days)


def test_purge_requires_timezone_aware_now(tmp_path):
    trail = AuditTrail(tmp_path / "audit.db", retention_days=30)

    with pytest.raises(ValueError, match="timezone-aware"):
        trail.purge_expired_events(now=datetime(2026, 1, 1))
