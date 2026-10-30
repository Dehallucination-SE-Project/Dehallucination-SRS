"""Read-only health checks for core stores and evidence dependencies."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

from evidence_adapters import LocalEvidenceAdapter, UnavailableEvidenceAdapter


def check_sqlite_store(db_path: str | Path, required_table: str) -> dict[str, str]:
    """Check an existing SQLite store without creating a missing database."""
    path_text = str(db_path)
    if path_text == ":memory:":
        return {
            "status": "unknown",
            "detail": "In-memory SQLite health cannot be checked from a separate connection",
        }

    path = Path(path_text)
    if not path.is_file():
        return {"status": "unhealthy", "detail": "Database file is missing"}

    try:
        safe_path = quote(path.resolve().as_posix(), safe="/:")
        uri = f"file:{safe_path}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=1) as connection:
            connection.execute("SELECT 1").fetchone()
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (required_table,),
            ).fetchone()
            if table is None:
                return {
                    "status": "unhealthy",
                    "detail": f"Required table '{required_table}' is missing",
                }
    except (sqlite3.Error, OSError) as exc:
        return {"status": "unhealthy", "detail": f"Database check failed: {type(exc).__name__}"}

    return {"status": "healthy", "detail": "SQLite store is reachable"}


def check_evidence_source(source: Any) -> dict[str, str]:
    """Report only what the adapter can establish; never perform a live query."""
    if isinstance(source, UnavailableEvidenceAdapter):
        return {
            "status": "not_configured",
            "detail": "No evidence source is configured",
        }

    health_check = getattr(source, "health_check", None)
    if callable(health_check):
        try:
            result = health_check()
        except Exception as exc:  # health probes must not break the endpoint
            return {
                "status": "unhealthy",
                "detail": f"Evidence source health check failed: {type(exc).__name__}",
            }

        if isinstance(result, dict):
            status = result.get("status", "unknown")
            detail = result.get("detail", "Adapter-provided health status")
            if status not in {"healthy", "unhealthy", "unknown", "not_configured"}:
                status = "unknown"
            return {"status": status, "detail": str(detail)}
        if result is True:
            return {"status": "healthy", "detail": "Adapter health check passed"}
        if result is False:
            return {"status": "unhealthy", "detail": "Adapter health check failed"}
        return {"status": "unknown", "detail": "Adapter health check returned no status"}

    # The local in-process adapter is known to be configured, but its health
    # cannot be inferred for arbitrary third-party adapters without a probe.
    if isinstance(source, LocalEvidenceAdapter):
        return {"status": "healthy", "detail": "Local evidence adapter is configured"}
    return {
        "status": "unknown",
        "detail": "Adapter does not expose a health_check method",
    }


def build_service_status(
    *,
    app_name: str,
    version: str,
    report_store: Any,
    audit_trail: Any,
    review_queue: Any,
    evidence_source: Any,
) -> dict[str, Any]:
    """Build detailed component health plus a derived overall status."""
    components = {
        "api": {"status": "healthy", "detail": "API process is responding"},
        "report_store": check_sqlite_store(
            report_store.db_path, "verification_reports"
        ),
        "audit_store": check_sqlite_store(audit_trail.db_path, "audit_events"),
        "review_queue": check_sqlite_store(
            review_queue.db_path, "review_items"
        ),
        "evidence_sources": check_evidence_source(evidence_source),
    }

    core_names = ("api", "report_store", "audit_store", "review_queue")
    if any(components[name]["status"] == "unhealthy" for name in core_names):
        overall = "unhealthy"
    elif any(
        components[name]["status"] != "healthy"
        for name in components
    ):
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": "ok",  # preserves the existing liveness-probe contract
        "overall_status": overall,
        "service": app_name,
        "version": version,
        "components": components,
        # Backward-compatible field used by existing clients/tests.
        "dependencies": {
            "evidence_sources": components["evidence_sources"]["status"]
        },
    }
