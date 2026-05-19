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
