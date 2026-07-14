from fastapi import FastAPI
from qdrant_client import QdrantClient
from sqlalchemy import create_engine, text

from app.config import settings

app = FastAPI(
    title="PO Compliance Agent",
    description="Purchase order intake, extraction, and compliance routing",
    version="0.1.0",
)

engine = create_engine(settings.database_url)


@app.get("/health")
def health():
    postgres_ok = False
    qdrant_ok = False

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception:
        pass

    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        client.get_collections()
        qdrant_ok = True
    except Exception:
        pass

    all_ok = postgres_ok and qdrant_ok

    return {
        "status": "ok" if all_ok else "degraded",
        "postgres": "connected" if postgres_ok else "unavailable",
        "qdrant": "connected" if qdrant_ok else "unavailable",
    }