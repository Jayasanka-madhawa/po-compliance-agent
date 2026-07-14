"""Usage: python scripts/extract_sample.py sample_documents/po_clean_ceylon_industrial.pdf"""
import json
import sys
from pathlib import Path

# Correct (points to project root)
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app.services.document_parser import parse_document
from app.services.extraction_service import extract_purchase_order


def main() -> None:
    path = Path(sys.argv[1])
    parsed = parse_document(path)
    po = extract_purchase_order(parsed)
    print(json.dumps(po.model_dump(), indent=2))


if __name__ == "__main__":
    main()