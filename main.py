from report_store import ReportStore
from verification_report import generate_verification_report
from audit_trail import AuditTrail
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from evidence_adapters import (
    EvidenceSource,
    EvidenceSourceUnavailableError,
    UnavailableEvidenceAdapter,
)
from resilience import (
    EvidenceRetrievalTimeoutError,
    retrieve_queries_independently,
    retrieve_with_timeout,
)
from review_queue import (
    ReviewAlreadyCompletedError,
    ReviewNotFoundError,
    ReviewQueue,
)
from service_status import build_service_status


class ReportCreateRequest(BaseModel):
    claims: list[dict[str, Any]]
    risk_summary: dict[str, Any] | None = None
    review_required: bool = False


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reviewer: str = Field(min_length=1, max_length=128)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("reviewer")
    @classmethod
    def reviewer_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reviewer must not be blank")
        return value.strip()


app = FastAPI(
    title="Dehallucination API",
    description="API foundation for the Dehallucination project",
    version="0.1.0",
)

# Configurable default for the current prototype. Network-backed adapters should
# additionally set native connect/read timeouts for their underlying clients.
EVIDENCE_RETRIEVAL_TIMEOUT_SECONDS = 2.0

# No real external evidence source is configured by default.
# Tests or future configuration can supply a different adapter.
report_store = ReportStore()
evidence_source: EvidenceSource = UnavailableEvidenceAdapter()
audit_trail = AuditTrail()
review_queue = ReviewQueue()


class EvidenceRetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value


class EvidenceBatchRetrieveRequest(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=100)

    @field_validator("queries")
    @classmethod
    def queries_must_not_be_blank(cls, values: list[str]) -> list[str]:
        if any(not query.strip() for query in values):
            raise ValueError("queries must not contain blank queries")
        return values


class EvidenceRetrieveResponse(BaseModel):
    query: str
    evidence: list[dict[str, Any]]


@app.get("/api/v1/health")
def health_check():
    """Return liveness plus detailed status for core and external dependencies."""
    return build_service_status(
        app_name="dehallucination-api",
        version=app.version,
        report_store=report_store,
        audit_trail=audit_trail,
        review_queue=review_queue,
        evidence_source=evidence_source,
    )


@app.get("/api/v1/status")
def service_status():
    """Alias for the detailed service/dependency status document."""
    return health_check()


class VerifyRequest(BaseModel):
    input_text: str = Field(min_length=1, max_length=10000)
    query_context: str | None = None
    domain: str | None = None
    verification_mode: str = "standard"
    source_policy: str | None = None

    @field_validator("input_text")
    @classmethod
    def input_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("input_text must not be blank")
        return value


class VerifyResponse(BaseModel):
    request_id: str
    created_at: datetime
    status: str
    input_text: str
    review_required: bool = False


@app.get("/")
def root():
    return {"message": "Dehallucination API is running"}


@app.post(
    "/api/v1/evidence/retrieve",
    response_model=EvidenceRetrieveResponse,
)
def retrieve_evidence(request: EvidenceRetrieveRequest):
    """Retrieve evidence with a bounded wait and explicit dependency errors."""
    try:
        results = retrieve_with_timeout(
            evidence_source,
            request.query,
            timeout_seconds=EVIDENCE_RETRIEVAL_TIMEOUT_SECONDS,
        )
    except EvidenceRetrievalTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except EvidenceSourceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Evidence retrieval failed",
        ) from exc

    return EvidenceRetrieveResponse(query=request.query, evidence=results)


@app.post("/api/v1/evidence/retrieve/batch")
def retrieve_evidence_batch(request: EvidenceBatchRetrieveRequest):
    """Retrieve multiple queries independently, returning successful partial results."""
    return retrieve_queries_independently(
        evidence_source,
        request.queries,
        timeout_seconds=EVIDENCE_RETRIEVAL_TIMEOUT_SECONDS,
    )


@app.post("/api/v1/verify", response_model=VerifyResponse, status_code=202)
def verify_request(request: VerifyRequest):
    """Accept a verification request and expose whether it requires human review."""
    request_id = str(uuid4())
    created_at = datetime.now(timezone.utc)
    review_required = request.verification_mode == "review-required"

    audit_trail.record_request_accepted(
        request_id=request_id,
        details={
            "input_length": len(request.input_text),
            "verification_mode": request.verification_mode,
            "domain": request.domain,
            "review_required": review_required,
        },
    )

    return VerifyResponse(
        request_id=request_id,
        created_at=created_at,
        status="accepted",
        input_text=request.input_text,
        review_required=review_required,
    )


@app.post("/api/v1/reports/{request_id}", status_code=201)
def create_report(
    request_id: str,
    request: ReportCreateRequest,
):
    """Generate and persist a report; optionally place it in the review queue."""
    try:
        report = generate_verification_report(
            claims=request.claims,
            risk_summary=request.risk_summary,
        )
        saved_report = report_store.save_report(request_id, report)
        if request.review_required:
            review_item = review_queue.add_pending(request_id)
            saved_report["review"] = review_item
            audit_trail.record_event(
                request_id=request_id,
                action="review_requested",
                details={"status": "pending"},
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (TypeError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return saved_report


@app.get("/api/v1/reports/{request_id}")
def retrieve_report(request_id: str):
    """Retrieve a saved report and any associated human-review state."""
    try:
        report = report_store.get_report(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Verification report not found",
        )

    review_item = review_queue.get(request_id)
    if review_item is not None:
        report["review"] = review_item
    return report


@app.get("/api/v1/reviews/pending")
def list_pending_reviews(limit: int = Query(default=100, ge=1, le=500)):
    """List reports awaiting human review, including report payloads."""
    items = review_queue.list_pending(limit=limit)
    for item in items:
        item["report"] = report_store.get_report(item["request_id"])
    return {"count": len(items), "items": items}


@app.get("/api/v1/reviews/{request_id}")
def get_review(request_id: str):
    """Get review state and the associated verification report."""
    try:
        item = review_queue.get(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Review item not found")
    item["report"] = report_store.get_report(request_id)
    return item


@app.post("/api/v1/reviews/{request_id}")
def decide_review(request_id: str, request: ReviewDecisionRequest):
    """Record an approve/reject decision for a pending report review."""
    try:
        item = review_queue.record_decision(
            request_id,
            decision=request.decision,
            reviewer=request.reviewer,
            comment=request.comment,
        )
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReviewAlreadyCompletedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit_trail.record_event(
        request_id=request_id,
        action="review_decision",
        actor=request.reviewer,
        details={"decision": request.decision, "comment": request.comment},
    )
    return item
