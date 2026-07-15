from unittest.mock import patch

import pytest

from app.models.purchase_order import LineItem, PurchaseOrder
from app.services import rag_service
from app.services.rag_service import (
    check_payment_terms,
    check_spending,
    check_vendor,
    validate_math,
    validate_purchase_order,
)

CEYLON_VENDOR_HIT = {
    "text": (
        "vendor_id=VND-001, legal_name=Ceylon Industrial Bearings (Pvt) Ltd, "
        "aliases=Ceylon Industrial|Ceylon Bearings, status=approved"
    ),
    "source_doc": "approved_vendors.csv",
    "score": 0.92,
}

LAKPURA_VENDOR_HIT = {
    "text": (
        "vendor_id=VND-002, legal_name=Lakpura Logistics (Pvt) Ltd, "
        "aliases=Lakpura, status=approved"
    ),
    "source_doc": "approved_vendors.csv",
    "score": 0.88,
}

PAYMENT_POLICY_HIT = {
    "text": "# Auto-approve\nNet 15, Net 30\nMaximum payment terms for auto-approve: 30 days",
    "source_doc": "payment_policy.md",
    "score": 0.81,
}

APPROVAL_POLICY_HIT = {
    "text": "# Auto-approve\nSingle purchase order up to LKR 1,000,000 from an approved vendor",
    "source_doc": "approval_policy.md",
    "score": 0.79,
}


def make_po(**overrides) -> PurchaseOrder:
    defaults = {
        "vendor_name": "Ceylon Industrial Bearings (Pvt) Ltd",
        "po_number": "PO-4521-LK",
        "total_amount": 750_000.0,
        "payment_terms_days": 30,
        "subtotal": 625_000.0,
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


def test_validate_math_reconciled():
    po = make_po(subtotal=625_000.0)
    result = validate_math(po)
    assert result.total_reconciled is True
    assert result.line_items_sum == 625_000.0


def test_validate_math_mismatch():
    po = make_po(
        subtotal=330_000.0,
        line_items=[
            LineItem(
                description="Item A",
                quantity=1,
                unit_price=200_000.0,
                line_total=200_000.0,
            ),
            LineItem(
                description="Item B",
                quantity=1,
                unit_price=135_000.0,
                line_total=135_000.0,
            ),
        ],
    )
    result = validate_math(po)
    assert result.total_reconciled is False
    assert result.line_items_sum == 335_000.0
    assert result.declared_subtotal == 330_000.0


def test_check_vendor_approved():
    result = check_vendor(
        "Ceylon Industrial Bearings (Pvt) Ltd",
        [CEYLON_VENDOR_HIT],
    )
    assert result.status == "approved"
    assert result.vendor_id == "VND-001"
    assert result.source_doc == "approved_vendors.csv"


def test_check_vendor_unapproved():
    result = check_vendor("Serendib Heavy Parts Ltd", [CEYLON_VENDOR_HIT])
    assert result.status == "unapproved"


def test_check_payment_terms_approved():
    result = check_payment_terms(30, [PAYMENT_POLICY_HIT])
    assert result.status == "approved"
    assert result.extracted_terms_days == 30


def test_check_payment_terms_requires_review():
    result = check_payment_terms(60, [PAYMENT_POLICY_HIT])
    assert result.status == "requires_review"


def test_check_spending_auto_approve_eligible():
    result = check_spending(750_000.0, [APPROVAL_POLICY_HIT])
    assert result.status == "auto_approve_eligible"
    assert result.limit == 1_000_000.0


def test_check_spending_director_review():
    result = check_spending(14_775_000.0, [APPROVAL_POLICY_HIT])
    assert result.status == "director_review"


@patch("app.services.rag_service.search_qdrant")
def test_validate_purchase_order_ceylon(mock_search):
    mock_search.side_effect = [
        [CEYLON_VENDOR_HIT],
        [PAYMENT_POLICY_HIT],
        [APPROVAL_POLICY_HIT],
    ]

    rag = validate_purchase_order(make_po())

    assert rag.issues == []
    assert rag.vendor_check.status == "approved"
    assert rag.vendor_check.vendor_id == "VND-001"
    assert rag.payment_terms_check.status == "approved"
    assert rag.spending_check.status == "auto_approve_eligible"
    assert rag.math_validation.total_reconciled is True
    assert len(rag.rag_queries_used) == 3


@patch("app.services.rag_service.search_qdrant")
def test_validate_purchase_order_serendib(mock_search):
    mock_search.side_effect = [
        [CEYLON_VENDOR_HIT, LAKPURA_VENDOR_HIT],
        [PAYMENT_POLICY_HIT],
        [APPROVAL_POLICY_HIT],
    ]

    po = make_po(
        vendor_name="Serendib Heavy Parts Ltd",
        po_number="SHP-2026-044",
        total_amount=14_775_000.0,
        payment_terms_days=60,
        subtotal=14_775_000.0,
        line_items=[
            LineItem(
                description="Hydraulic pump",
                quantity=1,
                unit_price=14_775_000.0,
                line_total=14_775_000.0,
            )
        ],
    )
    rag = validate_purchase_order(po)

    assert "unknown_vendor" in rag.issues
    assert "payment_terms_exceed_policy" in rag.issues
    assert "amount_requires_review" in rag.issues
    assert rag.vendor_check.status == "unapproved"
    assert rag.spending_check.status == "director_review"


@patch("app.services.rag_service.search_qdrant")
def test_validate_purchase_order_lakpura(mock_search):
    mock_search.side_effect = [
        [LAKPURA_VENDOR_HIT],
        [PAYMENT_POLICY_HIT],
        [APPROVAL_POLICY_HIT],
    ]

    po = make_po(
        vendor_name="Lakpura Logistics (Pvt) Ltd",
        po_number=None,
        total_amount=390_000.0,
        payment_terms_days=None,
        subtotal=330_000.0,
        line_items=[
            LineItem(
                description="Item A",
                quantity=1,
                unit_price=200_000.0,
                line_total=200_000.0,
            ),
            LineItem(
                description="Item B",
                quantity=1,
                unit_price=135_000.0,
                line_total=135_000.0,
            ),
        ],
    )
    rag = validate_purchase_order(po)

    assert rag.vendor_check.status == "approved"
    assert rag.vendor_check.vendor_id == "VND-002"
    assert "payment_terms_missing" in rag.issues
    assert "subtotal_mismatch" in rag.issues
    assert rag.math_validation.total_reconciled is False


@pytest.mark.live
def test_validate_purchase_order_live_ceylon():
    """Requires: docker compose up -d qdrant && python scripts/seed_rag.py"""
    rag_service._qdrant_client.cache_clear()
    rag_service._openai_client.cache_clear()

    po = make_po()
    rag = validate_purchase_order(po)

    assert rag.vendor_check.status == "approved"
    assert rag.issues == []