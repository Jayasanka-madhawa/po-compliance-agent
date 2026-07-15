from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.process_order_response import ProcessOrderResponse
from app.models.review import ReviewDecisionRequest
from app.services import database_service

router = APIRouter(tags=["review"])


@router.get("/review-queue", response_model=list[ProcessOrderResponse])
def get_review_queue(
    limit: int = 20,
    vendor: str | None = None,
    db: Session = Depends(get_db),
):
    records = database_service.list_review_queue(db, limit=limit, vendor=vendor)
    return [database_service.job_to_response(record) for record in records]


@router.patch("/jobs/{job_id}/review", response_model=ProcessOrderResponse)
def review_job(
    job_id: str,
    body: ReviewDecisionRequest,
    db: Session = Depends(get_db),
):
    try:
        record = database_service.apply_review(
            db,
            job_id,
            action=body.action,
            reviewer=body.reviewer,
            note=body.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return database_service.job_to_response(record)
