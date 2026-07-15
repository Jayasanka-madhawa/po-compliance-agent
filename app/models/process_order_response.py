from pydantic import BaseModel, Field

from app.models.purchase_order import PurchaseOrder


class ProcessOrderResponse(BaseModel):
    job_id: str
    status: str  # "completed" | "failed"
    decision: str  # stub until step 7: "PENDING_ROUTING" | "PROCESSING_FAILED"
    extraction: PurchaseOrder | None = None
    error: str | None = None
    message: str | None = None