from audit_trail import AuditTrail
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from evidence_adapters import (
    EvidenceSource,
    EvidenceSourceUnavailableError,
    UnavailableEvidenceAdapter,
)


app = FastAPI(
    title="Dehallucination API",
    description="API foundation for the Dehallucination project",
    version="0.1.0",
)

# No real external evidence source is configured by default.
# Tests or future configuration can supply a different adapter.
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
    """Retrieve evidence through the configured evidence adapter."""
    try:
        results = evidence_source.retrieve(request.query)
    except EvidenceSourceUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return EvidenceRetrieveResponse(
        query=request.query,
        evidence=results,
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
