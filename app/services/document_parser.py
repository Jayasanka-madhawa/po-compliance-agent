from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import csv

import fitz  # PyMuPDF


class DocumentType(str, Enum):
    PDF_TEXT = "pdf_text"
    PDF_SCANNED = "pdf_scanned"
    CSV = "csv"
    IMAGE = "image"
    UNSUPPORTED = "unsupported"


@dataclass
class ParsedDocument:
    document_type: DocumentType
    text: str
    file_name: str
    page_count: int | None = None


MIN_TEXT_CHARS = 80  # below this → treat as scanned PDF


def parse_document(file_path: Path) -> ParsedDocument:
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        return _parse_csv(file_path)
    if suffix == ".pdf":
        return _parse_pdf(file_path)
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return ParsedDocument(
            document_type=DocumentType.IMAGE,
            text="",
            file_name=file_path.name,
        )

    raise ValueError(f"Unsupported file type: {suffix}")


def _parse_csv(file_path: Path) -> ParsedDocument:
    rows = []
    with file_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(",".join(row))
    return ParsedDocument(
        document_type=DocumentType.CSV,
        text="\n".join(rows),
        file_name=file_path.name,
    )


def _parse_pdf(file_path: Path) -> ParsedDocument:
    doc = fitz.open(file_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text("text"))
    full_text = "\n".join(text_parts).strip()
    page_count = doc.page_count
    doc.close()

    doc_type = (
        DocumentType.PDF_TEXT
        if len(full_text) >= MIN_TEXT_CHARS
        else DocumentType.PDF_SCANNED
    )

    return ParsedDocument(
        document_type=doc_type,
        text=full_text,
        file_name=file_path.name,
        page_count=page_count,
    )