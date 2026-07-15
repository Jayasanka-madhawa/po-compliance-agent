from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.process_order_response import ProcessOrderResponse
from app.services import database_service

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=ProcessOrderResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    record = database_service.get_job(db, job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return database_service.job_to_response(record)


@router.get("/jobs", response_model=list[ProcessOrderResponse])
def list_jobs(limit: int = 20, db: Session = Depends(get_db)):
    records = database_service.list_jobs(db, limit=limit)
    return [database_service.job_to_response(record) for record in records]
