# RuleGraph

An AI-powered business rules knowledge graph that extracts business logic from source code and documents, connects rules across service boundaries, detects conflicts and drift, and surfaces everything through a plain-English interface — for both business analysts and engineers.

Most organisations have business logic scattered across dozens of microservices with no central record of what the rules are, who owns them, or whether they are consistent. RuleGraph ingests your code and docs, uses an LLM to extract rules in plain English, stores them in a structured graph (PostgreSQL + Cognee/LanceDB), and exposes reports, a chat interface, an approval workflow, and a feedback loop that improves rule quality over time.

---

## Features

- **LLM rule extraction** — reads source code and documents; produces plain-English business rules with confidence scores. Routes simple files to `claude-haiku-4-5` and complex files to `claude-sonnet-4-5` based on a static complexity scorer.
- **Cross-service rule graph** — rules are linked to the services that implement them; one rule can span Ordering, Payments, and Billing.
- **Conflict detection** — flags when two services define the same concept differently (keyword-based overlap across service boundaries).
- **Terminology normalisation** — detects `buyerId`/`customerId`/`customer_id` — same thing, three names.
- **Coverage tracking** — tags every rule `covered`, `partial`, `uncovered`, or `stale`.
- **Three-mode compare view** — Defined (what the wiki says) vs Implemented (what the code does) vs Compare (where they diverge).
- **Impact analysis** — "If I change this rule, what services, tests, and rules are affected?" Bidirectional: forward and reverse traversal.
- **Approval chain** — User proposes → Business Admin approves → Tech Lead flags code changes → rule goes active.
- **QA wiki** — every code change produces a plain-language diff; Tech Leads promote changes to the main wiki.
- **Feedback loop** — thumbs up/down, "this is wrong", "mark as verified" signals update `graph_quality_score` per rule via `POST /improve`.
- **Chat** — ask natural language questions about your rules; answers cite specific rules as sources.
- **Subscriptions and notifications** — subscribe to any rule or service; receive in-app notifications on status changes.
- **Graph visualisation** — React Flow canvas showing services, rules, and their `IMPLEMENTS` edges (Tech Lead and Admin only).
- **Audit log** — every state-changing action recorded with actor, target, and timestamp.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- An [Anthropic API key](https://console.anthropic.com/)

---

## Installation

### 1. Clone the repository

```bash
git clone <repo-url>
cd RuleGraph
```

### 2. Generate required secrets

These two values must be generated before creating `.env` — they cannot be arbitrary strings.

```bash
# Fernet encryption key (for PAT storage)
python3 -c "from cryptography.fernet import Fernet; print('RULEGRAPH_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# JWT signing secret
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
```

### 3. Create `.env`

```env
RULEGRAPH_ENCRYPTION_KEY=<paste Fernet key from above>
JWT_SECRET_KEY=<paste hex secret from above>
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rulegraph
REDIS_URL=redis://localhost:6379
ANTHROPIC_API_KEY=sk-ant-...
```

`DATABASE_URL` is auto-corrected from `postgresql://` or `postgres://` if you copy-paste a standard Postgres URL.

### 4. Start infrastructure

```bash
docker compose up -d
```

This starts PostgreSQL 16 on port 5432 and Redis 7 on port 6379. Wait a few seconds for Postgres to initialise, then create the test database (required for the test suite):

```bash
docker compose exec postgres createdb -U postgres rulegraph_test
```

### 5. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 6. Run database migrations

```bash
alembic upgrade head
```

### 7. Start the backend

```bash
uvicorn app.main:app --reload
```

API available at **http://localhost:8000**
Interactive docs at **http://localhost:8000/docs**

### 8. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at **http://localhost:5173**

---

## Configuration

All configuration is read from environment variables (or `.env`). The application exits at startup with a clear error message if any required variable is missing.

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL async URL (`postgresql+asyncpg://user:pass@host:port/db`) |
| `REDIS_URL` | Yes | Redis URL (`redis://host:port`) |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key — used for LLM rule extraction and Cognee |
| `JWT_SECRET_KEY` | Yes | Secret for HS256 JWT signing — generate with `secrets.token_hex(32)` |
| `RULEGRAPH_ENCRYPTION_KEY` | Yes | Fernet key for encrypting stored PATs — generate with `Fernet.generate_key()` |
| `WEBHOOK_TEST_SECRET` | No | HMAC secret for ADO webhook validation (default: `test-webhook-secret`) |

Non-secret settings (LLM model names, pagination limits, complexity threshold) are in `rulegraph.yaml` and `app/config.py`. Do not put secrets in `rulegraph.yaml`.

---

## Usage

### Create demo users

```bash
python seeds/demo_users.py
```

Creates one user per role: `admin@test.com`, `ba@test.com`, `tl@test.com`, `user@test.com` — all with password `Test1234!`.

### Get a JWT token

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"Test1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"
```

### Ingest a single file

```bash
curl -X POST http://localhost:8000/ingest/file \
  -H "Authorization: Bearer <token>" \
  -F "file=@seeds/Order.cs"
```

### Ingest a local or remote git repository

```bash
# From a local clone
python scripts/ingest_repo.py \
  --path /path/to/your/repo \
  --source my-service \
  --login admin@test.com Test1234!

# Clone and ingest a public repo
python scripts/ingest_repo.py \
  --clone https://github.com/org/repo \
  --source my-service \
  --login admin@test.com Test1234!

# Clone a private repo with a PAT
python scripts/ingest_repo.py \
  --clone https://github.com/org/repo \
  --git-token ghp_xxx \
  --source my-service \
  --login admin@test.com Test1234!
```

The script walks the repo, filters by extension (`.cs .py .ts .js .java .go .md .txt` and more), skips build artifacts and files over 200 KB, and calls `POST /ingest/file` for each file. Use `--dry-run` to preview the file list without sending anything. Requires Admin role.

### Ingest seed data (eShopOnContainers demo)

```bash
python seeds/eshop_seed.py
```

Seeds two C# files (`seeds/Order.cs`, `seeds/PaymentsProcessor.cs`) to demonstrate cross-service conflict and terminology detection.

---

## Architecture

```
Browser (React + Vite)  →  http://localhost:5173
         │
         ▼
FastAPI (Python)         →  http://localhost:8000
         │
         ├── PostgreSQL 16   ← canonical store for all rules, users, audit log
         ├── Redis 7         ← JWT rate limiting, chat session memory (24h TTL)
         └── Cognee/LanceDB  ← knowledge graph + vector search (best-effort enrichment)

LLM routing (Anthropic):
  complexity score < 0.5  →  claude-haiku-4-5   (fast, cheap)
  complexity score ≥ 0.5  →  claude-sonnet-4-5  (thorough)
```

**Complexity scoring** (`app/ingest/complexity.py`) combines four signals: line count, branch keyword density, business logic keyword density, and nesting depth — producing a 0.0–1.0 score that gates which LLM tier is used per file.

**Cognee is best-effort.** All Cognee failures are caught, logged to the application log, and never written to the `ingest_errors` table. If Cognee is unavailable, rule extraction and storage continue normally; only graph enrichment and vector recall are affected. PostgreSQL is the authoritative data store.

**Rule lifecycle state machine:**
```
proposed → under_review → approved → active
                 ↑              ↓
              rejected      drift / needs_update / deprecated
```

**Role system:**

| Role | What they can do |
|------|-----------------|
| `user` | Browse rules, propose rules, submit feedback, subscribe, use chat |
| `business_admin` | All of user + approve/reject rules in the review queue |
| `tech_lead` | All of user + tech lead dashboard, wiki promotion, graph visualisation |
| `admin` | Full access including ingest, audit log, user management, settings, data reset |

---

## API Overview

All endpoints except `/auth/*` and `/webhooks/*` require `Authorization: Bearer <token>`.

**Auth**
```
POST /auth/register   — create account (role field accepted for seeding; default: user)
POST /auth/login      — returns JWT access token (rate-limited: 100 attempts/15 min per IP)
```

**Rules**
```
GET  /rules                     — paginated list with filters
GET  /rules/{id}                — single rule with compare view data
POST /rules                     — propose a new rule (returns authoring hints if similar rules exist)
PUT  /rules/{id}                — update rule (triggers authoring assists)
GET  /rules/{id}/lineage        — full version history
GET  /rules/{id}/impact         — downstream: what does this rule affect?
GET  /rules/{id}/impact/reverse — upstream: what affects this rule?
```

**Ingest** (Admin only)
```
POST /ingest/file     — ingest a single file (multipart form)
POST /ingest          — bulk ingest from rulegraph.yaml sources
POST /ingest/migrate  — migrate-only sources
```

**Search and reports**
```
GET /search           — full-text search across rules
GET /conflicts        — cross-service rule conflicts
GET /coverage         — coverage status report
GET /terminology      — terminology inconsistency report
GET /diff             — paginated list of changed rules
GET /diff/{rule_id}   — before/after diff for a specific rule
```

**Documents**
```
POST /documents         — upload a document (PDF, DOCX, TXT, MD, EML); stored in uploads/
POST /documents/preview — sandbox preview without committing (BA, Admin)
GET  /documents         — browse document library
```

**Feedback and quality**
```
POST /feedback    — record a signal (thumbs_up, thumbs_down, this_is_wrong, mark_as_verified, …)
POST /improve     — recompute graph_quality_score from all signals (Admin)
POST /lint        — re-ingest Cognee skills to enrich graph (Admin)
```

**Wiki**
```
POST /wiki/promote  — promote QA changes to main wiki (Tech Lead, Admin)
```

**Chat**
```
POST /chat          — ask a natural language question (business or technical view)
GET  /chat/history  — session history (keyed by user + session_id in Redis)
```

**Subscriptions and notifications**
```
GET    /subscriptions       — my subscriptions
POST   /subscriptions       — subscribe to a rule/service/conflict
DELETE /subscriptions/{id}  — unsubscribe
GET    /notifications       — my notification feed
PUT    /notifications/{id}/read
```

**Graph** (Tech Lead, Admin)
```
GET /graph  — nodes and edges for React Flow visualisation
```

**Admin**
```
GET /admin/review-queue                  — rules pending BA approval
PUT /admin/review-queue/{id}/approve
PUT /admin/review-queue/{id}/reject
GET /admin/tech-lead-dashboard           — approved rules needing TL action
PUT /admin/tech-lead-dashboard/{id}/code-change
PUT /admin/tech-lead-dashboard/{id}/no-code
GET /admin/audit-log
GET /admin/users / POST / PUT
GET /admin/ingest-errors
GET /admin/settings / PUT
GET /admin/synonyms / approve / reject
DELETE /admin/data                       — danger zone: wipe all rules and related data
```

---

## Development

### Run tests

```bash
# Unit + integration tests (no live server or Anthropic key needed — LLM calls are mocked)
pytest tests/unit/ tests/integration/ -v

# Stage verification (run together with unit/integration so seeded data is available)
pytest tests/unit/ tests/integration/ tests/verify_stage_6.py -v
```

The test suite uses a separate `rulegraph_test` database. All 150+ tests run without a live server or Cognee — graph calls and LLM calls are mocked where needed. The database is dropped and recreated at the start of each test session.

**Before running tests** you must create the test database (one-time):
```bash
docker compose exec postgres createdb -U postgres rulegraph_test
```

### Frontend development

```bash
cd frontend
npm run dev   # dev server with HMR
npm run build # production build
npm run lint  # ESLint
```

### Project structure

```
app/
├── main.py            # FastAPI app — middleware, CORS, router registration, Cognee startup
├── config.py          # Pydantic settings — validates all env vars at startup; exits on missing var
├── database.py        # Async SQLAlchemy engine + session factory
├── dependencies.py    # JWT auth + role guards as FastAPI dependencies
├── models/            # SQLAlchemy ORM models (Rule, Service, User, Feedback, …)
├── schemas/           # Pydantic request/response models
├── routers/           # Thin route handlers — business logic lives in services/
├── services/
│   ├── rule_service.py      # Rule lifecycle state machine + authoring assists
│   ├── feedback_service.py  # FEEDBACK_WEIGHTS, signal recording, score aggregation
│   ├── impact_service.py    # Upstream/downstream dependency traversal
│   ├── chat_service.py      # Cognee recall + Postgres fallback + Redis session memory
│   ├── conflict_service.py  # Cross-service keyword-overlap conflict detection
│   ├── coverage_service.py
│   └── …
├── graph/
│   └── cognee_client.py  # ALL Cognee calls isolated here — no other file touches Cognee
├── security/
│   ├── jwt.py            # HS256 token creation and validation (60-min TTL)
│   ├── encryption.py     # Fernet symmetric encryption for PAT storage
│   ├── rate_limit.py     # Redis sliding-window rate limiter (fail-open if Redis down)
│   └── webhook.py        # HMAC webhook signature validation
└── ingest/
    ├── pipeline.py           # Per-file orchestration (8-step pipeline)
    ├── complexity.py         # Static complexity scorer (0.0–1.0)
    ├── extractor.py          # LLM rule extraction with prompt injection framing
    ├── coverage_mapper.py
    ├── terminology_scanner.py
    └── connectors/           # ADO repo, ADO wiki, GitHub, Confluence (stubs — not yet implemented)

frontend/src/
├── pages/
│   ├── rules/         # RuleBrowser, RuleDetail (compare view + impact panel + feedback)
│   ├── reports/       # Conflicts, Coverage, Terminology, Diff
│   ├── admin/         # ReviewQueue, TechLeadDashboard, WikiPromotion, AuditLog, Users, …
│   ├── chat/          # Natural language query interface
│   ├── graph/         # React Flow knowledge graph canvas
│   └── documents/
├── components/        # Shared UI — CompareView, RuleDiff, ProtectedRoute, …
├── api/               # TanStack Query hooks + Axios wrappers
└── store/             # Zustand: auth state, view toggles, notifications

my_skills/             # Cognee skill files re-ingested on POST /improve
seeds/                 # Demo data: Order.cs, PaymentsProcessor.cs, demo_users.py, eshop_seed.py
scripts/               # ingest_repo.py — CLI tool for ingesting local or remote git repos
alembic/versions/      # Database migrations (0001–0004)
tests/
├── unit/              # Per-module unit tests
├── integration/       # Multi-component integration tests
└── verify_stage_N.py  # Stage-specific end-to-end verification (do not modify)
```

---

## Feedback weights

All signal weights live in `app/services/feedback_service.py:FEEDBACK_WEIGHTS` — never hardcoded elsewhere:

| Signal | Weight | Type |
|--------|--------|------|
| `mark_as_verified` | 1.0 | Explicit |
| `thumbs_up` | 0.9 | Explicit |
| `drift_caught_and_resolved` | 0.9 | Automated |
| `edited_rule_after_view` | 0.8 | Implicit |
| `conflict_resolved` | 0.8 | Implicit |
| `coverage_gap_fixed` | 0.8 | Implicit |
| `clicked_source_doc` | 0.7 | Implicit |
| `clicked_through` | 0.6 | Implicit |
| `thumbs_down` | 0.2 | Explicit |
| `searched_again_immediately` | 0.2 | Implicit |
| `this_is_wrong` | 0.1 | Explicit |

`graph_quality_score` is the weighted average of all recorded signals for a rule, recomputed on every `POST /improve` call.

---

## Dependencies

**Backend (key packages)**

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.115.0 | API framework |
| `uvicorn` | 0.30.6 | ASGI server |
| `sqlalchemy` | 2.0.35 | Async ORM |
| `asyncpg` | 0.29.0 | PostgreSQL async driver |
| `alembic` | 1.13.2 | Database migrations |
| `anthropic` | 0.34.2 | LLM rule extraction |
| `cognee` | 0.1.15 | Knowledge graph + vector search |
| `redis` | 5.0.8 | Rate limiting, chat session memory |
| `arq` | 0.26.1 | Async task queue (webhook event processing) |
| `python-jose` | 3.3.0 | JWT signing and validation |
| `cryptography` | 43.0.1 | Fernet encryption for PAT storage |
| `gitpython` | 3.1.43 | Git repo cloning in `ingest_repo.py` |
| `pypdf2` | 3.0.1 | PDF document parsing |
| `python-docx` | 1.1.2 | DOCX document parsing |

**Frontend (key packages)**

| Package | Purpose |
|---------|---------|
| `react` + `react-dom` | UI framework (v19) |
| `react-router-dom` | Client-side routing |
| `@tanstack/react-query` | Server state management and caching |
| `zustand` | Client state (auth, view mode, notifications) |
| `reactflow` | Knowledge graph canvas visualisation |
| `@radix-ui/*` | Accessible headless UI primitives (shadcn/ui) |
| `axios` | HTTP client |
| `tailwindcss` | Utility CSS |
| `vite` | Build tool and dev server |

---

## Notes

**Non-obvious setup steps**
- `RULEGRAPH_ENCRYPTION_KEY` must be a valid Fernet key — it is not an arbitrary string. Use the generation command in step 2 above. The app will crash at startup with a cryptography error if you provide a random string.
- The test database (`rulegraph_test`) must be created manually before first running `pytest`. The test suite does not create it.
- `DATABASE_URL` is silently corrected from `postgresql://` or `postgres://` to `postgresql+asyncpg://` at startup — you do not need to include the driver in the URL.

**Architecture decisions worth knowing**
- Cognee failures are never fatal. If `import cognee` fails or any Cognee API call raises, the exception is caught and logged at WARNING level. Rule extraction and storage proceed normally.
- Conflict detection and terminology scanning run after every `POST /ingest/file` call. Both are wrapped in `try/except` and are non-fatal.
- passlib was replaced with direct `bcrypt` calls (`auth_service.py`) due to a `passlib 1.7.4` incompatibility with `bcrypt 4.x+`.
- Document files are stored in a local `uploads/` directory (not cloud storage). The `storage_path` column is abstracted to allow backend replacement later.
- The source connectors (GitHub, Confluence, ADO, Notion) exist as stubs in `app/ingest/connectors/` and raise `NotImplementedError`. Use `POST /ingest/file` or `scripts/ingest_repo.py` for actual ingestion.
- The `arq` worker (`app/tasks/worker.py`) handles ADO webhook events asynchronously but currently only logs them — targeted ingest on push is not yet implemented.
- Chat session memory is stored in Redis with a 24-hour TTL. If Redis is unavailable, chat still works but without prior-turn context.
- Stage verify scripts (`tests/verify_stage_N.py`) must not be modified. Stages 1–2 verify scripts fail when run standalone after Stage 3 (which added auth) — this is expected and documented in DECISIONS.md.

**Security**
- JWT tokens use HS256 with a 60-minute TTL.
- Login is rate-limited to 100 attempts per IP per 15 minutes (Redis sliding window, fails open if Redis is down).
- PATs are encrypted at rest using Fernet symmetric encryption and are never returned in API responses.
- LLM extraction prompts use explicit prompt injection framing to prevent source content from hijacking extraction instructions.

See [`DECISIONS.md`](DECISIONS.md) for the full reasoning behind all non-obvious implementation choices.
