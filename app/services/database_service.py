from sqlalchemy.orm import Session

from app.db.models import JobRecord
from app.models.decision import DecisionType, JobStatus
from app.models.process_order_response import ProcessOrderResponse
from app.models.purchase_order import PurchaseOrder


def save_job(
    db: Session,
    response: ProcessOrderResponse,
    *,
    filename: str | None = None,
    sender: str | None = None,
    subject: str | None = None,
) -> JobRecord:
    record = JobRecord(
        id=response.job_id,
        status=response.status.value,
        decision=response.decision.value,
        filename=filename,
        sender=sender,
        subject=subject,
        extraction_json=(
            response.extraction.model_dump(mode="json") if response.extraction else None
        ),
        error=response.error,
        message=response.message,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_job(db: Session, job_id: str) -> JobRecord | None:
    return db.get(JobRecord, job_id)


def list_jobs(db: Session, limit: int = 20) -> list[JobRecord]:
    return (
        db.query(JobRecord)
        .order_by(JobRecord.created_at.desc())
        .limit(limit)
        .all()
    )


def job_to_response(record: JobRecord) -> ProcessOrderResponse:
    extraction = None
    if record.extraction_json:
        extraction = PurchaseOrder.model_validate(record.extraction_json)

    return ProcessOrderResponse(
        job_id=record.id,
        status=JobStatus(record.status),
        decision=DecisionType(record.decision),
        extraction=extraction,
        error=record.error,
        message=record.message,
    )
