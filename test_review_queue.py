import pytest

from review_queue import (
    ReviewAlreadyCompletedError,
    ReviewNotFoundError,
    ReviewQueue,
)


def test_add_pending_review_and_retrieve(tmp_path):
    queue = ReviewQueue(tmp_path / "review.db")

    item = queue.add_pending("request-1")

    assert item["request_id"] == "request-1"
    assert item["status"] == "pending"
    assert queue.get("request-1")["status"] == "pending"


def test_add_pending_is_idempotent(tmp_path):
    queue = ReviewQueue(tmp_path / "review.db")

    first = queue.add_pending("request-1")
    second = queue.add_pending("request-1")

    assert first["submitted_at"] == second["submitted_at"]
    assert len(queue.list_pending()) == 1


def test_pending_list_is_oldest_first_and_limited(tmp_path):
    queue = ReviewQueue(tmp_path / "review.db")
    queue.add_pending("request-1")
    queue.add_pending("request-2")

    result = queue.list_pending(limit=1)

    assert len(result) == 1
    assert result[0]["request_id"] == "request-1"


def test_approve_review_records_reviewer_and_time(tmp_path):
    queue = ReviewQueue(tmp_path / "review.db")
    queue.add_pending("request-1")

    result = queue.record_decision(
        "request-1", decision="approved", reviewer="reviewer-1", comment="Looks good"
    )

    assert result["status"] == "approved"
    assert result["reviewer"] == "reviewer-1"
    assert result["comment"] == "Looks good"
    assert result["reviewed_at"]
    assert queue.list_pending() == []


def test_reject_review_is_supported(tmp_path):
    queue = ReviewQueue(tmp_path / "review.db")
    queue.add_pending("request-1")

    result = queue.record_decision(
        "request-1", decision="rejected", reviewer="reviewer-1"
    )

    assert result["status"] == "rejected"


def test_decision_for_missing_item_raises(tmp_path):
    queue = ReviewQueue(tmp_path / "review.db")

    with pytest.raises(ReviewNotFoundError):
        queue.record_decision(
            "missing", decision="approved", reviewer="reviewer-1"
        )


def test_second_decision_is_rejected(tmp_path):
    queue = ReviewQueue(tmp_path / "review.db")
    queue.add_pending("request-1")
    queue.record_decision("request-1", decision="approved", reviewer="reviewer-1")

    with pytest.raises(ReviewAlreadyCompletedError):
        queue.record_decision("request-1", decision="rejected", reviewer="reviewer-2")


def test_invalid_decision_and_reviewer_are_rejected(tmp_path):
    queue = ReviewQueue(tmp_path / "review.db")
    queue.add_pending("request-1")

    with pytest.raises(ValueError):
        queue.record_decision("request-1", decision="pending", reviewer="reviewer-1")
    with pytest.raises(ValueError):
        queue.record_decision("request-1", decision="approved", reviewer="   ")


def test_invalid_pending_limit_is_rejected(tmp_path):
    queue = ReviewQueue(tmp_path / "review.db")

    with pytest.raises(ValueError):
        queue.list_pending(limit=0)
    with pytest.raises(ValueError):
        queue.list_pending(limit=501)
