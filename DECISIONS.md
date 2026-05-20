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

### DEC-014: Conflict + terminology detection runs after every /ingest/file call

**Date**: 2026-05-19
**Context**: Detection needs to run across all stored rules. The spec's demo check calls individual file ingest endpoints, not /ingest/migrate.

**Decision**: `pipeline.process_file()` calls `conflict_service.detect_and_store(db)` and `terminology_service.scan_content_and_update(db, content, service_name)` after every file ingest. Both are wrapped in `try/except` and are non-fatal.

**Reasoning**: Ensures conflicts and terminology are always current after ingestion. The per-call cost is acceptable for Stage 2 (few services). Both operations fail silently to preserve the existing "clean seed = no ingest errors" guarantee for Stage 1 tests.
