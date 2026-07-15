from enum import Enum

from pydantic import BaseModel, Field

from app.models.purchase_order import PurchaseOrder


class DecisionType(str, Enum):
    AUTO_ACCEPT = "AUTO_ACCEPT"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    REJECTED = "REJECTED"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    PENDING_ROUTING = "PENDING_ROUTING"


class JobStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class VendorCheck(BaseModel):
    status: str
    vendor_id: str | None = None
    matched_name: str | None = None
    match_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_doc: str | None = None


class PaymentTermsCheck(BaseModel):
    status: str
    extracted_terms_days: int | None = None
    policy_max_auto_approve_days: int | None = None
    source_doc: str | None = None


class SpendingCheck(BaseModel):
    status: str
    total_amount: float | None = None
    limit: float | None = None
    source_doc: str | None = None


class MathValidation(BaseModel):
    line_items_sum: float | None = None
    declared_subtotal: float | None = None
    total_reconciled: bool
    variance_pct: float | None = None


class RagValidation(BaseModel):
    vendor_check: VendorCheck | None = None
    payment_terms_check: PaymentTermsCheck | None = None
    spending_check: SpendingCheck | None = None
    math_validation: MathValidation | None = None
    rag_queries_used: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    overall_rag_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ProcessingResult(BaseModel):
    job_id: str
    status: JobStatus
    decision: DecisionType
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction: PurchaseOrder | None = None
    rag_validation: RagValidation | None = None
    reasons: list[str] = Field(default_factory=list)
    explanation: str | None = None
    error: str | None = None
    message: str | None = None
