import tempfile
import uuid
from pathlib import Path

from app.models.purchase_order import PurchaseOrder
from app.services.document_parser import parse_document
from app.services.extraction_service import extract_purchase_order


def process_order_file(file_path: Path) -> tuple[str, PurchaseOrder]:
    job_id = str(uuid.uuid4())
    parsed = parse_document(file_path)
    extraction = extract_purchase_order(parsed)
    return job_id, extraction