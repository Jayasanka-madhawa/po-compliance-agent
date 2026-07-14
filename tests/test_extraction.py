import os
from pathlib import Path

import pytest

from app.services.document_parser import parse_document
from app.services.extraction_service import extract_purchase_order

SAMPLES = Path(__file__).resolve().parent.parent / "sample_documents"

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY required for live extraction tests",
)


@pytest.mark.live
def test_extract_clean_ceylon_pdf():
    parsed = parse_document(SAMPLES / "po_clean_ceylon_industrial.pdf")
    po = extract_purchase_order(parsed)

    assert "Ceylon Industrial" in po.vendor_name
    assert po.po_number == "PO-4521-LK"
    assert po.total_amount == 750_000.0
    assert po.payment_terms_days == 30
    assert len(po.line_items) >= 1
    assert po.extraction_confidence >= 0.75
    assert "po_number" not in po.fields_missing


@pytest.mark.live
def test_extract_messy_serendib_pdf():
    parsed = parse_document(SAMPLES / "po_messy_serendib_parts.pdf")
    po = extract_purchase_order(parsed)

    assert "Serendib" in po.vendor_name
    assert po.po_number == "SHP-2026-044"
    assert po.total_amount == 14_775_000.0
    assert po.payment_terms_days == 60
    assert po.extraction_confidence >= 0.7


@pytest.mark.live
def test_extract_partial_lakpura_csv():
    parsed = parse_document(SAMPLES / "po_partial_lakpura.csv")
    po = extract_purchase_order(parsed)

    assert "Lakpura" in po.vendor_name
    assert po.po_number is None or po.po_number == ""
    assert "po_number" in po.fields_missing
    assert len(po.line_items) >= 2
    # Declared subtotal 330000 but lines sum to 335000 — LLM may flag ambiguity
    assert po.total_amount == 390_000.0