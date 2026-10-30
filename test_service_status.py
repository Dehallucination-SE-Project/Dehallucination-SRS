import sqlite3

from evidence_adapters import UnavailableEvidenceAdapter
from service_status import build_service_status, check_evidence_source, check_sqlite_store
from review_queue import ReviewQueue


class Store:
    def __init__(self, path):
        self.db_path = str(path)


def make_db(path, table):
    with sqlite3.connect(path) as connection:
        connection.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")


def test_sqlite_store_reports_healthy_when_required_table_exists(tmp_path):
    path = tmp_path / "reports.db"
    make_db(path, "verification_reports")

    result = check_sqlite_store(path, "verification_reports")

    assert result["status"] == "healthy"


def test_sqlite_store_reports_missing_database_without_creating_it(tmp_path):
    path = tmp_path / "missing.db"

    result = check_sqlite_store(path, "verification_reports")

    assert result["status"] == "unhealthy"
    assert not path.exists()


def test_sqlite_store_reports_missing_table(tmp_path):
    path = tmp_path / "reports.db"
    make_db(path, "other_table")

    result = check_sqlite_store(path, "verification_reports")

    assert result["status"] == "unhealthy"
    assert "missing" in result["detail"]


def test_unavailable_evidence_adapter_is_not_configured():
    result = check_evidence_source(UnavailableEvidenceAdapter())

    assert result["status"] == "not_configured"


def test_custom_evidence_health_check_is_used():
    class HealthyAdapter:
        def health_check(self):
            return {"status": "healthy", "detail": "stub is ready"}

    assert check_evidence_source(HealthyAdapter()) == {
        "status": "healthy", "detail": "stub is ready"
    }


def test_overall_status_degrades_when_evidence_is_not_configured(tmp_path):
    report_db = tmp_path / "reports.db"
    audit_db = tmp_path / "audit.db"
    review_db = tmp_path / "review.db"
    make_db(report_db, "verification_reports")
    make_db(audit_db, "audit_events")
    queue = ReviewQueue(review_db)

    result = build_service_status(
        app_name="dehallucination-api",
        version="0.1.0",
        report_store=Store(report_db),
        audit_trail=Store(audit_db),
        review_queue=queue,
        evidence_source=UnavailableEvidenceAdapter(),
    )

    assert result["status"] == "ok"
    assert result["overall_status"] == "degraded"
    assert result["dependencies"]["evidence_sources"] == "not_configured"
    assert result["components"]["review_queue"]["status"] == "healthy"


def test_overall_status_is_unhealthy_when_core_store_is_missing(tmp_path):
    audit_db = tmp_path / "audit.db"
    review_db = tmp_path / "review.db"
    make_db(audit_db, "audit_events")
    queue = ReviewQueue(review_db)

    result = build_service_status(
        app_name="dehallucination-api",
        version="0.1.0",
        report_store=Store(tmp_path / "missing-reports.db"),
        audit_trail=Store(audit_db),
        review_queue=queue,
        evidence_source=UnavailableEvidenceAdapter(),
    )

    assert result["overall_status"] == "unhealthy"
