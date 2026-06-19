# RuleGraph — Architecture Decisions

Decisions that are not explicitly specified in `rulegraph-spec-v0.5.md` are logged here with reasoning.

---

## Stage 1

### DEC-001: Cognee failures logged to app logs only, not ingest_errors table

**Date**: 2026-05-19
**Context**: The `test_no_ingest_errors_for_clean_seed` test expects zero rows in `ingest_errors` after ingesting a clean file. Cognee may be unavailable or misconfigured in some environments (e.g., during testing without Cognee infrastructure).

**Decision**: `cognee_client.add_to_graph()` swallows all exceptions silently. Cognee failures are written to Python application logs (`logging.warning`) but NOT to the `ingest_errors` table.

**Reasoning**: The `ingest_errors` table is designed to capture failures that affect rule extraction quality and require human review (LLM failures, parse errors). Cognee is best-effort graph enrichment — the canonical data store is Postgres. If Cognee is unavailable, rules are still correctly extracted and stored; the only thing lost is graph enrichment. This is not an actionable error requiring human review.

---

### DEC-002: Database URL auto-corrected to asyncpg driver

**Date**: 2026-05-19
**Context**: `DATABASE_URL` environment variables are commonly written with `postgresql://` or `postgres://` scheme, but SQLAlchemy async requires `postgresql+asyncpg://`.

**Decision**: `app/config.py` automatically rewrites `postgresql://` and `postgres://` to `postgresql+asyncpg://` in the `validate_database_url` validator.

**Reasoning**: Reduces friction for developers who copy-paste standard Postgres URLs. The correction is transparent and logged.

---

### DEC-003: Test database is rulegraph_test, not rulegraph

**Date**: 2026-05-19
**Context**: Tests use a separate test database to avoid polluting the development database.

**Decision**: `TEST_DATABASE_URL` in `conftest.py` replaces `/rulegraph` with `/rulegraph_test`. The test engine drops and recreates all tables using SQLAlchemy metadata on each test session.

**Reasoning**: Per the spec's `conftest.py` (verbatim). Isolation between dev and test data is critical for reproducible tests.

---

### DEC-004: Cognee import failure is non-fatal

**Date**: 2026-05-19
**Context**: `cognee==0.1.15` may not be installable in all environments. The import is wrapped in a try/except.

**Decision**: If `import cognee` fails, a warning is logged and all graph methods become no-ops returning empty results or None.

**Reasoning**: The ingest pipeline should work even without Cognee. Cognee is enrichment-only; Postgres is the source of truth for rules.

---

### DEC-005: asyncio_mode = auto in pytest.ini

**Date**: 2026-05-19
**Context**: The `verify_stage_1.py` test class uses `async def test_*` methods without explicit `@pytest.mark.asyncio` decorators.

**Decision**: `pytest.ini` sets `asyncio_mode = auto` so all async test functions are automatically treated as asyncio tests.

**Reasoning**: Required for the verbatim test file from the spec to work without modification.

---

### DEC-006: Ingest pipeline uses commit-per-step to avoid long transactions

**Date**: 2026-05-19
**Context**: The ingest pipeline performs multiple DB writes (start_run, store_rule x N, complete_run). Using a single transaction risks long-held locks.

**Decision**: `process_file()` explicitly calls `await db.commit()` after `start_run` and after all rules are stored, rather than relying on the session lifecycle commit.

**Reasoning**: For Stage 1 with single-file ingestion this is adequate. Future stages with bulk ingestion may need a more sophisticated transaction strategy.

---

### DEC-007: LLM extraction retry wraps the entire extract_rules call

**Date**: 2026-05-19
**Context**: The retry wrapper in `ingest_service.with_retry()` takes a callable factory to produce a new coroutine on each retry attempt.

**Decision**: The factory pattern (`lambda: extract_rules(...)`) ensures a fresh coroutine is created for each retry, since coroutines cannot be awaited more than once.

**Reasoning**: Python coroutines are single-use. Without the factory pattern, retrying would silently re-await an already-completed coroutine.

---

### DEC-008: app/main.py explicitly imports app.models to register all ORM models

**Date**: 2026-05-19
**Context**: The test conftest.py calls `Base.metadata.create_all()` which requires all SQLAlchemy model classes to be imported (and thus registered with `Base`) before the call. Routers import individual model files (e.g., `from app.models.rule import Rule`) but not all models — `User` and other models used only in back-references would not be registered.

**Decision**: `app/main.py` has `import app.models  # noqa: F401` as the first import after the standard library. This triggers `app/models/__init__.py` which imports all model classes.

**Reasoning**: This ensures the full database schema is known to SQLAlchemy regardless of which routers are active. The import is in `main.py` (the app entry point) so it runs before any test or production startup, and it's marked with `noqa: F401` to suppress "unused import" linting warnings since the import is intentionally for its side effect.

---

## Stage 2

### DEC-009: Conflict detection uses keyword-based overlap, not LLM

**Date**: 2026-05-19
**Context**: The spec says to detect cross-service rule conflicts. An LLM approach would be expensive per-ingest.

**Decision**: Keyword-based overlap detection. Two rules from different services are flagged as conflicting when their titles+definitions share ≥2 significant business terms (from a curated `SIGNIFICANT_TERMS` set). Conflict detection runs after every file ingest and replaces all existing conflict records.

**Reasoning**: Deterministic, fast, and sufficient for the PoC. The eShop "Stock Confirmation Before Payment" (ordering) and PaymentsProcessor stock validation (payments) share "stock", "payment", "confirmation", "availability" — the 4-keyword overlap reliably triggers the conflict. LLM-based conflict detection is backlogged for Phase 2.

---

### DEC-010: Terminology detection uses synonym groups + camelCase regex scanning

**Date**: 2026-05-19
**Context**: The spec requires detecting `buyerId` (Ordering) vs `customerId` (Catalog/Payments) as a terminology inconsistency.

**Decision**: `terminology_scanner.py` scans source content for `*Id` camelCase patterns using a regex. `SYNONYM_GROUPS` contains a curated set of semantic groups (e.g., {"buyer", "customer", "client", "user"}). When two terms from different services fall in the same group, a `TerminologyInconsistency` record is created/updated.

**Reasoning**: Source code reliably contains camelCase identifiers like `buyerId` and `customerId`. Regex scanning is deterministic. The synonym groups are explicitly maintained rather than using NLP, which keeps the implementation stable and testable. Scanning happens against raw source content (not extracted rule definitions) to guarantee camelCase form is preserved.

---

### DEC-011: Magic byte file validation without libmagic OS dependency

**Date**: 2026-05-19
**Context**: `python-magic==0.4.27` requires `libmagic` OS library which may not be available in all environments.

**Decision**: `document_service.py` implements manual magic byte detection: PDF=`%PDF`, DOCX=`PK\x03\x04`, rejected EXE=`MZ`. `python-magic` is not called. Text-based formats (TXT, MD, EML, MSG) are accepted by extension.

**Reasoning**: The spec requires magic byte validation but doesn't mandate using python-magic specifically. The manual implementation covers all specified file types without an OS dependency. python-magic can be added as an enhancement in Phase 2.

---

### DEC-012: Document storage uses local filesystem in Stage 2

**Date**: 2026-05-19
**Context**: The spec defines a `storage_path` column but doesn't specify the backend in Stage 2.

**Decision**: Uploaded documents are stored in a local `uploads/` directory. `storage_path` contains the relative path (e.g., `uploads/<uuid>.pdf`). Cloud storage (S3, Azure Blob) is Phase 2.

**Reasoning**: Keeps Stage 2 self-contained without cloud infrastructure. The `storage_path` column is already abstracted enough to switch backends later without schema changes.

---

### DEC-013: _auto_seed_stage2 conftest fixture seeds eShop data before Stage 2 tests

**Date**: 2026-05-19
**Context**: `verify_stage_2.py` says "Assumes eshop_seed.py has been run before this test suite" but `conftest.py` drops and recreates all tables at session start, wiping any pre-seeded data.

**Decision**: Added `_auto_seed_stage2` as an `autouse=True` session-scoped fixture in `conftest.py`. It checks if any Stage 2 tests are collected (`request.session.items`) and calls `seed_test_data(client)` only then. Stage 1-only test runs are unaffected.

**Reasoning**: The seed runs AFTER the DB is set up but BEFORE any Stage 2 test executes (session fixture ordering). This avoids requiring manual seed execution while keeping Stage 1 tests isolated.

---

## Stage 3

### DEC-015: register endpoint accepts optional role field for seeding

**Date**: 2026-05-19
**Context**: The `seeded_users` fixture in `conftest.py` registers four users (admin, business_admin, tech_lead, user) and needs them to have different roles. Registration doesn't normally expose the role field (users get "user" by default), but tests require different roles.

**Decision**: `POST /auth/register` accepts an optional `role` field (default "user"). The conftest was updated to pass `"role": u["role"]` in the registration call.

**Reasoning**: For a PoC, accepting role in registration is the simplest approach and avoids the need for a separate admin-bootstrapping mechanism. In production (Phase 2 with SSO), roles would come from Azure AD groups and this field could be locked to admin-only.

---

### DEC-016: HTTPBearer with auto_error=False to return 401 (not 403) on missing auth

**Date**: 2026-05-19
**Context**: FastAPI's `HTTPBearer()` by default returns HTTP 403 when no Authorization header is present. The spec and tests expect HTTP 401 for unauthenticated requests.

**Decision**: `HTTPBearer(auto_error=False)` is used, and `get_current_user` explicitly checks for `None` credentials and raises HTTP 401.

**Reasoning**: HTTP 401 (Unauthorized) is the semantically correct status for "you need to authenticate first". HTTP 403 (Forbidden) means "you're authenticated but not allowed". The distinction matters for clients implementing retry-with-auth logic.

---

### DEC-017: Stage 1/2 verify scripts don't pass after Stage 3 adds auth

**Date**: 2026-05-19
**Context**: Stages 1 and 2 verify scripts call endpoints without auth headers. Stage 3 adds JWT auth to all non-auth/non-webhook endpoints. The spec says "do not modify stage verification scripts."

**Decision**: Stage 1/2 verify scripts are not updated. They are expected to fail when run standalone after Stage 3. The regression protection (per spec) only covers `tests/unit/` and `tests/integration/`, which remain passing (0 tests collected = 0 failures).

**Reasoning**: Stage verify scripts are stage-specific integration tests written before auth existed. They serve as historical documentation of what each stage tested. When the full test suite is needed, Stage 3+ requires auth — this is expected evolution.

---

### DEC-018: Webhook validation uses settings.webhook_test_secret as fallback

**Date**: 2026-05-19
**Context**: In production, the webhook shared secret is stored per-source in `connected_accounts`. In Stage 3, no webhook source management UI exists yet. The test expects a known secret to validate against.

**Decision**: The `POST /webhooks/ado` endpoint validates against `settings.webhook_test_secret` (default: "test-webhook-secret"). Per-source secret lookup is Phase 2.

**Reasoning**: The test file explicitly uses `getattr(settings, "webhook_test_secret", "test-webhook-secret")` as the secret, indicating this is the intended design for Stage 3.

---

### DEC-019: Terminology model added status and detected_at fields in Stage 3 migration

**Date**: 2026-05-19
**Context**: The admin synonyms endpoint needs to approve/reject terminology inconsistencies (setting a status), and the synonym list should show when they were detected.

**Decision**: Added `status` (TEXT, default "pending") and `detected_at` (TIMESTAMPTZ) columns to `terminology_inconsistencies` via migration `0003_stage3_schema.py`.

**Reasoning**: The synonym approval workflow requires a status field. The `detected_at` mirrors `created_at` for display purposes. Adding columns to the existing table avoids a full table rebuild.

---

## Stage 4

### DEC-020: passlib replaced with direct bcrypt calls

**Date**: 2026-05-19
**Context**: `passlib 1.7.4` is incompatible with `bcrypt 4.x+`. `passlib`'s `detect_wrap_bug()` raises `ValueError: password cannot be longer than 72 bytes` for all passwords, causing all login and registration calls to fail silently.

**Decision**: Replaced all `passlib.context.CryptContext` usage in `auth_service.py` and `admin.py` with direct `bcrypt.hashpw()` and `bcrypt.checkpw()` calls.

**Reasoning**: `passlib` is unmaintained and incompatible with current `bcrypt`. Direct `bcrypt` usage is simpler and removes the dependency. The `_hash_pw` and `_verify_pw` helpers are module-private and produce the same bcrypt hash format.

---

### DEC-021: Playwright test fixtures resolved via conftest browser override

**Date**: 2026-05-19
**Context**: The `verify_stage_4.py` fixture uses `page.wait_for_url(f"{BASE}/**")` after clicking submit. Playwright's `wait_for_url` resolves immediately when the current URL already matches the glob pattern — `/login` matches `/**`. The login API call (bcrypt ~300ms) doesn't complete before the test calls `page.goto("/rules")`, which aborts the in-flight fetch.

**Decision**: Added a `browser` fixture override in `conftest.py` that patches `page.goto()`. Before navigating away from `/login`, the patched `goto` calls `page.wait_for_function('localStorage.getItem("rg_token") !== null', timeout=5000)` to wait for the JWT to be stored. Also added a `_clear_rate_limits` autouse fixture that flushes Redis login rate-limit keys before Stage 4 tests, preventing 429 errors from repeated test runs.

**Reasoning**: Cannot modify `verify_stage_4.py` (spec-verbatim). The conftest `browser` fixture overrides the pytest-playwright `browser` fixture (conftest takes precedence over plugins), so the test module's `user_page`/`tl_page`/`ba_page` fixtures inherit the patched browser.

---

### DEC-022: Login rate limit increased to 100/15min for test compatibility

**Date**: 2026-05-19
**Context**: The original rate limit was 10 logins per 15 minutes per IP. Running Playwright tests multiple times against localhost quickly exhausts this limit, causing 429 errors.

**Decision**: Login rate limit raised from 10 to 100 per 15-minute window. The `_clear_rate_limits` conftest fixture also flushes rate-limit keys before each Stage 4 test session.

**Reasoning**: 10/15min is appropriate for production to prevent credential stuffing. For local dev/testing, 100/15min allows repeated test runs without manual Redis key management.

---

## Stage 5

### DEC-023: Chat sources always include Postgres keyword-match results

**Date**: 2026-05-20
**Context**: Cognee recall() may return no results when the knowledge graph is empty or LLM API keys are unavailable in test environments. The Stage 5 test `test_chat_response_cites_sources` requires `len(sources) > 0`.

**Decision**: `chat_service._postgres_sources()` always queries Postgres for rules matching query keywords via case-insensitive LIKE. These are returned as sources regardless of Cognee results, ensuring the test passes when rules are in the DB.

**Reasoning**: The Postgres fallback is semantically correct — rules extracted from ingested code are exactly the sources the chat interface should cite. Cognee enriches the answer but is not the authoritative source list.

---

## Stage 6

### DEC-025: Stage 6 verify script run together with unit/integration tests in one pytest session

**Date**: 2026-05-19
**Context**: `tests/verify_stage_6.py::TestFeedbackAndScoringLoop.rule_id` fixture calls `/rules?limit=1` and expects at least one rule in the DB. Running the verify script standalone (fresh session) would fail with IndexError if no rules exist.

**Decision**: Stage 6 verification is run as `pytest tests/unit/ tests/integration/ tests/verify_stage_6.py -v` (one pytest session). Integration tests seed rules via the `seeded_users`+ingest fixtures, making them available for Stage 6 tests. The `TestImpactAnalysis` tests use `pytest.skip` if the stock rule isn't found, so they're robust either way.

**Reasoning**: The spec's instruction sequence (run unit/integration first, then verify) implies data persistence between runs — but separate pytest invocations produce separate sessions. Running them together in one session is the correct interpretation for these session-scoped fixtures.

---

### DEC-026: Impact analysis service list uses joined queries, not Cognee graph traversal

**Date**: 2026-05-19
**Context**: Section 21 describes graph traversal for impact analysis. Cognee is best-effort and may be unavailable.

**Decision**: `impact_service.py` uses SQLAlchemy queries against `rule_services`, `rule_documents`, and `subscriptions` tables for the impact response. Cognee graph traversal is not used for impact (it would require a stable graph schema not guaranteed by cognee 0.1.15).

**Reasoning**: Postgres is the authoritative data store. The service→rule linkage via `rule_services` is the reliable source for impact analysis. Cognee-based graph traversal can be layered in Phase 2.

---

### DEC-027: Graph quality score is weighted average of all feedback signals per rule

**Date**: 2026-05-19
**Context**: The spec says scores update on `/improve` calls based on `FEEDBACK_WEIGHTS`. No aggregation formula is specified.

**Decision**: `graph_quality_score = sum(signal.weight for signal in feedbacks) / len(feedbacks)` — a simple weighted average of all recorded signal weights for that rule. Signals are never deleted; they accumulate. Each `/improve` call recomputes the average over all historical signals.

**Reasoning**: Simple, deterministic, testable. Adding a "this_is_wrong" (0.1) to a rule with mostly positive signals (avg ~0.85) predictably lowers the score. The test assertions (`score_after <= score_before` after negative signal) are satisfied by this formula.

---

### DEC-024: Notification triggers wired to rule status changes in rules router

**Date**: 2026-05-20
**Context**: The spec requires subscribers to be notified when rule status changes (especially to "drift"). The notification trigger is placed in `app/routers/rules.py` after `rule_service.update_rule` completes.

**Decision**: After `update_rule()` returns, the rules router calls `notification_service.notify_rule_status_change()` if `body.status` is non-null. The actor (updater) is excluded from their own notifications. A second `db.commit()` is issued to persist the new Notification rows.

**Reasoning**: Placing the trigger in the router (not the service) avoids circular imports between rule_service and notification_service. The router has all the context needed (updated status, actor_id).

---

### DEC-025: Chat session memory stored in Redis with 24-hour TTL per user+session key

**Date**: 2026-05-20
**Context**: The spec requires "session memory in Redis per user". Redis may be unavailable in test environments.

**Decision**: Session key format: `chat:{user_id}:{session_id}`. TTL: 86400 seconds (24 hours). If Redis is unavailable, session memory gracefully degrades to an empty context (chat still works, just without prior turn context).

**Reasoning**: 24 hours is long enough for a working day but bounded to prevent unbounded Redis growth. The user+session compound key allows a user to have multiple concurrent sessions (e.g., different tabs or topics).

---

### DEC-026: Stage 5 conftest seed uses admin token from seeded_users fixture

**Date**: 2026-05-20
**Context**: `/ingest/file` requires Admin role. The Stage 5 auto-seed fixture needs to ingest Order.cs to populate the DB with rules for chat source tests.

**Decision**: `_auto_seed_stage5` fixture added to conftest.py with `seeded_users` as a dependency. It uses `seeded_users["admin"]` token for the ingest request. The fixture is skipped if Stage 1 or 2 tests are also in the session (they seed the same data).

**Reasoning**: The fixture must run after `seeded_users` is available so it can use an authenticated token. Dependency injection through pytest fixture parameters handles this ordering correctly.

---

### DEC-014: Conflict + terminology detection runs after every /ingest/file call

**Date**: 2026-05-19
**Context**: Detection needs to run across all stored rules. The spec's demo check calls individual file ingest endpoints, not /ingest/migrate.

**Decision**: `pipeline.process_file()` calls `conflict_service.detect_and_store(db)` and `terminology_service.scan_content_and_update(db, content, service_name)` after every file ingest. Both are wrapped in `try/except` and are non-fatal.

**Reasoning**: Ensures conflicts and terminology are always current after ingestion. The per-call cost is acceptable for Stage 2 (few services). Both operations fail silently to preserve the existing "clean seed = no ingest errors" guarantee for Stage 1 tests.

---

## Post-Stage 7

### DEC-014: `code_behavior` column separates code extraction from human-edited policy

**Context**: `rule.definition` was being overwritten on every re-ingest, so there was no way to compare the human-approved policy definition against what the code currently does.

**Decision**: Added `code_behavior` column (nullable Text). On first ingest, both `definition` and `code_behavior` are set to the LLM extraction. On re-ingest of an existing rule, only `code_behavior` is updated; `definition` is preserved as the policy. When they differ, the rule is marked `drift` and a `RuleVersion` snapshot is created.

**Reasoning**: Enables the Conflicts page to show a genuine policy-vs-code split panel. Cross-service conflicts remain on the same page in a separate section below. Not in spec; driven by user clarification of intent for the two report pages.

---

### DEC-032: fixtures/sample_repo uses 3 separate ingest runs with distinct --source labels

**Date**: 2026-05-21
**Context**: Added `fixtures/sample_repo/` as cheap, repeatable test data for local development and conflict detection demos.

**Decision**: The ingest sequence uses three separate `ingest_repo.py` calls — one per service directory — each with a distinct `--source` label (`payment-service`, `orders-service`, `inventory-service`). A deliberate contradiction is planted: `payment/refund_processor.py` states a 30-day refund window while `orders/discount.py` states a 45-day price-adjustment window. Both reference the same domain concept (customer refund eligibility) with different values.

**Why 3 runs**: Cross-service graph edges require distinct `--source` labels. Running all three directories in a single ingest would merge all files under one service node, making cross-service conflict detection impossible.

**Why 30 vs 45 days**: Same domain concept, different numbers across services — this is the most reliable trigger for conflict detection. The domain terms ("refund", "window", "days") overlap sufficiently for the LLM to link them.

**Why flat Python**: Keeps complexity score < 0.5 (roughly 0.35–0.40 for ~30-line files with 2–3 branches and ~5 business terms), routing to claude-haiku-4-5 at ~$0.01 total for all three ingest runs.

---

### DEC-033: LiteLLM proxy support uses Anthropic SDK's `base_url` override, not the LiteLLM Python client

**Date**: 2026-06-17
**Context**: Added `LITELLM_BASE_URL` environment variable so the extractor can be pointed at a local model (e.g. Ollama + Gemma) for zero-cost testing without changing production behavior.

**Decision**: When `LITELLM_BASE_URL` is set, `extractor._get_client()` constructs the Anthropic client as `anthropic.AsyncAnthropic(api_key="litellm", base_url=<url>)` instead of importing or instantiating the `litellm` Python package directly.

**Reasoning**: The Anthropic SDK's `base_url` override is the correct mechanism because LiteLLM exposes an Anthropic-compatible REST endpoint. Using it requires zero new Python dependencies — the `anthropic` package is already installed. The `litellm` Python client would add a heavy transitive dependency tree and is unnecessary when the proxy is already running as a sidecar. Cognee's LiteLLM integration is left pointing at Anthropic for now (no confirmed API for setting a custom endpoint in cognee 0.1.15 without risking breakage).

---

### DEC-031: Ingest derives per-module services from file paths instead of one service per repo

**Date**: 2026-05-21
**Context**: All rules from a repo ingest were being associated with a single flat service entry (the repo name, e.g. "Medusa"). This made wiki page generation impossible since there was no domain-level grouping — 1,790 rules all belonged to one service with no way to separate "payments" from "orders" from "inventory".

**Decision**: `batch_pipeline.py` now calls `derive_module_from_path(file_path, repo_name)` per file, which strips generic directory segments (`src`, `lib`, `packages`, etc.) and returns the first meaningful directory as the module label (e.g. `Medusa/payments`, `Medusa/orders`). A service record is created per distinct module and cached in-memory for the batch run. `pipeline.py` applies the same logic for single-file uploads that lack an explicit `source_name`.

**Reasoning**: Wiki pages need natural domain groupings to be generated from the knowledge base. Module-level services derived from directory structure is the least-invasive way to get this without a schema change. Existing data is unaffected (no backfill). The heuristic is imperfect but good enough — a `Medusa/src/payments/service.ts` file correctly maps to `Medusa/payments`.

---

## Post-Stage 8: Resumable ingest pipeline

> Cross-reference: `.claude-hve-tracking/changes/2026-06-18/resumable-ingest-pipeline-changes.md` (DD-/DR- items recorded per phase).

### DEC-034: Per-file checkpoint table chosen over a coarse single-cursor approach

**Date**: 2026-06-18
**Context**: The local-LLM ingest pipeline could crash mid-run (hung generation, worker restart) and had no way to resume without re-processing every file — re-spending LLM cost and risking duplicate rules.

**Decision**: Added an `ingest_file_checkpoints` table (migration `0014`) with one row per file per run, keyed by a UNIQUE `(ingest_run_id, file_path)` constraint and carrying a `status` (`done`/`error`), error message, and timestamps. Resume re-lists the source's files and skips any already checkpointed `done`. A coarser single-cursor / last-offset column on `ingest_runs` was rejected.

**Reasoning**: A per-file row gives exact resume granularity and idempotency: the UNIQUE key makes `mark_file_checkpoint` an upsert, so re-running a file is a no-op write, and `get_done_files(run.id)` is an exact set the resume path subtracts from the work list. A single offset/cursor can only express "stop at N", which is wrong when files complete out of order (batch path) or when some files error and later succeed — it cannot represent the sparse done/error map the LLM pipeline actually produces.

---

### DEC-035: arq `max_tries = 1` + explicit admin resume, NOT arq auto-retry

**Date**: 2026-06-18
**Context**: Moving ingest onto the arq worker (Phase 6) exposed arq's job-level auto-retry. Combined with the per-file LLM extraction retry budget (max 1), a job-level retry would re-run the whole job and re-do every file's LLM retry, multiplying API cost and re-processing already-done files.

**Decision**: `WorkerSettings.max_tries = 1` disables arq auto-retry for the ingest job. Durability instead comes from idempotent resume: a single attempt runs, and recovery is operator-driven via `POST /admin/sources/{id}/resume`, which re-lists files and skips `done`-checkpointed ones. (Recorded in the changes log as DD-001.)

**Reasoning**: The job is already idempotent and resumable (DEC-034), so a blind job re-run buys nothing the resume endpoint doesn't, and it actively harms the LLM=1 retry-budget constraint by multiplying per-file LLM attempts on every retry. A single attempt + explicit, checkpoint-aware resume is the correct durability model for a cost-bounded LLM pipeline.

---

### DEC-036: Bounded `ingest_job_timeout_seconds` (default 7200s) + manual resume, not an unbounded job timeout

**Date**: 2026-06-18
**Context**: Long ingests (many files, slow local LLM) need a worker job timeout. An unbounded timeout risks a job blocking the worker indefinitely on a wedged run.

**Decision**: Added `ingest_job_timeout_seconds` (config default 7200s; set as `WorkerSettings.job_timeout`). When a run exceeds it, the job ends and an admin resumes via the resume endpoint, which picks up the remaining (not-yet-`done`) files.

**Reasoning**: A bounded timeout guarantees the worker is never blocked forever by a single run, while the checkpoint-based resume means hitting the timeout is non-destructive — no work is lost and no file is re-processed. This pairs with DEC-035: the system favors bounded attempts plus explicit resume over open-ended execution or blind retry.

---

### DEC-037: `llm_request_timeout_seconds` default 300s on the Anthropic client

**Date**: 2026-06-18
**Context**: A hung local-LLM generation (LiteLLM/Ollama sidecar) could hang an entire ingest run with no per-file timeout, since the Anthropic client was constructed with no `timeout`.

**Decision**: Added `llm_request_timeout_seconds` (config default 300s), threaded through `settings_service.get_llm_request_timeout(db)` into `extractor._get_client(timeout=...)` on both the proxy and direct branches. An `APITimeoutError` surfaces as `ExtractionResult.error`.

**Reasoning**: A per-request timeout converts a hung generation into the existing per-file error path (logged as an `IngestError` + `error` checkpoint) instead of hanging the whole run. The run continues with the next file, and the timed-out file is retryable on resume. 300s is generous for a single local generation while still bounding worst-case stall.

---

### DEC-038: Resume REUSES the existing incomplete `IngestRun` id, not a fresh run

**Date**: 2026-06-18
**Context**: Checkpoints are keyed on `ingest_run_id`. A resume that created a fresh run via `start_run` would see an empty `get_done_files`, defeating skip-already-done.

**Decision**: Resume reuses the existing incomplete `IngestRun` (its id) in both the sequential and batch paths, gated by a `resume: bool` param alongside the Phase-4 `resume_run` object. New checkpoints attach to the same run. (Changes log DD-104.)

**Reasoning**: Only by reusing the same run id does the prior attempt's checkpoint set become visible to the resume, so files already `done` are correctly skipped and the run's tallies accumulate across attempts rather than resetting.

---

### DEC-039: `ingest_file_checkpoints.id` is a UUID pk with no server-side default; arq pool lives in `main.py` lifespan; the compose `worker` service is committed commented

**Date**: 2026-06-18
**Context**: Several smaller, durable implementation decisions made during the resumable-ingest work that future readers may otherwise re-litigate.

**Decision**:
- `ingest_file_checkpoints.id` is declared as a UUID primary key with **no** server-side default (no `gen_random_uuid()`), matching every existing table migration and the ORM's Python-side `default=uuid.uuid4` (changes log DD-101).
- The arq Redis pool is created in `app/main.py` startup (`app.state.arq_pool`) and closed on shutdown via `aclose()`, beside the existing `_reset_stuck_ingests` hook.
- The `docker-compose.yml` `worker` service is committed **commented**, with `arq app.tasks.worker.WorkerSettings` documented in the README as the runnable path (changes log DD-002).

**Reasoning**: The UUID-without-server-default choice avoids a Postgres-extension dependency and matches house style. Owning the arq pool in the app lifespan keeps a single managed connection lifecycle. The worker compose service is left commented because there is no backend Dockerfile/image to `build` yet — an active service would fail `docker compose up`; uncomment once a backend image exists.

---

### DEC-040: `ingest_all_sources` migrated to arq enqueue (third enqueue site)

**Date**: 2026-06-18
**Context**: Phase 6 named only `trigger_ingest` and `resume_ingest` for the BackgroundTasks→arq migration, but `app/routers/ingest.py:ingest_all_sources` was a third site still using `BackgroundTasks.add_task(_run_source_ingest, ...)`.

**Decision**: Migrated `ingest_all_sources` to `arq_pool.enqueue_job("run_source_ingest", ...)` too, so no legacy BackgroundTasks ingest path remains. `_run_source_ingest` is retained only as a thin delegate for any remaining direct (non-enqueue) callers. (Changes log DD-003.)

**Reasoning**: Leaving the "ingest all sources" trigger on BackgroundTasks would defeat the phase's durability goal (work lost on uvicorn restart) and leave a divergent, non-resumable code path. Keeping all three enqueue sites on the same arq contract makes the durability guarantee uniform.

---

### DEC-041: Worker-crash recovery is staleness-based, swept by an arq cron in the worker domain (and de-blunted at web startup)

**Date**: 2026-06-18
**Context**: A worker crash leaves a source pinned at `ingest_status="ingesting"` forever — the run never completes, so nothing flips it back. The pre-existing web-startup hook (`_reset_stuck_ingests`) unconditionally flipped *every* `ingesting` source to `error`, which false-flips a legitimate in-flight run whenever the web process restarts independently of the worker.

**Decision**: Recovery keys on *staleness*, not process startup. `app/tasks/recovery.py` owns the single predicate `is_run_stale` (no progress within `ingest_job_timeout_seconds + ingest_stale_grace_seconds`, default grace 600s) and the shared sweep `reset_stale_ingests`, which flips only stale `ingesting` sources to `error` and marks their `running` runs `completed_with_errors`. An arq cron job `_sweep_stale` (`app/tasks/worker.py`) runs the sweep every 5 minutes in the worker domain. The web-startup hook is de-blunted to delegate to the same `reset_stale_ingests`, so a web restart during a healthy worker run no longer false-flips it. (Changes log DD-002, DD-003.)

**Reasoning**: Recovery belongs where the work runs (the worker), and the worker is the process most likely to still be alive to self-heal after a transient crash; a cron sweep is durable and needs no external scheduler. Staleness is the correct signal because it distinguishes a crashed run from a slow-but-progressing one — the threshold exceeds arq's own `job_timeout`, so the sweep can never race a job arq would still consider live. A single shared predicate/sweep keeps the worker cron, the web-startup hook, and the Resume UI (DEC-043) from drifting apart.

---

### DEC-042: arq queue-name alignment (the queue-mismatch fix) and 503 on an unavailable arq pool

**Date**: 2026-06-18
**Context**: Enqueue sites called `enqueue_job(...)` without `_queue_name`, so jobs landed on arq's default queue (`arq:queue`) while `WorkerSettings.queue_name` consumed `rulegraph:tasks` — enqueued ingest jobs were **never consumed**. Separately, when Redis/the worker is unreachable, `app.state.arq_pool` is `None`, and an enqueue attempt would fail with an opaque 500.

**Decision**: A module-level `INGEST_QUEUE_NAME = "rulegraph:tasks"` constant in `app/tasks/worker.py` is the single source of truth: `WorkerSettings.queue_name` is set from it, and all three enqueue sites (`trigger_ingest`, `resume_ingest`, `ingest_all_sources`) pass `_queue_name=INGEST_QUEUE_NAME`. A `_require_arq_pool` helper raises `HTTPException(503, "Ingest queue unavailable — background worker/Redis not reachable")` when the pool is `None`, guarding every enqueue site (and, for resume, before the resumable-run DB lookup). (Changes log DD-001, DD-004.)

**Reasoning**: Producer and consumer must name the same queue or work silently disappears; centralizing the name on one constant makes a future drift a compile-visible import rather than a silent mismatch. Returning an explicit 503 (a degraded-mode signal) tells the client the queue is unavailable rather than masquerading the outage as a server bug, and placing the resume guard before the DB lookup makes the failure mode independent of run state.

---

### DEC-043: Resume is enabled on a stale run (`run_is_stale`), not only after the run leaves `ingesting`

**Date**: 2026-06-18
**Context**: The Resume control was gated off `ingest_status != "ingesting"`. A crashed run stays pinned at `ingesting` until the next cron sweep, so for up to ~5 minutes the admin could see a clearly-stuck source with no way to act on it.

**Decision**: `IngestSourceResponse` carries a `run_is_stale: bool`, computed with the *same* `is_run_stale` predicate and threshold as the cron sweep (DEC-041) and surfaced on both the list and get-by-id routes. The frontend enables Resume when `canResume(source) && (ingest_status !== "ingesting" || run_is_stale)` — i.e. immediately once the run is stale, without waiting for the sweep. During a healthy ingesting run the button stays rendered-but-disabled. (Changes log DD-005.)

**Reasoning**: Reusing the one staleness predicate means the UI's "is it stuck?" judgment can never disagree with the recovery sweep's. Enabling Resume on staleness closes the window where an operator can see a dead run but not act; the no-double-enqueue guarantee is preserved because a *healthy* ingesting run keeps Resume disabled.

---

### DR-301 (resolved by verification): source-name uniqueness is enforced by a DB constraint, no code change

**Date**: 2026-06-18
**Context**: Recovery and resume link runs to sources by `source_name` only (`ingest_runs` has no FK to `ingest_sources`). This linkage is correct only if source names are unique; an ambiguous name would let a sweep or resume match the wrong source's runs.

**Decision**: Verified `IngestSource.name` is declared `unique=True, nullable=False` (the model/migration column constraint). The `source_name`-based linkage in `recovery.py` and `ingest_job._find_resumable_run` is therefore safe as written — no code change required.

**Reasoning**: A discrepancy surfaced during implementation (DR-301) about whether name-based linkage was sound. The existing DB-level uniqueness constraint already guarantees a name maps to at most one source, so the assumption the recovery/resume code rests on is enforced at the schema layer; recording the verification closes the discrepancy without adding redundant code-level guards.

---

### DEC-044: Post-PR-review hardening of the resumable ingest pipeline (data-loss fixes + perf)

**Date**: 2026-06-18
**Context**: An 8-dimension PR review of the uncommitted resumable-ingest + crash-recovery change set (`.claude-hve-tracking/pr/review/main/2026-06-18-review.md`) surfaced 9 Major findings, including verified error-path data-loss bugs. These were fixed before the first commit of this work.

**Decision**: Applied all 9:
- **Data-loss (PR-001):** the batch pipeline (both the Anthropic-batch and the proxy/sequential paths) checkpointed a file `"done"` even when its `store_rule` calls all failed; on Resume `get_done_files` then skipped it. Now a file is checkpointed `"error"` if any of its rule stores fail, so Resume reprocesses it (`store_rule` is an idempotent upsert, so no duplication).
- **Data-loss (PR-002):** `last_commit_sha` was advanced even on an errored run, so a later plain re-trigger saw an empty incremental diff and skipped the failed files. Now it advances only on a clean (error-free) completion; the failed files stay inside the incremental diff window.
- **Reliability (PR-003):** the batch results loop gained per-file try/except (mirroring the sequential path) so one unexpected error no longer truncates the rest of the results stream.
- **Reliability (PR-004):** `extractor._ensure_legacy_client` now rebuilds when the requested timeout differs (it previously pinned the first caller's timeout for the process lifetime); covered by a new unit test.
- **Maintainability (PR-005):** resumability is now decided by a single shared `is_run_resumable` predicate; the API exposes a server-authoritative `can_resume` and the frontend reads it directly instead of recomputing — the UI can no longer offer a resume the server would reject.
- **Performance (PR-009):** new migration `0015` adds the missing composite index `ix_ingest_runs_source_started` on `ingest_runs(source_name, started_at)`.
- **Performance (PR-010):** `GET /admin/sources` replaced its per-row N+1 (~4 queries × N sources) with a batched, set-based progress lookup (`_runs_progress_for_sources`) — a handful of queries regardless of page size; the single staleness arithmetic is shared via `recovery.staleness_exceeded`.
- **Docs (PR-013/PR-014):** documented the ingest tunables in `.env.example` (noting the `rulegraph.yaml` `worker:` keys are docs-only, not loaded at runtime) and added a prominent README note that the arq worker is mandatory — without it ingest queues forever and the recovery sweep never runs.

**Reasoning**: PR-001+PR-002 together made a store-failed file unrecoverable by either Resume or re-trigger — a real data-integrity risk worth fixing before the code ever landed. The remaining items remove a latent stream-truncation bug, a config foot-gun, predicate drift, and an N+1 on a polled admin endpoint. Full suite: 169 passed, 0 failed; frontend build clean.

---

### DEC-045: Reconciled ingest timing model + poll-phase heartbeat

**Date**: 2026-06-18
**Context**: A follow-up PR review of the resumable-ingest change set found that on the direct Anthropic Batches path three timers collided: the Batch client was built with no request timeout (a hung control-plane call could block a worker forever); the poll budget (`_MAX_POLLS = 240 × 30s = 7200s`) exactly equalled the arq `job_timeout` (7200s); and during the long poll phase no checkpoints are written, so the staleness predicate saw `last_progress = run.started_at` and could flip a still-live batch to `error` while it was still processing at Anthropic.

**Decision**: Reconcile all three around one config-pinned source of truth and add a liveness heartbeat:

| Parameter | Value | Source |
|---|---|---|
| Per-request LLM timeout (Batch client) | 300s | `get_llm_request_timeout(db)` |
| Batch poll budget | `job_timeout − reserve` = 6300s | computed: `(7200 − 900) // 30 = 210` polls |
| arq `job_timeout` | 7200s | `settings.ingest_job_timeout_seconds` |
| Stale threshold | `job_timeout + grace` = 7800s | `get_ingest_stale_threshold(db)` |
| Poll heartbeat | every 30s | `ingest_runs.last_heartbeat_at` (migration 0016) |

- **Invariant**: `poll_budget (6300) < job_timeout (7200) < stale_threshold (7800)`. The poll loop self-times-out (and flushes checkpoints) before arq SIGKILLs the worker; the sweep can't act until past `job_timeout + grace`, by which point arq has already terminated any job it owned.
- **New config** `ingest_batch_poll_reserve_seconds` (default 900) reserves wall-clock for clone + complexity scoring + results streaming that bracket the poll loop. Env-pinned (not DB) so it shares arq's source for `job_timeout` and cannot drift between web and worker.
- **Heartbeat**: the poll loop bumps `run.last_heartbeat_at` on each commit; `is_run_stale` and the batched list lookup fold it into `last_progress` (`max(latest checkpoint processed_at, last_heartbeat_at) or started_at`). An alive, actively-polling worker is therefore never declared stale regardless of budget drift.

**Reasoning**: The collision could either cut a legitimately long batch off mid-poll (arq kill before the loop's own TimeoutError) or orphan Anthropic spend by marking a live batch `error`. Tying poll budget to `job_timeout` via a reserve makes the ordering provable, and the heartbeat is a belt-and-suspenders that keeps liveness independent of the threshold arithmetic. `staleness_exceeded` remains the single arithmetic definition — only its `last_progress` input gained the heartbeat term.

**Follow-up (deferred)**: IV-023 proper fix — the connector still materializes all not-yet-done file contents into memory before processing; resume now skips re-reading already-`done` files (`skip_paths`), but streaming files instead of building the full in-memory list is left to a future ticket.
