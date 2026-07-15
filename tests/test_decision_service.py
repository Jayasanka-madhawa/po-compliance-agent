import pytest

from app.models.decision import (
    DecisionType,
    JobStatus,
    PaymentTermsCheck,
    RagValidation,
    SpendingCheck,
    VendorCheck,
)
from app.models.purchase_order import LineItem, PurchaseOrder
from app.services.decision_service import route_decision

CEYLON_RAG = RagValidation(
    vendor_check=VendorCheck(
        status="approved",
        vendor_id="VND-001",
        matched_name="Ceylon Industrial Bearings (Pvt) Ltd",
        source_doc="approved_vendors.csv",
    ),
    payment_terms_check=PaymentTermsCheck(
        status="approved",
        extracted_terms_days=30,
        policy_max_auto_approve_days=30,
        source_doc="payment_policy.md",
    ),
    spending_check=SpendingCheck(
        status="auto_approve_eligible",
        total_amount=750_000.0,
        limit=1_000_000.0,
        source_doc="approval_policy.md",
    ),
    issues=[],
    overall_rag_confidence=0.95,
)

SERENDIB_RAG = RagValidation(
    vendor_check=VendorCheck(status="unapproved", source_doc="approved_vendors.csv"),
    payment_terms_check=PaymentTermsCheck(
        status="requires_review",
        extracted_terms_days=60,
        policy_max_auto_approve_days=30,
        source_doc="payment_policy.md",
    ),
    spending_check=SpendingCheck(
        status="director_review",
        total_amount=14_775_000.0,
        limit=5_000_000.0,
        source_doc="approval_policy.md",
    ),
    issues=[
        "unknown_vendor",
        "payment_terms_exceed_policy",
        "amount_requires_review",
    ],
    overall_rag_confidence=0.65,
)


def make_po(**overrides) -> PurchaseOrder:
    defaults = {
        "vendor_name": "Ceylon Industrial Bearings (Pvt) Ltd",
        "po_number": "PO-4521-LK",
        "total_amount": 750_000.0,
        "payment_terms_days": 30,
        "line_items": [
            LineItem(
                sku="BRG-220",
                description="Ball bearing 22 mm",
                quantity=500,
                unit_price=1250.0,
                line_total=625_000.0,
            )
        ],
        "extraction_confidence": 1.0,
    }
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


def test_route_ceylon_auto_accept():
    result = route_decision("job-1", make_po(), CEYLON_RAG)

    assert result.decision == DecisionType.AUTO_ACCEPT
    assert result.status == JobStatus.COMPLETED
    assert result.reasons == []
    assert result.confidence == 0.95
    assert "automatic acceptance" in (result.explanation or "").lower()


def test_route_serendib_human_review():
    po = make_po(
        vendor_name="Serendib Heavy Parts Ltd",
        po_number="SHP-2026-044",
        total_amount=14_775_000.0,
        payment_terms_days=60,
    )
    result = route_decision("job-2", po, SERENDIB_RAG)

    assert result.decision == DecisionType.HUMAN_REVIEW
    assert len(result.reasons) == 3
    assert any("vendor" in reason.lower() for reason in result.reasons)
    assert any("payment terms" in reason.lower() for reason in result.reasons)
    assert any("amount" in reason.lower() for reason in result.reasons)


def test_route_low_confidence_human_review():
    po = make_po(extraction_confidence=0.6)
    result = route_decision("job-3", po, CEYLON_RAG)

    assert result.decision == DecisionType.HUMAN_REVIEW
    assert any("confidence" in reason.lower() for reason in result.reasons)


def test_route_missing_fields_human_review():
    po = make_po(po_number=None, fields_missing=["po_number"])
    rag = RagValidation(
        issues=["payment_terms_missing", "subtotal_mismatch"],
        overall_rag_confidence=0.85,
    )
    result = route_decision("job-4", po, rag)

    assert result.decision == DecisionType.HUMAN_REVIEW
    assert any("po_number" in reason for reason in result.reasons)
    assert any("payment terms" in reason.lower() for reason in result.reasons)


def test_confidence_out_of_range_raises():
    with pytest.raises(Exception):
        route_decision(
            "job-5",
            make_po(extraction_confidence=1.5),
            CEYLON_RAG,
        )
