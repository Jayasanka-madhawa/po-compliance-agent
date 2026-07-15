from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.decision import DecisionType, JobStatus
from app.models.purchase_order import LineItem, PurchaseOrder

client = TestClient(app)
SAMPLES = Path(__file__).resolve().parent.parent / "sample_documents"

MOCK_PO = PurchaseOrder(
    vendor_name="Ceylon Industrial Bearings (Pvt) Ltd",
    po_number="PO-4521-LK",
    total_amount=750_000.0,
    line_items=[
        LineItem(
            sku="BRG-220",
            description="Ball bearing 22 mm",
            quantity=500,
            unit_price=1250.0,
            line_total=625_000.0,
        )
    ],
    extraction_confidence=1.0,
)


@patch("app.api.routes.process_order.process_order_file")
def test_process_order_returns_extraction(mock_process):
    mock_process.return_value = ("job-test-123", MOCK_PO)

    with open(SAMPLES / "po_clean_ceylon_industrial.pdf", "rb") as f:
        response = client.post(
            "/process-order",
            files={"file": ("po_clean_ceylon_industrial.pdf", f, "application/pdf")},
            data={"sender": "vendor@test.com", "subject": "PO test"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == JobStatus.COMPLETED.value
    assert body["decision"] == DecisionType.PENDING_ROUTING.value
    assert body["extraction"]["po_number"] == "PO-4521-LK"
    assert body["job_id"] == "job-test-123"


def test_process_order_rejects_unsupported_file():
    response = client.post(
        "/process-order",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400