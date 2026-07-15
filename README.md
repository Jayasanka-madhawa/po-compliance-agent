# PO Compliance Agent

Purchase order compliance automation: ingest PDF/CSV attachments,
extract structured data with OpenAI, validate against company policies (RAG),
and route to AUTO_ACCEPT or HUMAN_REVIEW.

Built for Flat Rock Technology Agentic AI Engineer test task.

## Architecture

Email / manual trigger → n8n → FastAPI → OpenAI + Qdrant + Postgres

- **n8n** — workflow orchestration
- **FastAPI** — parse, extract, RAG validate, route decision
- **OpenAI** — structured extraction + embeddings
- **Qdrant** — policy knowledge base (RAG)
- **PostgreSQL** — job persistence + review queue

## Prerequisites

- Docker & Docker Compose
- OpenAI API key

## Quick start

```bash
git clone <your-repo-url>
cd po-compliance-agent
cp env.example .env
# Edit .env — set OPENAI_API_KEY=sk-proj-...

docker compose up -d
QDRANT_HOST=localhost python scripts/seed_rag.py