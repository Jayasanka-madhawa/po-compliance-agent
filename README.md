# PO Compliance Agent

This project is a **Purchase Order Compliance Agent**.

A company called **Lanka Precision Manufacturing** receives purchase orders from vendors — usually as **PDF or CSV files**, often by **email**.

Instead of a person reading every PO by hand, this system:

1. **Reads** the file  
2. **Pulls out** vendor name, PO number, amounts, line items  
3. **Checks** it against company rules  
4. **Decides**: auto-accept, or send to a human for review  

Under the hood: OpenAI for extraction, Qdrant for policy lookup (RAG), PostgreSQL for job storage, n8n for email intake, and Streamlit for the review UI.

Built for the Flat Rock Technology Agentic AI Engineer test task.

**Demo video:** [Loom recording](#) *(add link after recording)*

**Repository:** https://github.com/Jayasanka-madhawa/po-compliance-agent

---

## Architecture

```
┌─────────────┐     ┌──────┐     ┌─────────────────────┐     ┌────────┐
│ Gmail       │────▶│ n8n  │────▶│ FastAPI             │────▶│ Qdrant │
│             │     │      │     │ OpenAI extraction   │     │ (RAG)  │
│             │     └──────┘     │ + routing rules     │     └────────┘
└─────────────┘                  └──────────┬──────────┘
                                            │
                                            ▼
                                     ┌─────────────┐
                                     │ PostgreSQL  │
                                     │ (jobs)      │
                                     └──────┬──────┘
                                            │
                                            ▼
                                     ┌─────────────┐
                                     │ Streamlit   │
                                     │ review UI   │
                                     └─────────────┘
```

| Layer | Technology | Role |
|-------|------------|------|
| Orchestration | n8n | Gmail trigger, forward attachment to API, branch on decision |
| Backend | FastAPI + Python | Parse, extract, RAG validate, route, persist |
| LLM | OpenAI (`gpt-4o`) | Structured JSON extraction |
| Embeddings | OpenAI (`text-embedding-3-small`) | Policy chunk vectors |
| Vector DB | Qdrant | RAG knowledge base |
| Database | PostgreSQL | Job history, review queue |
| UI | Streamlit | Review queue, job history, manual upload, policies |

Business logic lives in FastAPI. n8n handles email intake and notifications only.

---

## Decision types

| Decision | Meaning |
|----------|---------|
| `AUTO_ACCEPT` | All policy checks passed; extraction confidence ≥ 75% |
| `HUMAN_REVIEW` | Flagged — vendor, payment terms, spending, missing fields, math mismatch, or low confidence |
| `MANUALLY_APPROVED` | Human approved a flagged PO in the review UI |
| `REJECTED` | Human rejected a flagged PO |
| `PROCESSING_FAILED` | Could not parse or extract the document (e.g. scanned PDF, image, API error) |

---

## Sample documents

Three demo files in `sample_documents/`:

| File | Expected decision | Why |
|------|-------------------|-----|
| `po_clean_ceylon_industrial.pdf` | `AUTO_ACCEPT` | Approved vendor, Net 30, under LKR 1M |
| `po_messy_serendib_parts.pdf` | `HUMAN_REVIEW` | Unapproved vendor, Net 60, LKR 14.7M (director review) |
| `po_partial_lakpura.csv` | `HUMAN_REVIEW` | Approved vendor but missing fields / subtotal mismatch |

---

## Prerequisites

- Docker & Docker Compose
- OpenAI API key
- Python 3.11+ (for local tests and seeding RAG from the host)

---

## Quick start

```bash
git clone https://github.com/Jayasanka-madhawa/po-compliance-agent.git
cd po-compliance-agent
cp env.example .env
# Edit .env — set OPENAI_API_KEY=sk-...

docker compose up -d --build
```

Seed the Qdrant knowledge base (from the host, with Qdrant exposed on port 6333):

```bash
pip install -r requirements.txt   # if not using Docker for scripts
QDRANT_HOST=localhost python scripts/seed_rag.py
```

Expected output: `Seeded 41 chunks into 'po_policies'.`

### URLs

| Service | URL |
|---------|-----|
| Streamlit UI | http://localhost:8502 |
| API docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |
| n8n | http://localhost:5678 |
| Qdrant | http://localhost:6333 |

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Postgres + Qdrant connectivity |
| `POST` | `/process-order` | Upload PO file (`multipart/form-data`: `file`, optional `sender`, `subject`) |
| `GET` | `/jobs/{job_id}` | Get job by ID |
| `GET` | `/jobs?limit=20` | List recent jobs (newest first) |
| `GET` | `/review-queue?limit=50` | List jobs with `HUMAN_REVIEW` decision |
| `PATCH` | `/jobs/{job_id}/review` | Approve or reject (`{"action": "approve"\|"reject", "reviewer": "...", "note": "..."}`) |

Example:

```bash
curl -X POST http://localhost:8000/process-order \
  -F "file=@sample_documents/po_clean_ceylon_industrial.pdf" \
  -F "sender=vendor@test.com" \
  -F "subject=PO submission"
```

---

## Knowledge base & RAG

Policy documents live in `knowledge_base/`:

- `approved_vendors.csv` — vendor master (approved / suspended, aliases)
- `payment_policy.md` — payment term rules
- `approval_policy.md` — spending limits (LKR)
- `required_fields_policy.md`, `currency_policy.md`, `procurement_categories.md`, `vendor_onboarding_policy.md`

Seed script (`scripts/seed_rag.py`) chunks and embeds all files into Qdrant collection `po_policies`.

Validation flow:

1. **Vendor** — RAG retrieval + alias matching against approved list
2. **Payment terms** — max 30 days for auto-approve
3. **Spending** — LKR 1M auto / 5M manager / above director review
4. **Math** — line items vs declared subtotal (1% tolerance)

Re-seed after changing policy files:

```bash
QDRANT_HOST=localhost python scripts/seed_rag.py
```

---

## Streamlit UI

Open http://localhost:8502

| Page | Purpose |
|------|---------|
| **Review Queue** | Approve/reject flagged POs |
| **Job History** | Audit trail with processed timestamp |
| **Process Order** | Manual file upload (same API as n8n) |
| **Policies** | Read-only view of knowledge base |

---

## n8n email workflow

Workflow export: `n8n/workflows/PO-Compliance-Intake.json`

```
Gmail Trigger → HTTP Request (POST /process-order) → Switch → AUTO-ACCEPTED / HUMAN_REVIEW / PROCESSING_FAILED
```

Setup:

1. Open http://localhost:5678
2. Import or open **PO-Compliance-Intake**
3. Configure **Gmail OAuth** on the trigger node
4. **Publish** the workflow (n8n 2.x — required for production triggers)
5. Send a new unread email with a PO attachment to the connected inbox

The HTTP node calls `http://api:8000/process-order` inside Docker. Streamlit uses the same endpoint for manual demos.

---

## Tests

```bash
pip install -r requirements.txt
pytest -m "not live" -q          # unit tests (no OpenAI/Qdrant calls)
pytest -m live -q                  # live extraction + RAG (needs API key + seeded Qdrant)
```

---

## Project structure

```
├── app/
│   ├── api/routes/          # process-order, jobs, review-queue
│   ├── services/            # parser, extraction, RAG, routing, DB
│   ├── models/              # Pydantic schemas
│   └── prompts/             # OpenAI extraction prompt
├── knowledge_base/          # policy documents (RAG source)
├── n8n/workflows/           # PO-Compliance-Intake.json
├── sample_documents/        # 3 demo PO files
├── scripts/seed_rag.py      # embed + load Qdrant
├── streamlit_app.py         # review UI
├── docker-compose.yml
└── tests/
```

---

## Environment variables

See `env.example`:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Required for extraction and embeddings |
| `OPENAI_MODEL` | Default `gpt-4o` |
| `OPENAI_EMBEDDING_MODEL` | Default `text-embedding-3-small` |
| `DATABASE_URL` | Postgres connection (set for Docker) |
| `QDRANT_HOST` | `qdrant` in Docker; `localhost` when seeding from host |
| `QDRANT_PORT` | Default `6333` |
| `QDRANT_COLLECTION` | Default `po_policies` |

Never commit `.env` — it is listed in `.gitignore`.

---

## Local development (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# Start Postgres + Qdrant (e.g. docker compose up -d postgres qdrant)
QDRANT_HOST=localhost python scripts/seed_rag.py
uvicorn app.main:app --reload --port 8000
API_URL=http://localhost:8000 streamlit run streamlit_app.py
```

---

## License

MIT (or as required by your submission).
