import uuid
from pathlib import Path

from app.models.decision import ProcessingResult
from app.services.decision_service import route_decision
from app.services.document_parser import parse_document
from app.services.extraction_service import extract_purchase_order
from app.services.rag_service import validate_purchase_order


def process_order_file(file_path: Path) -> ProcessingResult:
    job_id = str(uuid.uuid4())
    parsed = parse_document(file_path)
    extraction = extract_purchase_order(parsed)
    rag_validation = validate_purchase_order(extraction)
    return route_decision(job_id, extraction, rag_validation)
