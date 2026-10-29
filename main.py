from report_store import ReportStore
from verification_report import generate_verification_report
from audit_trail import AuditTrail
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

class ReportCreateRequest(BaseModel):
    claims: list[dict[str, Any]]
    risk_summary: dict[str, Any] | None = None

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
    """Report API health and external evidence-source configuration."""
    return {
        "status": "ok",
        "service": "dehallucination-api",
        "version": app.version,
        "dependencies": {
            "evidence_sources": "not_configured"
        },
    }


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
    """Accept a verification request and record its audit event."""
    request_id = str(uuid4())
    created_at = datetime.now(timezone.utc)

    audit_trail.record_request_accepted(
        request_id=request_id,
        details={
            "input_length": len(request.input_text),
            "verification_mode": request.verification_mode,
            "domain": request.domain,
        },
    )

    return VerifyResponse(
        request_id=request_id,
        created_at=created_at,
        status="accepted",
        input_text=request.input_text,
    )


@app.post("/api/v1/reports/{request_id}", status_code=201)
def create_report(
    request_id: str,
    request: ReportCreateRequest,
):
    """Generate and persist a report from supplied pipeline results."""
    try:
        report = generate_verification_report(
            claims=request.claims,
            risk_summary=request.risk_summary,
        )
        saved_report = report_store.save_report(request_id, report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (TypeError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return saved_report


@app.get("/api/v1/reports/{request_id}")
def retrieve_report(request_id: str):
    """Retrieve a previously saved verification report by request ID."""
    try:
        report = report_store.get_report(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Verification report not found",
        )

    return report
