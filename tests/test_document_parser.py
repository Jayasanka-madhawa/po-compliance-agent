from pathlib import Path

import pytest

from app.services.document_parser import DocumentType, parse_document

SAMPLES = Path(__file__).resolve().parent.parent / "sample_documents"


@pytest.mark.parametrize(
    "filename,expected_type,expected_snippets",
    [
        (
            "po_clean_ceylon_industrial.pdf",
            DocumentType.PDF_TEXT,
            ["PO-4521-LK", "Ceylon Industrial Bearings", "750,000.00"],
        ),
        (
            "po_messy_serendib_parts.pdf",
            DocumentType.PDF_TEXT,
            ["Serendib Heavy Parts", "SHP-2026-044", "14,775,000"],
        ),
        (
            "po_partial_lakpura.csv",
            DocumentType.CSV,
            ["Lakpura Logistics", "320000.00"],
        ),
    ],
)
def test_parse_real_sample_files(filename, expected_type, expected_snippets):
    path = SAMPLES / filename
    assert path.exists(), f"Missing sample file: {path}"

    parsed = parse_document(path)

    assert parsed.document_type == expected_type
    assert parsed.text.strip()

    for snippet in expected_snippets:
        assert snippet in parsed.text, f"Expected '{snippet}' in parsed text"