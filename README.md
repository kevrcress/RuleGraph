# RuleGraph

[![CI](https://github.com/kevrcress/RuleGraph/actions/workflows/ci.yml/badge.svg)](https://github.com/kevrcress/RuleGraph/actions/workflows/ci.yml)

An AI-powered knowledge graph that extracts business rules from source code and documents, connects them across service boundaries, and becomes the single source of truth for how your organization's software actually behaves — in plain English.

---

## What it does

Most organizations have business logic scattered across dozens of microservices with no central record of what the rules are, who owns them, or whether they're consistent. RuleGraph fixes that.

**It ingests** your repos, wikis, PDFs, and Word docs. It uses an LLM to extract business rules in plain English from raw code. It stores those rules in a structured knowledge graph (Postgres + Cognee/LanceDB) and connects rules that span multiple services.

**It detects** conflicts (same rule defined differently in two services), terminology inconsistencies (`buyerId` vs `customerId` — same concept, different names), coverage gaps (rules with no automated tests), and drift (the code diverged from the documented rule).

**It surfaces** all of this through two lenses: a plain-English business view for BAs and product owners, and a technical view with file paths, confidence scores, and git attribution for engineers.

**It learns** from feedback. Thumbs up/down, "This is wrong" flags, and "Mark as verified" signals feed into a quality score per rule that improves over time.

---

## Key features

| Feature | Description |
|---------|-------------|
| **Rule extraction** | LLM reads source code, produces plain-English business rules with confidence scores |
| **Cross-service graph** | Rules linked across services — one rule can span Ordering, Payments, and Billing |
| **Conflict detection** | Flags when two services define the same concept differently |
| **Terminology normalization** | Finds `buyerId`/`customerId`/`customer_id` — same thing, three names |
| **Coverage tracking** | Tags every rule Covered / Partial / Uncovered / Stale |
| **Three-mode compare view** | Defined (what the wiki says) vs Implemented (what the code does) vs Compare (where they diverge) |
| **Impact analysis** | "If I change this rule, what services, tests, and rules are affected?" |
| **QA wiki** | Every code change produces a plain-language diff; promoted to main wiki after TL review |
| **Approval chain** | User proposes → Business Admin approves → Tech Lead flags code changes → rule goes active |
| **Feedback loop** | Signals (thumbs up/down, verified, wrong) update graph quality scores via `/improve` |
| **Chat** | Ask natural language questions about your rules: "What would break if we change the grace period?" |
| **Subscriptions** | Subscribe to any rule or service; get notified in-app when it changes |

---

## Screenshots

**Rules catalog** — browse extracted rules with status, confidence score, and source attribution. Filter by service, status, or search by keyword.

![Rules catalog](screenshots/Screenshot%201%20RuleGraph.png)

**Rule detail** — three-mode view (Defined / Implemented / Compare) with feedback controls, source file link, and an impact panel showing what else depends on this rule.

![Rule detail](screenshots/Screenshot%202%20RuleGraph.png)

**AI-generated wiki** — per-service summaries auto-generated from ingested code, with a linked rule list for navigating from high-level docs back to individual rules.

![AI-generated wiki](screenshots/Screenshot%203%20RuleGraph.png)

---

## Architecture

```
Browser (React 18 + Vite)
       │
       ▼
FastAPI (Python) ─── JWT auth, role-based access
       │
       ├── PostgreSQL  ← canonical store for all rules, users, audit log
       ├── Redis       ← sessions, rate limits, task queue (arq)
       └── Cognee/LanceDB ← knowledge graph + vector search (best-effort enrichment)

LLM routing (Anthropic — default):
  complexity < 0.5  →  claude-haiku-4-5   (fast, cheap)
  complexity ≥ 0.5  →  claude-sonnet-4-5  (thorough)

LLM routing (local — via LiteLLM proxy):
  set LITELLM_BASE_URL  →  routes all extraction through any Ollama/local model
  Batches API unavailable in proxy mode; files are processed sequentially
```

**Roles:** User · Business Admin · Technical Lead · Admin — each with a different view and different permissions in the approval chain.

---

## Running locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose
- An [Anthropic API key](https://console.anthropic.com/)

### 1. Clone and set up environment

```bash
git clone <repo-url> && cd RuleGraph
```

Create a `.env` file:

```bash
# Generate these two secrets first:
python3 -c "from cryptography.fernet import Fernet; print('RULEGRAPH_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
```

Then create `.env`:

```env
RULEGRAPH_ENCRYPTION_KEY=<paste from above>
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rulegraph
REDIS_URL=redis://localhost:6379
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET_KEY=<paste from above>
```

**Optional — run without an Anthropic key using a local model:**

Install LiteLLM and start a proxy in front of any Ollama model:

```bash
pip install litellm
litellm --model ollama/gemma3 --port 4000
```

Then add to `.env` (no `ANTHROPIC_API_KEY` required):

```env
LITELLM_BASE_URL=http://localhost:4000
```

Rule extraction will route through the proxy instead of Anthropic. Note: the Batches API is unavailable in proxy mode, so files are processed sequentially (same quality, slightly slower for large repos).

### 2. Start infrastructure

```bash
docker compose up -d
```

This starts Postgres on port 5432 and Redis on port 6379. Wait a few seconds for Postgres to be ready, then create the test database:

```bash
docker compose exec postgres createdb -U postgres rulegraph_test
```

### 3. Install Python dependencies

Install in two steps — a single `pip install -r requirements.txt` fails with
`ResolutionImpossible`, because `cognee==0.1.15` pins `anthropic<0.27.0` while the
app requires `anthropic==0.34.2` (it also pins older `fastapi`, `sqlalchemy`, and
`uvicorn`).

```bash
# 1. cognee first, with its own older pins
pip install "cognee==0.1.15"

# 2. everything else, which upgrades the shared packages to the versions the app needs
grep -v '^cognee==' requirements.txt > requirements-app.txt
pip install -r requirements-app.txt
```

On Windows PowerShell, substitute step 2's first line:

```powershell
Select-String -NotMatch '^cognee==' requirements.txt | ForEach-Object { $_.Line } > requirements-app.txt
```

Step 2 ends with a `pip` message reporting that cognee's pins are no longer
satisfied. That is expected and safe to ignore — pip still exits 0 and reports
`Successfully installed`. RuleGraph deliberately runs cognee alongside newer
shared packages; the graph layer is best-effort and its failures are contained by
design (see `DECISIONS.md`, DEC-001). CI and the Dockerfile install the exact same
way.

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the backend

```bash
uvicorn app.main:app --reload
```

API available at **http://localhost:8000**  
Interactive docs at **http://localhost:8000/docs**

### 5b. Start the ingest worker

Source ingest runs in a separate **arq** worker process so jobs survive a backend
restart. Start it alongside the backend (same env / `.env`):

```bash
arq app.tasks.worker.WorkerSettings
```

Triggering an ingest (`POST /admin/sources/{id}/ingest` or `/resume`) enqueues a
job onto Redis; the worker picks it up and runs it. If the worker is not running,
jobs queue in Redis until it starts.

> **⚠️ The worker is required, not optional.** `docker compose up` does **not** start
> it. Without a running worker: (1) every ingest sits queued in Redis and never runs,
> and (2) the staleness auto-recovery sweep — an arq cron that lives only in the worker
> — never fires, so a source left mid-ingest by a crash stays stuck at
> `ingest_status="ingesting"` until a worker is started. Run it as a managed process
> (e.g. a systemd unit or a `command:` override on the commented `worker` compose service).

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at **http://localhost:5173**

### 7. Load fixture data (recommended for local testing)

```bash
python3 scripts/seed_fixtures.py
```

Seeds the database with realistic-looking data across all tables — no Anthropic API calls required. Use this instead of running a real ingest when you just want to test UI or API behavior.

To wipe the database and re-seed from scratch:

```bash
python3 scripts/seed_fixtures.py --reset
```

**Seeded login credentials:**

| Email | Password | Role |
|-------|----------|------|
| `admin@acme.com` | `admin123` | admin |
| `sarah@acme.com` | `tech123` | tech_lead |
| `mark@acme.com` | `biz123` | business_admin |
| `jane@acme.com` | `user123` | user |

**What gets seeded:** 4 users · 5 services · 15 rules (all 7 statuses) · 6 rule versions · 2 ingest sources · 3 ingest runs · 3 ingest errors · 2 conflicts · 3 terminology inconsistencies · 2 documents · 3 notifications · 5 audit log entries · 4 feedback records · 4 system settings.

### 8. Ingest sample fixture data (cheap — ~$0.01 in API credits)

The `fixtures/sample_repo/` directory contains synthetic Python files designed to exercise conflict detection and terminology normalization with minimal cost. Each file scores < 0.5 complexity, so they route to `claude-haiku-4-5`.

Run each service directory as a separate ingest so RuleGraph builds cross-service graph edges:

```bash
python scripts/ingest_repo.py --path fixtures/sample_repo/payment   --source payment-service   --login admin@test.com Test1234!
python scripts/ingest_repo.py --path fixtures/sample_repo/orders     --source orders-service    --login admin@test.com Test1234!
python scripts/ingest_repo.py --path fixtures/sample_repo/inventory  --source inventory-service --login admin@test.com Test1234!
```

After all three runs, open the **Conflicts** page — you should see a conflict between `payment-service` (30-day refund window) and `orders-service` (45-day price-adjustment window). Both reference the same domain concept with different values.

### 9. Ingest real data (optional, costs API credits)

```bash
# Ingest the included seed file (eShopOnContainers Order.cs)
curl -X POST http://localhost:8000/ingest/file \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@seeds/Order.cs"
```

Or ingest a whole repo via the config in `rulegraph.yaml`.

---

## Running tests

```bash
# Unit + integration tests (no server needed — uses ASGI test client)
pytest tests/unit/ tests/integration/ -v

# Stage verification (run together so integration data is available)
pytest tests/unit/ tests/integration/ tests/verify_stage_6.py -v
```

The test suite uses a separate `rulegraph_test` database. All tests run without a live server, Anthropic key, or Cognee — the LLM and graph calls are mocked where needed.

---

## API overview

All endpoints except `/auth/*` and `/webhooks/*` require a `Authorization: Bearer <token>` header.

**Auth**
```
POST /auth/register   — create account
POST /auth/login      — returns JWT access token
```

**Rules**
```
GET  /rules               — paginated list
GET  /rules/{id}          — single rule with compare view data
POST /rules               — propose a new rule
PUT  /rules/{id}          — update (triggers authoring assists)
GET  /rules/{id}/lineage  — full version history
GET  /rules/{id}/impact         — what does this rule affect?
GET  /rules/{id}/impact/reverse — what affects this rule?
```

**Ingest**
```
POST /ingest/file     — ingest a single file (Admin)
POST /ingest          — full migration ingest from rulegraph.yaml (Admin)
POST /ingest/migrate  — migrate-only sources (Admin)
```

**Search & reports**
```
GET /search           — full-text search across rules
GET /conflicts        — cross-service rule conflicts
GET /coverage         — rule coverage status report
GET /terminology      — terminology inconsistency report
GET /diff             — paginated list of changed rules
GET /diff/{rule_id}   — before/after diff for a specific rule
```

**Documents**
```
POST /documents         — upload a document (PDF, DOCX, TXT, MD, EML)
POST /documents/preview — sandbox preview without committing (BA, Admin)
GET  /documents         — browse document library
```

**Feedback & quality**
```
POST /feedback    — record a signal (thumbs_up, thumbs_down, this_is_wrong, mark_as_verified, ...)
POST /improve     — recompute graph_quality_score from all signals (Admin)
POST /lint        — re-ingest Cognee skills to enrich graph (Admin)
```

**Wiki**
```
POST /wiki/promote  — promote QA changes to main wiki (TL, Admin)
```

**Chat**
```
POST /chat          — ask a natural language question
GET  /chat/history  — session history
```

**Subscriptions & notifications**
```
GET    /subscriptions       — my subscriptions
POST   /subscriptions       — subscribe to a rule/service/conflict
DELETE /subscriptions/{id}  — unsubscribe
GET    /notifications       — my notification feed
PUT    /notifications/{id}/read
```

**Admin**
```
GET /admin/review-queue               — rules pending BA approval
PUT /admin/review-queue/{id}/approve
PUT /admin/review-queue/{id}/reject
GET /admin/tech-lead-dashboard        — approved rules needing TL action
PUT /admin/tech-lead-dashboard/{id}/code-change
PUT /admin/tech-lead-dashboard/{id}/no-code
GET /admin/audit-log
GET /admin/users / POST / PUT
GET /admin/ingest-errors
GET /admin/settings / PUT
GET /admin/synonyms / approve / reject
```

**Sources (Admin)** — configure repos and drive ingest. List responses carry per-source
run progress: `run_status`, `done_file_count`/`total_file_count`, `run_is_stale`, and
`can_resume` (server-authoritative — the UI enables Resume from this flag).
```
GET    /admin/sources                 — list sources + latest-run progress
POST   /admin/sources                 — add a source
PUT    /admin/sources/{id}            — update a source
DELETE /admin/sources/{id}            — remove a source
POST   /admin/sources/{id}/ingest     — enqueue a fresh ingest (arq worker)
POST   /admin/sources/{id}/resume     — resume the latest incomplete run, skipping done files
GET    /admin/ingest-runs/{id}        — run detail
```

---

## Project structure

```
app/
├── main.py            # FastAPI app — middleware, router registration
├── config.py          # Pydantic settings — validates all env vars at startup
├── database.py        # Async SQLAlchemy engine + session factory
├── dependencies.py    # JWT auth + role guards as FastAPI dependencies
├── models/            # SQLAlchemy ORM models (Rule, Service, User, Feedback, ...)
├── schemas/           # Pydantic request/response schemas
├── routers/           # Thin route handlers — logic lives in services/
├── services/          # Business logic
│   ├── impact_service.py    # Upstream/downstream dependency traversal
│   ├── feedback_service.py  # FEEDBACK_WEIGHTS, signal recording, score aggregation
│   ├── rule_service.py      # Rule lifecycle state machine + authoring assists
│   ├── chat_service.py      # Cognee recall + session memory
│   ├── conflict_service.py
│   ├── coverage_service.py
│   └── ...
├── graph/
│   └── cognee_client.py  # ALL Cognee calls isolated here — nothing else touches Cognee
└── ingest/
    ├── pipeline.py       # Per-file orchestration
    ├── complexity.py     # Complexity scorer (0.0–1.0 → routes to haiku vs sonnet)
    ├── extractor.py      # LLM rule extraction with prompt injection framing
    ├── coverage_mapper.py
    ├── terminology_scanner.py
    └── connectors/       # ADO, GitHub, Confluence, Notion

frontend/src/
├── pages/
│   ├── rules/         # RuleBrowser, RuleDetail (with impact panel + feedback)
│   ├── reports/       # Conflicts, Coverage, Terminology, Diff
│   ├── admin/         # ReviewQueue, TechLeadDashboard, WikiPromotion, ...
│   └── chat/
├── components/
│   ├── CompareView/   # Three-mode compare (Defined / Implemented / Compare)
│   └── RuleDiff/      # Split-panel before/after diff, reused in 3 places
├── api/               # TanStack Query hooks + fetch wrappers
└── store/             # Zustand: auth, view toggle, notifications

my_skills/             # Cognee skill files — re-ingested on /improve
seeds/                 # Demo data: Order.cs, demo users, eShop seed script
tests/
├── unit/              # Per-module unit tests
├── integration/       # Multi-component integration tests
└── verify_stage_N.py  # End-to-end stage verification (do not modify)
```

---

## Feedback weights

All signal weights live in `feedback_service.FEEDBACK_WEIGHTS` — never hardcoded elsewhere:

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

## Design decisions

See [`DECISIONS.md`](DECISIONS.md) for the reasoning behind non-obvious choices (why Cognee failures are non-fatal, why scoring uses a weighted average, how the test suite handles session-scoped data, etc.).
