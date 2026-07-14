import json
from pathlib import Path

from openai import OpenAI

from app.config import settings
from app.models.purchase_order import PurchaseOrder
from app.services.document_parser import DocumentType, ParsedDocument

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "extraction.txt"

SCHEMA = {
    "type": "object",
    "properties": {
        "vendor_name": {"type": "string"},
        "po_number": {"type": ["string", "null"]},
        "po_date": {"type": ["string", "null"]},
        "buyer_name": {"type": ["string", "null"]},
        "currency": {"type": "string"},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sku": {"type": ["string", "null"]},
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "line_total": {"type": "number"},
                },
                "required": [
                    "sku",
                    "description",
                    "quantity",
                    "unit_price",
                    "line_total",
                ],
                "additionalProperties": False,
            },
        },
        "subtotal": {"type": ["number", "null"]},
        "tax": {"type": ["number", "null"]},
        "shipping": {"type": ["number", "null"]},
        "total_amount": {"type": "number"},
        "payment_terms": {"type": ["string", "null"]},
        "payment_terms_days": {"type": ["integer", "null"]},
        "delivery_date": {"type": ["string", "null"]},
        "notes": {"type": ["string", "null"]},
        "extraction_confidence": {"type": "number"},
        "fields_missing": {"type": "array", "items": {"type": "string"}},
        "ambiguities": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "vendor_name",
        "po_number",
        "po_date",
        "buyer_name",
        "currency",
        "line_items",
        "subtotal",
        "tax",
        "shipping",
        "total_amount",
        "payment_terms",
        "payment_terms_days",
        "delivery_date",
        "notes",
        "extraction_confidence",
        "fields_missing",
        "ambiguities",
    ],
    "additionalProperties": False,
}


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def extract_purchase_order(parsed: ParsedDocument) -> PurchaseOrder:
    if parsed.document_type == DocumentType.IMAGE:
        raise ValueError("Image documents require vision extraction (not implemented yet)")
    if parsed.document_type == DocumentType.PDF_SCANNED:
        raise ValueError("Scanned PDFs require vision extraction (not implemented yet)")
    if not parsed.text.strip():
        raise ValueError(f"No extractable text in {parsed.file_name}")

    client = OpenAI(api_key=settings.openai_api_key)

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _load_prompt()},
            {
                "role": "user",
                "content": (
                    f"File: {parsed.file_name}\n"
                    f"Document type: {parsed.document_type.value}\n\n"
                    f"Document text:\n{parsed.text}"
                ),
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "purchase_order",
                "strict": True,
                "schema": SCHEMA,
            },
        },
        temperature=0,
    )

    raw = response.choices[0].message.content
    if not raw:
        raise ValueError("Empty response from OpenAI")

    data = json.loads(raw)
    return PurchaseOrder.model_validate(data)