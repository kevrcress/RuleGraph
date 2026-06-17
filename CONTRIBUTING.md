# Contributing to RuleGraph

Thanks for your interest in contributing. This document covers how to get a local dev environment running, how to submit changes, and what to expect from the review process.

---

## Table of contents

- [Prerequisites](#prerequisites)
- [Local setup](#local-setup)
- [Running tests](#running-tests)
- [Project structure](#project-structure)
- [Submitting changes](#submitting-changes)
- [Code style](#code-style)
- [Reporting bugs](#reporting-bugs)

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose
- An [Anthropic API key](https://console.anthropic.com/) (or set one via Admin → Settings after first run)

---

## Local setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/<your-fork>/RuleGraph.git
cd RuleGraph

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Copy the example env file and fill in values
cp .env.example .env
# Edit .env — generate RULEGRAPH_ENCRYPTION_KEY and JWT_SECRET_KEY per the comments

# 5. Start Postgres and Redis
docker compose up -d

# 6. Create the test database (once)
docker compose exec postgres createdb -U postgres rulegraph_test

# 7. Run migrations
alembic upgrade head

# 8. Seed demo data (no API credits required)
python3 scripts/seed_fixtures.py

# 9. Start the backend
uvicorn app.main:app --reload
# API at http://localhost:8000 — docs at http://localhost:8000/docs

# 10. Start the frontend (separate terminal)
cd frontend && npm install && npm run dev
# UI at http://localhost:5173
```

**Demo login credentials** (seeded by `seed_fixtures.py`):

| Email | Password | Role |
|-------|----------|------|
| `admin@acme.com` | `admin123` | Admin |
| `sarah@acme.com` | `tech123` | Tech Lead |
| `mark@acme.com` | `biz123` | Business Admin |
| `jane@acme.com` | `user123` | User |

---

## Running tests

```bash
# Unit + integration tests (no running server needed)
pytest tests/unit/ tests/integration/ -v

# Stage verification tests (requires both servers running)
uvicorn app.main:app --port 8000 &
cd frontend && npm run dev &
sleep 5
pytest tests/verify_stage_7.py -v
```

The test suite uses a separate `rulegraph_test` database. All ~150 tests run without a live Anthropic key — LLM calls are mocked where needed.

---

## Project structure

```
app/
├── config.py              # Pydantic settings, validated at startup
├── database.py            # Async SQLAlchemy engine + session factory
├── graph/cognee_client.py # ALL Cognee calls live here — nowhere else
├── ingest/                # Extraction pipeline, connectors, complexity scoring
├── models/                # SQLAlchemy ORM models
├── routers/               # FastAPI route handlers
├── schemas/               # Pydantic request/response schemas
├── security/              # JWT, encryption, rate limiting, webhook HMAC
└── services/              # Business logic layer

frontend/src/
├── api/                   # TanStack Query hooks
├── components/            # Shared UI components
└── pages/                 # Route-level page components

alembic/versions/          # Database migrations (never edit existing ones)
tests/
├── unit/                  # Per-module unit tests
├── integration/           # Multi-component integration tests
└── verify_stage_N.py      # End-to-end stage checks (do not modify)
```

Key constraints from `CLAUDE.md`:
- All Cognee calls are isolated in `app/graph/cognee_client.py`. No other file calls Cognee directly.
- Postgres only — no SQLite anywhere.
- Secrets from environment only — never hardcoded or in `rulegraph.yaml`.
- Never return PAT values in API responses.

---

## Submitting changes

1. **Fork** the repo and create a branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/the-bug-description
   ```

2. **Write tests** for any new service function or non-trivial utility. Unit tests go in `tests/unit/test_<module>.py`.

3. **Run the full test suite** before opening a PR:
   ```bash
   pytest tests/unit/ tests/integration/ -v
   cd frontend && npx tsc --noEmit && npm run lint
   ```

4. **Open a pull request** against `main`. Fill out the PR template — it asks for a summary, test plan, and breaking-change notes.

5. A maintainer will review within a few days. Please address feedback before re-requesting review.

### Branch naming

| Type | Example |
|------|---------|
| New feature | `feat/graph-clustering` |
| Bug fix | `fix/idle-in-transaction` |
| Docs | `docs/update-contributing` |
| Refactor | `refactor/extractor-async` |

---

## Code style

**Python**
- Formatting: [black](https://black.readthedocs.io/) (line length 100)
- Imports: [isort](https://pycqa.github.io/isort/)
- No inline comments that just restate what the code does — only comments explaining *why*

**TypeScript / React**
- ESLint config is in `frontend/.eslintrc.cjs`
- Functional components + hooks only
- Inline styles use the CSS variables defined in `index.css` (`var(--accent)`, `var(--panel)`, etc.)

---

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Please include:
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or screenshots
- Your OS, Python version, and Node version
