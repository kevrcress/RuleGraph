# RuleGraph

AI-powered business rules knowledge graph.

## Overview

RuleGraph ingests source code and documents, extracts business rules using LLM analysis, stores them in a structured knowledge graph (Postgres + Cognee), and provides an API for querying and managing those rules.

## Prerequisites

- Python 3.11+
- Docker + Docker Compose
- An Anthropic API key

## Setup

### 1. Clone and configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in all required values:

```
RULEGRAPH_ENCRYPTION_KEY=<generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rulegraph
REDIS_URL=redis://localhost:6379
ANTHROPIC_API_KEY=<your Anthropic API key>
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
```

### 2. Start infrastructure

```bash
docker compose up -d
```

This starts Postgres (port 5432) and Redis (port 6379).

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the backend

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000.

Interactive docs: http://localhost:8000/docs

## Running Tests

### Create the test database first

```bash
# Connect to Postgres and create the test database
docker exec -it rulegraph-postgres-1 psql -U postgres -c "CREATE DATABASE rulegraph_test;"
```

### Run unit and integration tests

```bash
pytest tests/unit/ tests/integration/ -v
```

### Run Stage 1 verification

```bash
pytest tests/verify_stage_1.py -v
```

## API Endpoints (Stage 1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest/file` | Ingest a file and extract business rules |
| GET | `/rules` | Paginated list of rules |
| GET | `/rules/{id}` | Single rule detail |
| GET | `/admin/ingest-errors` | List ingest errors |

### Example: Ingest a file

```bash
curl -X POST http://localhost:8000/ingest/file \
  -F "file=@seeds/Order.cs"
```

### Example: List rules

```bash
curl http://localhost:8000/rules?page=1&limit=10
```

## Project Structure

```
app/
├── config.py          # Pydantic settings, validates env vars at startup
├── database.py        # Async SQLAlchemy engine + session factory
├── main.py            # FastAPI app entry point
├── dependencies.py    # Shared FastAPI dependencies
├── models/            # SQLAlchemy ORM models
├── schemas/           # Pydantic response schemas
├── routers/           # FastAPI route handlers
├── services/          # Business logic services
├── graph/             # Cognee knowledge graph client (isolated here)
└── ingest/            # File ingestion pipeline
    ├── complexity.py  # Complexity scorer (0.0-1.0)
    ├── extractor.py   # LLM-based rule extractor
    └── pipeline.py    # Per-file processing orchestration
```

## Key Design Decisions

See `DECISIONS.md` for detailed rationale on non-obvious implementation choices.

## Configuration

See `rulegraph.yaml` for application configuration (no secrets).
See `.env.example` for required environment variables.
