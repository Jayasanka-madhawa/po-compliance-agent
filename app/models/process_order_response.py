from datetime import datetime

from pydantic import BaseModel, Field

from app.models.decision import DecisionType, JobStatus, RagValidation
from app.models.purchase_order import PurchaseOrder


class ProcessOrderResponse(BaseModel):
    job_id: str
    status: JobStatus
    decision: DecisionType
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction: PurchaseOrder | None = None
    rag_validation: RagValidation | None = None
    reasons: list[str] = Field(default_factory=list)
    explanation: str | None = None
    reviewer: str | None = None
    review_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime | None = None
    error: str | None = None
    message: str | None = None
