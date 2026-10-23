from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator


app = FastAPI(
    title="Dehallucination API",
    description="API foundation for the Dehallucination project",
    version="0.1.0",
)


@app.get("/api/v1/health")
def health_check():
    """Report the API's health and configured dependency status."""
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


@app.post("/api/v1/verify", response_model=VerifyResponse, status_code=202)
def verify_request(request: VerifyRequest):
    return VerifyResponse(
        request_id=str(uuid4()),
        created_at=datetime.now(timezone.utc),
        status="accepted",
        input_text=request.input_text,
    )
