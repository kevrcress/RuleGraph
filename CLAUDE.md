# RuleGraph — Claude Code Context

## Project
RuleGraph is an AI-powered business rules knowledge graph. Full spec
is in `rulegraph-spec-v0.5.md`. Read it before writing any code.

## Working rules
- One stage at a time. Do not build ahead of the current stage.
- Run `pytest tests/unit/ tests/integration/ -v` before any stage
  verification script. Fix regressions first.
- Only stop when pytest exits 0. Print `[STAGE N COMPLETE]` summary.
- Log every non-spec decision to `DECISIONS.md` with reasoning.
- Never commit with failing tests.
- Never return PAT values in API responses.
- All Cognee calls isolated in `app/graph/cognee_client.py` only.
- Postgres only — no SQLite anywhere.
- Secrets from environment only — never in `rulegraph.yaml`.

## Stack
- Backend: FastAPI + asyncpg + SQLAlchemy 2.x + Alembic + Cognee
- Frontend: React 18 + TypeScript + Vite + Tailwind + shadcn/ui
- DB: PostgreSQL (Docker)
- Cache/queue: Redis (Docker)
- LLM: Anthropic — claude-haiku-4-5 (simple) / claude-sonnet-4-5 (complex)

## Commands
- Start services: `docker compose up -d`
- Run backend: `uvicorn app.main:app --reload`
- Run frontend: `cd frontend && npm run dev`
- Run tests: `pytest tests/unit/ tests/integration/ -v`
- Run stage check: `pytest tests/verify_stage_N.py -v`