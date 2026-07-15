import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.models.process_order_response import ProcessOrderResponse
from app.services.processing_pipeline import process_order_file

router = APIRouter(tags=["orders"])

ALLOWED_EXTENSIONS = {".pdf", ".csv", ".png", ".jpg", ".jpeg", ".webp"}


@router.post("/process-order", response_model=ProcessOrderResponse)
async def process_order(
    file: UploadFile = File(...),
    sender: str | None = Form(default=None),
    subject: str | None = Form(default=None),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        job_id, extraction = process_order_file(tmp_path)

        return ProcessOrderResponse(
            job_id=job_id,
            status="completed",
            decision="PENDING_ROUTING",
            extraction=extraction,
            message="Extraction complete. Routing will be added in a later step.",
        )

    except ValueError as exc:
        return ProcessOrderResponse(
            job_id=str(__import__("uuid").uuid4()),
            status="failed",
            decision="PROCESSING_FAILED",
            error=str(exc),
            message="Could not process the attachment.",
        )

    except Exception as exc:
        return ProcessOrderResponse(
            job_id=str(__import__("uuid").uuid4()),
            status="failed",
            decision="PROCESSING_FAILED",
            error=str(exc),
            message="Unexpected error during processing.",
        )

    finally:
        if "tmp_path" in locals() and tmp_path.exists():
            tmp_path.unlink()