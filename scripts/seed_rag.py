"""Seed Qdrant with knowledge-base chunks.

Usage (from project root):
  docker compose up -d qdrant
  source .venv/bin/activate
  python scripts/seed_rag.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from uuid import uuid4

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402

KB_DIR = ROOT / "knowledge_base"
EMBEDDING_DIM = 1536  # text-embedding-3-small


def chunk_csv(path: Path) -> list[dict]:
    chunks: list[dict] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            text = (
                f"vendor_id={row['vendor_id']}, "
                f"legal_name={row['legal_name']}, "
                f"aliases={row['aliases']}, "
                f"status={row['status']}"
            )
            chunks.append({"text": text, "source_doc": path.name})
    return chunks


def chunk_markdown(path: Path) -> list[dict]:
    chunks: list[dict] = []
    current_title = path.stem
    current_lines: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            if current_lines:
                chunks.append(
                    {
                        "text": f"# {current_title}\n" + "\n".join(current_lines),
                        "source_doc": path.name,
                    }
                )
                current_lines = []
            current_title = line[3:].strip()
            continue
        if line:
            current_lines.append(line)

    if current_lines:
        chunks.append(
            {
                "text": f"# {current_title}\n" + "\n".join(current_lines),
                "source_doc": path.name,
            }
        )

    return chunks


def load_chunks() -> list[dict]:
    chunks: list[dict] = []
    chunks.extend(chunk_csv(KB_DIR / "approved_vendors.csv"))
    for path in sorted(KB_DIR.glob("*.md")):
        chunks.extend(chunk_markdown(path))
    return chunks


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
    )
    return [item.embedding for item in response.data]


def ensure_collection(qdrant: QdrantClient, collection_name: str) -> None:
    if qdrant.collection_exists(collection_name):
        qdrant.delete_collection(collection_name)
    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )


def main() -> None:
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is required to seed embeddings.")

    chunks = load_chunks()
    if not chunks:
        raise SystemExit("No knowledge-base chunks found.")

    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    openai = OpenAI(api_key=settings.openai_api_key)

    vectors = embed_texts(openai, [chunk["text"] for chunk in chunks])

    ensure_collection(qdrant, settings.qdrant_collection)

    points = [
        PointStruct(
            id=str(uuid4()),
            vector=vector,
            payload={
                "text": chunk["text"],
                "source_doc": chunk["source_doc"],
            },
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]

    qdrant.upsert(collection_name=settings.qdrant_collection, points=points)
    print(f"Seeded {len(points)} chunks into '{settings.qdrant_collection}'.")


if __name__ == "__main__":
    main()