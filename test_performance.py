from benchmark_performance import (
    CLAIM_COUNT,
    P90_TARGET_SECONDS,
    make_claims,
    percentile_nearest_rank,
)


def test_p90_uses_nearest_rank():
    samples = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
    assert percentile_nearest_rank(samples, 0.90) == 0.09


def test_p90_rejects_empty_samples():
    import pytest

    with pytest.raises(ValueError):
        percentile_nearest_rank([], 0.90)


def test_benchmark_uses_twenty_claims():
    claims = make_claims(CLAIM_COUNT)
    assert len(claims) == 20


def test_performance_target_is_ten_seconds():
    assert P90_TARGET_SECONDS == 10.0