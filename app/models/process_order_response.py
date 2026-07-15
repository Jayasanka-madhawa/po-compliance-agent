from pydantic import BaseModel

from app.models.decision import DecisionType, JobStatus
from app.models.purchase_order import PurchaseOrder


class ProcessOrderResponse(BaseModel):
    job_id: str
    status: JobStatus
    decision: DecisionType
    extraction: PurchaseOrder | None = None
    error: str | None = None
    message: str | None = None
