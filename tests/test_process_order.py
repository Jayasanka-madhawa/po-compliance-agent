from pathlib import Path
from unittest.mock import patch

from app.models.decision import (
    DecisionType,
    JobStatus,
    ProcessingResult,
    RagValidation,
    VendorCheck,
)
from app.models.purchase_order import LineItem, PurchaseOrder

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

MOCK_RESULT = ProcessingResult(
    job_id="job-test-123",
    status=JobStatus.COMPLETED,
    decision=DecisionType.AUTO_ACCEPT,
    confidence=0.95,
    extraction=MOCK_PO,
    rag_validation=RagValidation(
        vendor_check=VendorCheck(
            status="approved",
            vendor_id="VND-001",
            source_doc="approved_vendors.csv",
        ),
        issues=[],
        overall_rag_confidence=0.95,
    ),
    reasons=[],
    explanation="Purchase order meets all compliance checks.",
    message="Processing complete.",
)


@patch("app.api.routes.process_order.process_order_file")
def test_process_order_returns_routed_decision(mock_process, client):
    mock_process.return_value = MOCK_RESULT

    with open(SAMPLES / "po_clean_ceylon_industrial.pdf", "rb") as f:
        response = client.post(
            "/process-order",
            files={"file": ("po_clean_ceylon_industrial.pdf", f, "application/pdf")},
            data={"sender": "vendor@test.com", "subject": "PO test"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == JobStatus.COMPLETED.value
    assert body["decision"] == DecisionType.AUTO_ACCEPT.value
    assert body["confidence"] == 0.95
    assert body["extraction"]["po_number"] == "PO-4521-LK"
    assert body["rag_validation"]["vendor_check"]["vendor_id"] == "VND-001"
    assert body["job_id"] == "job-test-123"

    job_response = client.get("/jobs/job-test-123")
    assert job_response.status_code == 200
    job_body = job_response.json()
    assert job_body["decision"] == DecisionType.AUTO_ACCEPT.value
    assert job_body["extraction"]["po_number"] == "PO-4521-LK"
    assert job_body["rag_validation"]["issues"] == []


def test_process_order_rejects_unsupported_file(client):
    response = client.post(
        "/process-order",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_get_job_not_found(client):
    response = client.get("/jobs/does-not-exist")
    assert response.status_code == 404
