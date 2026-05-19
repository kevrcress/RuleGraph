# RuleGraph — Claude Code Agentic Build Prompt

## How to use this file

This file contains a master header and 7 stage prompts.

**Starting Stage 1:**
Paste the MASTER HEADER + STAGE 1 into Claude Code as your first message.

**Starting each subsequent stage:**
Re-attach the full spec (`rulegraph-spec-v0_5_1_.md`) and paste:
- The MASTER HEADER
- The CONTINUATION HEADER (tells Claude which stages are done)
- The next stage prompt

The spec is the single source of truth. These prompts tell Claude Code
how to work and what to build in each stage. They do not repeat the spec.

---

## MASTER HEADER
*(Include this at the top of every stage prompt)*

You are building RuleGraph. The full specification is in
`rulegraph-spec-v0_5_1_.md` in this directory. Read the entire spec
before writing any code.

### Non-negotiable working rules

1. **One stage at a time.** Implement only the current stage. Sections
   marked `[NOT IN THIS STAGE — DO NOT BUILD YET]` are structural context
   only. Read them for awareness. Do not implement them.

2. **Run your own tests.** After implementing each stage, run the
   verification script yourself using your bash tool:
   `pytest tests/verify_stage_N.py -v`
   Fix all failures before stopping. Do not ask the human to run tests.

3. **Only stop when pytest exits 0.** Print a `[STAGE N COMPLETE — all
   tests passed]` summary showing the test count. That is the only
   acceptable stopping condition.

4. **Log decisions.** Any time you make a choice not explicitly specified,
   write it to `DECISIONS.md` with your reasoning. Do not ask — decide
   and document.

5. **Pinned dependencies.** Use the exact versions in Section 32.
   Do not upgrade or substitute without logging the reason in DECISIONS.md.

6. **Cognee API.** Use `cognee.add()` and `cognee.search()` as specified
   in Section 10. All Cognee calls are isolated in
   `app/graph/cognee_client.py`. No other file calls Cognee directly.

7. **Postgres only.** No SQLite anywhere. Use asyncpg + SQLAlchemy 2.x
   async + Alembic as specified in Section 10.

8. **Never return PAT values in API responses.** Ever.

9. **Secrets from environment only.** `rulegraph.yaml` never contains
   secrets. All secrets come from env vars validated at startup per
   Section 27.

10. **Folder structure is fixed.** Use the structure in Section 31
    exactly. Do not reorganize it.

### Environment setup
Before running the app or tests, ensure Docker services are running:
```bash
docker compose up -d
```
The `docker-compose.yml` must define both `postgres` and `redis`
services. The test suite uses a separate `rulegraph_test` database —
create it once after first bringing Postgres up:
```bash
docker compose exec postgres createdb -U postgres rulegraph_test
```

### Git discipline
- A git repo must exist in the project root before starting. If not
  present, initialize it:
  ```bash
  git init && git add -A && git commit -m "init"
  ```
- After pytest exits 0 for a stage, commit all changes before stopping:
  ```bash
  git add -A && git commit -m "stage N complete: <one line summary>"
  ```
- Never commit with failing tests.
- Never force push or amend commits from completed stages.
- Write meaningful commit messages — future stages may need to
  understand what changed and why.

### Unit tests and regression protection
- Every service function and non-trivial utility gets a unit test in
  `tests/unit/test_<module>.py` as you write it — not after.
- Integration tests go in `tests/integration/`.
- The stage verification scripts (`verify_stage_N.py`) are
  end-to-end tests — do not modify them.
- Before running `pytest tests/verify_stage_N.py -v`, always run
  the full existing test suite first:
  ```bash
  pytest tests/unit/ tests/integration/ -v
  ```
  Fix any regressions before running the stage verification.
- If a later stage breaks an earlier stage's tests, fix the regression
  before continuing. Log it in `DECISIONS.md`.
- Test directory layout:
  ```
  tests/
  ├── unit/              # per-module unit tests
  ├── integration/       # multi-component integration tests
  ├── conftest.py        # shared fixtures
  └── verify_stage_N.py  # end-to-end stage checks (do not modify)
  ```

### Design tokens (frontend)
```css
--ink-0: #0e0d0c;   --ink-1: #161513;   --ink-2: #1e1c19;
--ink-3: #2a2820;   --ink-4: #3a3830;
--bone-0: #e8e0d0;  --bone-1: #c8c0b0;  --bone-2: #a8a090;
--bone-3: #787060;  --bone-4: #484038;
--brass-0: #c9a84c; --brass-1: #8a6f32; --brass-2: #5a4820;
--ember: #c0392b;
--serif: 'Newsreader', Georgia, serif;
--sans: 'IBM Plex Sans', system-ui, sans-serif;
--mono: 'IBM Plex Mono', monospace;
```

---

## CONTINUATION HEADER
*(Include this when starting Stage 2 and beyond, filling in N)*

Stages 1 through N are complete and their tests pass.
Do not modify any files from completed stages except to fix bugs that
are blocking the current stage. If you need to fix a prior stage bug,
note it in DECISIONS.md.

Now implement Stage N+1 as described below.

---

## STAGE 1 — Foundation

Implement Stage 1 as defined in Section 33 of the spec.

**What to build** (from Section 33 Stage 1):
- Full project scaffold per Section 31 folder structure
- `docker-compose.yml` — Postgres + Redis
- `requirements.txt` — exact versions from Section 32
- `.env.example` — all required vars from Section 27, no values
- `app/config.py` — Pydantic settings, validates all required env vars
  at startup, exits with clear error if any are missing
- `app/database.py` — async SQLAlchemy engine + session factory
- Alembic migration — all tables and enums from Section 11
- `app/graph/cognee_client.py` — Cognee init and `add()`, `search()`,
  `recall()`, `config` methods isolated here, nothing else calls Cognee
- `rulegraph.yaml` example config loader (reads env vars for secrets,
  never secrets inline)
- `app/ingest/complexity.py` — complexity scorer (0.0–1.0) per Section 10
- `app/ingest/extractor.py` — LLM extraction with prompt injection
  framing from Section 27. Routes to claude-haiku-4-5 (score < 0.5)
  or claude-sonnet-4-5 (score ≥ 0.5)
- `app/ingest/pipeline.py` — per-file processing orchestration per
  Section 12
- `app/services/ingest_service.py` — retry logic per Section 13,
  error logging to `ingest_errors`, run tracking in `ingest_runs`
- `POST /ingest/file` — ingest a single file (no auth yet)
- `GET /rules` — paginated list (no auth yet)
- `GET /rules/{id}` — single rule (no auth yet)
- `seeds/Order.cs` — copy the seed fixture from Section 30
- `tests/conftest.py` — shared fixtures per spec
- `tests/verify_stage_1.py` — copy verbatim from Section 33
- `DECISIONS.md` — create now, append decisions as you go
- `README.md` — setup instructions (docker compose, env vars, run app)

**[NOT IN THIS STAGE — DO NOT BUILD YET]:**
Auth/JWT, all other endpoints, frontend, source connectors, conflict
detection, terminology, coverage, Cognee skills, seeds other than
Order.cs and demo_users stub

**After implementing**, run the full test suite then the stage check:
```bash
pytest tests/unit/ tests/integration/ -v        # fix any failures first
pytest tests/verify_stage_1.py -v               # then run stage check
git add -A && git commit -m "stage 1 complete"  # only after both pass
```
Only stop when both pytest runs exit 0.

---

## STAGE 2 — Multi-Source Ingest + Detection

*(Attach full spec. Include MASTER HEADER + CONTINUATION HEADER for
stages 1 complete, then this section.)*

Implement Stage 2 as defined in Section 33 of the spec.

**What to build** (from Section 33 Stage 2):
- `app/ingest/connectors/ado_repo.py` — git clone + ADO REST API
- `app/ingest/connectors/ado_wiki.py` — ADO wiki connector, ongoing
  sync config supported per Section 6
- `app/ingest/connectors/github_repo.py`
- `app/ingest/connectors/confluence.py`
- `POST /ingest` — full migration ingest from rulegraph.yaml config
- `POST /ingest/migrate` — migrate-only sources
- `app/ingest/coverage_mapper.py` — maps test files to rules per Section 5
- `app/ingest/terminology_scanner.py` — per Section 5
- `app/services/conflict_service.py` — per Section 5
- `app/services/coverage_service.py` — per Section 5
- `app/services/terminology_service.py` — per Section 5
- `app/services/document_service.py` — upload handling, magic byte
  validation per Section 8, sandbox storage
- `POST /documents` — upload with file type + size validation
- `POST /documents/preview` — sandbox preview, returns proposed changes
  without committing per Section 8
- `GET /conflicts` — paginated, per Section 15
- `GET /coverage` — paginated, per Section 15
- `GET /terminology` — paginated, per Section 15
- `GET /diff` — paginated summary list per Section 19
- `GET /diff/{rule_id}` — per-rule before/after diff data per Section 19
- Migration report output (markdown summary to stdout + stored)
- `seeds/eshop_seed.py` — clones eShopOnContainers, runs full ingest
- `seeds/late_fee_spec_sample.pdf` — generate a minimal valid PDF for
  testing
- `tests/verify_stage_2.py` — copy verbatim from Section 33

**[NOT IN THIS STAGE — DO NOT BUILD YET]:**
Auth/JWT, frontend, Cognee skills, `/improve`, approval chain,
notifications, webhooks

**After implementing**, run the full test suite then the stage check:
```bash
pytest tests/unit/ tests/integration/ -v        # fix any failures first
pytest tests/verify_stage_2.py -v               # then run stage check
git add -A && git commit -m "stage 2 complete"  # only after both pass
```
Only stop when both pytest runs exit 0.

---

## STAGE 3 — Auth, Roles, and Approval Chain

*(Attach full spec. Include MASTER HEADER + CONTINUATION HEADER for
stages 1-2 complete, then this section.)*

Implement Stage 3 as defined in Section 33 of the spec.

**What to build** (from Section 33 Stage 3):
- `app/security/jwt.py` — token creation and validation, TTL from
  system settings, signed with JWT_SECRET_KEY
- `app/security/encryption.py` — Fernet encrypt/decrypt per Section 27
- `app/security/rate_limit.py` — Redis sliding window per Section 27
- `app/security/webhook.py` — HMAC validation per Section 27
- `POST /auth/register` — with per-IP rate limit
- `POST /auth/login` — with per-IP rate limit
- JWT middleware on all non-auth, non-webhook endpoints
- Role enforcement on all endpoints per Section 15 roles column
- `app/services/auth_service.py`
- `app/services/rule_service.py` — rule lifecycle state machine per
  Section 17, authoring assists (similarity, conflict, completeness,
  terminology checks) per Section 17
- `POST /rules` — with role checks and authoring assists in response
- `PUT /rules/{id}` — with role checks
- `GET /admin/review-queue` — BA + Admin only
- `PUT /admin/review-queue/{id}/approve` — rule status → approved
- `PUT /admin/review-queue/{id}/reject` — rule returns with notes,
  status → proposed, rejection note on rule_versions record
- "Will Not Implement" path → status → deprecated per Section 17
- `GET /admin/tech-lead-dashboard` — TL + Admin only
- `PUT /admin/tech-lead-dashboard/{id}/code-change` — pre-populated
  work item form, editable before confirming, then created via ADO/GitHub
- `PUT /admin/tech-lead-dashboard/{id}/no-code` — rule → Active
- `app/services/workitem_service.py` — ADO REST API + GitHub Issues API,
  repo/project from user's connected accounts per Section 17
- `GET /rules/{id}/lineage` and `?since=` per Section 25
- `POST /webhooks/ado` — HMAC validated, returns 200 immediately,
  queues async job via arq per Section 27
- `GET /admin/audit-log` — Admin only, filterable, sortable
- `GET /admin/ingest-errors` — Admin only
- `PUT /admin/ingest-errors/{id}/resolve`
- `GET /admin/users`, `POST /admin/users`, `PUT /admin/users/{id}`
- `GET /admin/settings`, `PUT /admin/settings`
- `GET /admin/synonyms`, approve/reject endpoints
- `app/tasks/worker.py` — arq task definitions for webhook processing
- `seeds/demo_users.py` — creates one user per role with known passwords
- `tests/verify_stage_3.py` — copy verbatim from Section 33

All audit log actions from Section 11 must be written at the correct
points. Audit log is never modified or deleted.

**[NOT IN THIS STAGE — DO NOT BUILD YET]:**
Frontend, notifications, subscriptions, chat, feedback loop,
graph visualization

**After implementing**, run the full test suite then the stage check:
```bash
pytest tests/unit/ tests/integration/ -v        # fix any failures first
pytest tests/verify_stage_3.py -v               # then run stage check
git add -A && git commit -m "stage 3 complete"  # only after both pass
```
Only stop when both pytest runs exit 0.

---

## STAGE 4 — React Frontend

*(Attach full spec. Include MASTER HEADER + CONTINUATION HEADER for
stages 1-3 complete, then this section.)*

Implement Stage 4 as defined in Section 33 of the spec.

**What to build:**
All frontend code under `frontend/src/` per the folder structure in
Section 31. Stack: React 18 + TypeScript + Vite + Tailwind + shadcn/ui +
TanStack Query + Zustand + React Router v6.

Key implementation notes:

- **Auth:** JWT stored in localStorage. Protected routes redirect to
  login. Token attached to all API requests via TanStack Query client.

- **View toggle** (Section 3): User and Business Admin see business view
  only, no toggle. Technical Lead and Admin see technical view by default
  with toggle available. Preference persisted in localStorage.

- **Role-aware routing:** Each role sees a different home dashboard.
  Admin sees system overview. BA sees review queue. TL sees TL dashboard.
  User sees rule browser.

- **RuleDiff component** — split-panel before/after with red/green
  highlights per Section 19. Reused in: diff list drill-down, lineage
  timeline, QA promotion review. Build it once as a shared component.

- **CompareView** — three tabs: Defined / Implemented / Compare.
  Compare tab shows status badge (Verified / Drift / Undocumented /
  Orphaned) per Section 4.

- **WikiEditor** — plain text for User/BA, markdown toggle for TL/Admin.
  Authoring assist warnings appear inline as user types (debounced API
  call to check similarity, conflict, completeness, terminology).

- **data-testid attributes** — every interactive element that is tested
  in `verify_stage_4.py` through `verify_stage_7.py` must have the
  correct `data-testid`. Check the Playwright test files in Section 33
  for required testids before building components.

- **Document upload** — file type and size validation on the client
  before submission. Clear error messages for rejected types.

Pages to build (all per Section 31 folder structure):
- `auth/Login.tsx`, `auth/Register.tsx`
- `rules/RuleBrowser.tsx`, `rules/RuleDetail.tsx`
- `documents/DocumentLibrary.tsx`
- `reports/Conflicts.tsx`, `reports/Coverage.tsx`,
  `reports/Terminology.tsx`, `reports/Diff.tsx`
- `admin/Users.tsx`, `admin/ReviewQueue.tsx`,
  `admin/TechLeadDashboard.tsx`, `admin/IngestErrors.tsx`,
  `admin/AuditLog.tsx`, `admin/Settings.tsx`
- `settings/UserSettings.tsx` (role display, connected accounts,
  PAT connection flow)

**[NOT IN THIS STAGE — DO NOT BUILD YET]:**
Chat UI, subscription UI, feedback signal UI, graph visualization
(`/graph` page and React Flow), environment selector, demo script

**After implementing**, install Playwright and run:
```bash
cd frontend && npm run build && cd ..     # verify no TypeScript errors
playwright install chromium
pytest tests/unit/ tests/integration/ -v  # fix regressions first
# Start both servers in background
uvicorn app.main:app --port 8000 &
cd frontend && npm run dev &
sleep 5
pytest tests/verify_stage_4.py -v
git add -A && git commit -m "stage 4 complete"  # only after both pass
```
Only stop when all pytest runs exit 0.

---

## STAGE 5 — Chat, Subscriptions, and Notifications

*(Attach full spec. Include MASTER HEADER + CONTINUATION HEADER for
stages 1-4 complete, then this section.)*

Implement Stage 5 as defined in Section 33 of the spec.

**What to build** (from Section 33 Stage 5):
- `app/services/chat_service.py` — Cognee `recall()` with session memory
  in Redis per user, confidence score + sources cited in response,
  business/technical view shapes per Section 22
- `POST /chat` — rate limited per Section 27
- `GET /chat/history?session_id=`
- Chat thread submit-as-source flow → goes to BA review queue as a
  document entry per Section 22
- `app/services/notification_service.py` — notification creation,
  all triggers from Section 18 wired to their events
- `GET /subscriptions`, `POST /subscriptions`,
  `DELETE /subscriptions/{id}`
- `GET /notifications`, `PUT /notifications/{id}/read`
- Notification triggers wired to all events in Section 18 notification
  triggers table
- Cognee skills written and ingested:
  - `my_skills/business-logic-extraction.md`
  - `my_skills/conflict-detection.md`
  - `my_skills/terminology-normalization.md`
  Skills format: YAML frontmatter + Markdown body per Section 14
- **Frontend additions:**
  - `chat/Chat.tsx` — conversation view, source link-outs, view toggle,
    submit-as-source button
  - Subscription button on rule detail, service, and conflict pages
  - Notification bell + feed wired to live data (component built in
    Stage 4, now connected)
- `tests/verify_stage_5.py` — copy verbatim from Section 33

**[NOT IN THIS STAGE — DO NOT BUILD YET]:**
Feedback signals, `/improve` endpoint, graph visualization,
impact analysis, environment selector, demo script

**After implementing**, run the full test suite then the stage check:
```bash
pytest tests/unit/ tests/integration/ -v        # fix any failures first
pytest tests/verify_stage_5.py -v               # then run stage check
git add -A && git commit -m "stage 5 complete"  # only after both pass
```
Only stop when both pytest runs exit 0.

---

## STAGE 6 — Impact Analysis, Feedback Loop, and QA Wiki

*(Attach full spec. Include MASTER HEADER + CONTINUATION HEADER for
stages 1-5 complete, then this section.)*

Implement Stage 6 as defined in Section 33 of the spec.

**What to build** (from Section 33 Stage 6):
- `app/services/impact_service.py` — graph traversal for upstream and
  downstream dependencies per Section 21
- `GET /rules/{id}/impact` — predictive impact, business + technical
  views per Section 21
- `GET /rules/{id}/impact/reverse` — what affects this rule
- Impact analysis auto-runs post-ingest and is included in QA diff
  per Section 21
- `app/services/feedback_service.py` — FEEDBACK_WEIGHTS config object
  per Section 28 (never hardcode a weight inline), implicit + explicit
  + automated signal capture, score aggregation per Cognee node
- `POST /feedback` — record any feedback signal
- `POST /improve` — Admin only, applies feedback weights to graph nodes
  via Cognee, re-ingests skills per Section 28
- `POST /lint` — Admin only, re-enriches graph per Section 14
- QA wiki promotion flow — `POST /wiki/promote` (TL + Admin), applies
  approved changes from QA area to main wiki per Section 7
- **Frontend additions:**
  - Feedback signals wired: thumbs up/down on search results, "This is
    wrong" flag on rule detail, "Mark as verified" on compare view
  - Implicit signals captured: click-through, source doc click,
    immediate re-search detection, rule edit after view
  - Impact panel on rule detail page (collapsible, lazy loaded)
  - QA wiki promotion review screen using the RuleDiff component
- `tests/verify_stage_6.py` — copy verbatim from Section 33

**[NOT IN THIS STAGE — DO NOT BUILD YET]:**
Graph visualization page, demo script

**After implementing**, run the full test suite then the stage check:
```bash
pytest tests/unit/ tests/integration/ -v        # fix any failures first
pytest tests/verify_stage_6.py -v               # then run stage check
git add -A && git commit -m "stage 6 complete"  # only after both pass
```
Only stop when both pytest runs exit 0.

---

## STAGE 7 — Graph Visualization, Demo Script, and PoC Sign-off

*(Attach full spec. Include MASTER HEADER + CONTINUATION HEADER for
stages 1-6 complete, then this section.)*

Implement Stage 7 as defined in Section 33 of the spec. This is the
final stage. After it passes, the PoC is complete.

**What to build** (from Section 33 Stage 7):
- `frontend/src/components/GraphVisualization/` — React Flow wrapper
  per Section 26:
  - Service nodes and BusinessRule nodes
  - Typed and labeled relationship edges
  - Clicking a node navigates to rule or service detail page
  - Reasonable automatic layout (Phase 1 — no clustering/filtering yet)
  - `data-testid="graph-visualization"` on the root element
- `/graph` page in the frontend — Technical View only, all roles with
  toggle access can see it. Users (business view only) see an
  access-denied state per the Playwright tests in Section 33
- `GET /graph` endpoint — returns nodes and edges for React Flow
- `seeds/demo.py` — automated demo script per Section 31:
  - Accepts `--test-mode` flag
  - Ingests demo data
  - Runs before snapshot (node count, edge count, top search result)
  - Calls `/improve` with hardcoded score 0.9
  - Calls `/lint`
  - Runs after snapshot
  - Prints before/after diff
  - In `--test-mode`: exits 0 and prints `[✓] N.` confirmation for
    each of the 7 PoC requirements per the test assertions in
    `verify_stage_7.py`
- `tests/verify_stage_7.py` — copy verbatim from Section 33

**PoC requirements that must all pass** (from Section 33 Stage 7 tests):
1. At least one rule spanning multiple services
2. At least one conflict detected
3. At least one terminology inconsistency
4. At least one coverage gap
5. Plain language diff available on at least one rule
6. Business view hides file paths; technical view shows them
7. Compare view shows Verified, Drift, and Undocumented rules

**After implementing**, run:
```bash
playwright install chromium   # if not already installed
pytest tests/unit/ tests/integration/ -v  # fix regressions first
# Start both servers in background
uvicorn app.main:app --port 8000 &
cd frontend && npm run dev &
sleep 5
pytest tests/verify_stage_7.py -v
git add -A && git commit -m "stage 7 complete: PoC done"
```
Fix all failures. Only stop when all pytest runs exit 0 and you have printed:

```
[STAGE 7 COMPLETE — all tests passed]
[POC COMPLETE — all 7 requirements verified]
```
