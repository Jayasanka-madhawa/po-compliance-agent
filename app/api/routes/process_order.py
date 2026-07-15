import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.decision import DecisionType, JobStatus
from app.models.process_order_response import ProcessOrderResponse
from app.services import database_service
from app.services.processing_pipeline import process_order_file

router = APIRouter(tags=["orders"])

ALLOWED_EXTENSIONS = {".pdf", ".csv", ".png", ".jpg", ".jpeg", ".webp"}


@router.post("/process-order", response_model=ProcessOrderResponse)
async def process_order(
    file: UploadFile = File(...),
    sender: str | None = Form(default=None),
    subject: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        job_id, extraction = process_order_file(tmp_path)

        response = ProcessOrderResponse(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            decision=DecisionType.PENDING_ROUTING,
            extraction=extraction,
            message="Extraction complete. Routing will be added in a later step.",
        )
        database_service.save_job(
            db,
            response,
            filename=file.filename,
            sender=sender,
            subject=subject,
        )
        return response

    except ValueError as exc:
        response = ProcessOrderResponse(
            job_id=str(uuid.uuid4()),
            status=JobStatus.FAILED,
            decision=DecisionType.PROCESSING_FAILED,
            error=str(exc),
            message="Could not process the attachment.",
        )
        database_service.save_job(
            db,
            response,
            filename=file.filename,
            sender=sender,
            subject=subject,
        )
        return response

    except Exception as exc:
        response = ProcessOrderResponse(
            job_id=str(uuid.uuid4()),
            status=JobStatus.FAILED,
            decision=DecisionType.PROCESSING_FAILED,
            error=str(exc),
            message="Unexpected error during processing.",
        )
        database_service.save_job(
            db,
            response,
            filename=file.filename,
            sender=sender,
            subject=subject,
        )
        return response

    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
