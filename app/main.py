from contextlib import asynccontextmanager

from fastapi import FastAPI
from qdrant_client import QdrantClient
from sqlalchemy import text

from app.api.routes.jobs import router as jobs_router
from app.api.routes.process_order import router as process_order_router
from app.api.routes.review_queue import router as review_queue_router
from app.config import settings
from app.db.session import engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PO Compliance Agent",
    description="Purchase order intake, extraction, and compliance routing",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(process_order_router)
app.include_router(jobs_router)
app.include_router(review_queue_router)


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
