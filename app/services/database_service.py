from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import JobRecord
from app.models.decision import DecisionType, JobStatus, RagValidation
from app.models.process_order_response import ProcessOrderResponse
from app.models.purchase_order import PurchaseOrder
from app.models.review import ReviewAction


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
        rag_validation_json=(
            response.rag_validation.model_dump(mode="json")
            if response.rag_validation
            else None
        ),
        reasons_json=response.reasons or None,
        confidence=response.confidence,
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


def list_review_queue(
    db: Session,
    *,
    limit: int = 20,
    vendor: str | None = None,
) -> list[JobRecord]:
    records = (
        db.query(JobRecord)
        .filter(JobRecord.decision == DecisionType.HUMAN_REVIEW.value)
        .order_by(JobRecord.created_at.desc())
        .limit(limit if vendor is None else limit * 10)
        .all()
    )

    if vendor is None:
        return records

    vendor_lower = vendor.lower()
    filtered = [
        record
        for record in records
        if record.extraction_json
        and vendor_lower
        in record.extraction_json.get("vendor_name", "").lower()
    ]
    return filtered[:limit]


def apply_review(
    db: Session,
    job_id: str,
    *,
    action: ReviewAction,
    reviewer: str,
    note: str | None = None,
) -> JobRecord:
    record = get_job(db, job_id)
    if record is None:
        raise LookupError(f"Job not found: {job_id}")

    if record.decision != DecisionType.HUMAN_REVIEW.value:
        raise ValueError("Job is not pending human review")

    record.reviewer = reviewer
    record.review_note = note
    record.reviewed_at = datetime.now(UTC)

    if action == ReviewAction.APPROVE:
        record.decision = DecisionType.AUTO_ACCEPT.value
        record.message = f"Manually approved by {reviewer}"
    else:
        record.decision = DecisionType.REJECTED.value
        record.message = f"Rejected by {reviewer}"

    db.commit()
    db.refresh(record)
    return record


def job_to_response(record: JobRecord) -> ProcessOrderResponse:
    extraction = None
    if record.extraction_json:
        extraction = PurchaseOrder.model_validate(record.extraction_json)

    rag_validation = None
    if record.rag_validation_json:
        rag_validation = RagValidation.model_validate(record.rag_validation_json)

    return ProcessOrderResponse(
        job_id=record.id,
        status=JobStatus(record.status),
        decision=DecisionType(record.decision),
        confidence=record.confidence,
        extraction=extraction,
        rag_validation=rag_validation,
        reasons=record.reasons_json or [],
        explanation=None,
        reviewer=record.reviewer,
        review_note=record.review_note,
        reviewed_at=record.reviewed_at,
        error=record.error,
        message=record.message,
    )
