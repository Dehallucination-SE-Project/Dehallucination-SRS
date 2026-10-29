"""Manual P90 baseline benchmark for the currently implemented report API.

Run from the repository root:
    python benchmark_performance.py

Important: the current /api/v1/verify endpoint only accepts/records a request.
This benchmark measures report generation + persistence for a 20-claim payload.
It is a useful baseline, but it does NOT prove the complete verification pipeline
meets DH-NF-001. Re-run against the full verification workflow when implemented.
"""
from __future__ import annotations

import gc
import math
import statistics
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

import main
from report_store import ReportStore


CLAIM_COUNT = 20
SAMPLE_COUNT = 30
P90_TARGET_SECONDS = 10.0


def percentile_nearest_rank(values: list[float], percentile: float) -> float:
    """Return the nearest-rank percentile (e.g. P90) for non-empty values."""
    if not values:
        raise ValueError("values must not be empty")
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be in (0, 1]")
    ordered = sorted(values)
    rank = math.ceil(percentile * len(ordered))
    return ordered[rank - 1]


def make_claims(count: int) -> list[dict]:
    return [
        {
            "claim_id": f"C-{i:03d}",
            "normalized_text": f"Sample factual claim number {i}.",
            "verdict": "Supported",
            "evidence": [
                {"source": "benchmark-fixture", "text": f"Evidence for claim {i}."}
            ],
        }
        for i in range(1, count + 1)
    ]


def main_benchmark() -> int:
    timings: list[float] = []
    original_store = main.report_store

    # Isolate benchmark writes from the project's normal report database.
    with tempfile.TemporaryDirectory(
        prefix="dh086-benchmark-", ignore_cleanup_errors=True
    ) as temp_dir:
        main.report_store = ReportStore(Path(temp_dir) / "benchmark.sqlite3")
        client = TestClient(main.app)
        claims = make_claims(CLAIM_COUNT)

        try:
            # One warm-up request is excluded from the measurements.
            warmup = client.post(
                f"/api/v1/reports/{uuid4()}",
                json={"claims": claims},
            )
            if warmup.status_code != 201:
                print(f"Warm-up failed: {warmup.status_code} {warmup.text}")
                return 1

            for _ in range(SAMPLE_COUNT):
                started = time.perf_counter()
                response = client.post(
                    f"/api/v1/reports/{uuid4()}",
                    json={"claims": claims},
                )
                elapsed = time.perf_counter() - started

                if response.status_code != 201:
                    print(f"Sample failed: {response.status_code} {response.text}")
                    return 1
                timings.append(elapsed)
        finally:
            main.report_store = original_store
            # SQLite connections can remain referenced briefly on Windows;
            # collect released objects before TemporaryDirectory cleanup.
            gc.collect()

    p90 = percentile_nearest_rank(timings, 0.90)
    median = statistics.median(timings)
    maximum = max(timings)

    print("DH-086 performance baseline")
    print(f"Endpoint: POST /api/v1/reports/{{request_id}}")
    print(f"Claims per request: {CLAIM_COUNT}")
    print(f"Measured samples: {SAMPLE_COUNT} (plus one excluded warm-up)")
    print(f"Median: {median:.4f} seconds")
    print(f"P90 (nearest-rank): {p90:.4f} seconds")
    print(f"Maximum: {maximum:.4f} seconds")
    print(f"SRS P90 target: <= {P90_TARGET_SECONDS:.2f} seconds")
    print(f"Report endpoint baseline meets threshold: {p90 <= P90_TARGET_SECONDS}")

    print(
        "\nInterpretation: this measures report generation and SQLite persistence, "
        "not end-to-end claim verification. Do not claim full DH-NF-001 compliance "
        "until the complete verification workflow is benchmarked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main_benchmark())