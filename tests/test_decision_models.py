import pytest
from pydantic import ValidationError

from app.models.decision import (
    DecisionType,
    JobStatus,
    ProcessingResult,
    RagValidation,
    VendorCheck,
)
from app.models.purchase_order import LineItem, PurchaseOrder


def test_decision_type_values():
    assert DecisionType.AUTO_ACCEPT.value == "AUTO_ACCEPT"
    assert DecisionType.HUMAN_REVIEW.value == "HUMAN_REVIEW"
    assert DecisionType.PROCESSING_FAILED.value == "PROCESSING_FAILED"
    assert DecisionType.PENDING_ROUTING.value == "PENDING_ROUTING"


def test_processing_result_minimal_failed():
    result = ProcessingResult(
        job_id="job-1",
        status=JobStatus.FAILED,
        decision=DecisionType.PROCESSING_FAILED,
        error="Unsupported file",
    )
    assert result.extraction is None
    assert result.decision == DecisionType.PROCESSING_FAILED


def test_processing_result_with_rag():
    po = PurchaseOrder(
        vendor_name="Ceylon Industrial Bearings (Pvt) Ltd",
        po_number="PO-4521-LK",
        total_amount=750_000.0,
        line_items=[
            LineItem(
                description="Ball bearing 22 mm",
                quantity=500,
                unit_price=1250.0,
                line_total=625_000.0,
            )
        ],
        extraction_confidence=1.0,
    )
    result = ProcessingResult(
        job_id="job-2",
        status=JobStatus.COMPLETED,
        decision=DecisionType.AUTO_ACCEPT,
        confidence=0.95,
        extraction=po,
        rag_validation=RagValidation(
            vendor_check=VendorCheck(
                status="approved",
                vendor_id="VND-001",
                matched_name="Ceylon Industrial Bearings (Pvt) Ltd",
                source_doc="approved_vendors.csv",
            ),
            overall_rag_confidence=0.93,
        ),
        reasons=[],
        explanation="Vendor approved and totals reconcile.",
    )
    assert result.rag_validation.vendor_check.vendor_id == "VND-001"


def test_confidence_out_of_range_raises():
    with pytest.raises(ValidationError):
        ProcessingResult(
            job_id="job-3",
            status=JobStatus.COMPLETED,
            decision=DecisionType.HUMAN_REVIEW,
            confidence=1.5,
        )
