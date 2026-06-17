# RuleGraph — Future Implementation TODOs

## Human-editable wiki

The generated wiki (auto-synthesized from ingested rules) is implemented.
The following human-editing layer is deferred:

### Schema additions needed
- Add `human_content` (Text, nullable) to `wiki_pages` table
- Add `has_conflict` (Boolean, default false) to `wiki_pages` table
- Add `wiki_page_versions` table:
  - `id` (UUID PK)
  - `wiki_page_id` (FK → wiki_pages)
  - `content_type` ("generated" | "human")
  - `content` (Text)
  - `changed_by` (FK → users, nullable)
  - `changed_at` (DateTime)
  - `change_note` (Text, nullable)
- New Alembic migration for the above

### Backend
- `PUT /wiki/{id}` — save human edits to `human_content`, create a
  `wiki_page_versions` row (content_type="human"), set `has_conflict=false`
- `POST /wiki/{id}/resolve-conflict` — accept body `{ resolution: "generated" | "human" | "merged", content?: str }`:
  - "generated": copy `generated_content` → clear `human_content`, set `has_conflict=false`
  - "human": keep `human_content` as-is, set `has_conflict=false`
  - "merged": write provided `content` to `human_content`, set `has_conflict=false`
- On wiki regeneration: if `human_content` is set on an existing page, set
  `has_conflict=true` instead of overwriting — do NOT touch `human_content`
- Add `human_content` and `has_conflict` to `GET /wiki/{id}` response
- Add `wiki_page_versions` to export/import/delete (admin.py `_EXPORT_TABLES`,
  delete sequence, and `_CONFLICT_TARGET`)

### Frontend
- `WikiEntry`: show "Edit" button (all authenticated users, per spec Section 7)
- Edit mode: swap definition block for `WikiEditor` component (already built),
  pre-populated with current `human_content ?? generated_content`
- On save: call `PUT /wiki/{id}`, exit edit mode, refetch entry
- Conflict banner: when `has_conflict=true`, show a prominent banner above
  the definition block:
  > "The AI has updated the generated content for this page since your last
  > edit. Review and resolve below."
- Conflict resolution UI: side-by-side diff (generated vs human) with three
  buttons — "Keep mine", "Use AI version", "Edit merged version"
- Version history panel (collapsible, same pattern as rules lineage):
  shows each `wiki_page_versions` row with content_type badge, timestamp,
  changed_by, change_note, and a collapsed preview of the content
- `WikiBrowser`: show a conflict indicator badge on cards where `has_conflict=true`

---

## Plan: fixtures/sample_repo — Cheap Ingest Testing

### What already works (no changes needed)
- `--path <DIR>` is fully implemented in `scripts/ingest_repo.py` (line 153)
- Conflict detection and terminology scan run automatically after every file
- Pipeline skips files scoring 0.0 complexity — our files must score > 0.0 but < 0.5

### Complexity score target
A 30-line flat Python file with ~3 `if` branches and ~5 business terms scores roughly:
- `line_score`     = 0.0  (< 100 lines)
- `branch_score`   ≈ 0.13 (3 branches / 30 lines × 2.0)
- `business_score` ≈ 0.15 (5 of ~50 terms × 1.5)
- `nesting_score`  ≈ 0.10 (depth 1–2)
- **Total ≈ 0.38** → routes to claude-haiku-4-5 → ~$0.01 total

### The deliberate contradiction
Both rules reference the same domain concept (refund window) from different services:
- `payment/refund_processor.py` — "Refund requests must be submitted within **30 days**"
- `orders/discount.py`         — "Customers may request a refund or price adjustment within **45 days**"

### Deliverables (5 source files + 2 doc updates)

1. `fixtures/sample_repo/payment/validators.py` (~30 lines)
   - CVV length check (must be 3–4 digits)
   - Fraud threshold rule (flag if amount > 1000 and account not verified)

2. `fixtures/sample_repo/payment/refund_processor.py` (~30 lines)
   - Refund SLA rule (process within 5 business days)
   - **30-day refund window** ← plants the contradiction

3. `fixtures/sample_repo/orders/workflow.py` (~30 lines)
   - Approval required for orders above $500
   - 24-hour cancellation window after order placement

4. `fixtures/sample_repo/orders/discount.py` (~30 lines)
   - Discount stacking rule (max one promotional code per order)
   - **45-day price-adjustment window** ← the contradiction

5. `fixtures/sample_repo/inventory/monitor.py` (~30 lines)
   - Reorder triggered when stock falls below 10 units
   - Backorder display rule (show estimated date if stock = 0)

6. `fixtures/sample_repo/README.md`
   - One paragraph: synthetic test data, not production code
   - The 3-command ingest sequence (see below)

7. Main `README.md` — add Step 8 with 3-command ingest sequence:

       python scripts/ingest_repo.py --path fixtures/sample_repo/payment   --source payment-service  --login admin@test.com Test1234!
       python scripts/ingest_repo.py --path fixtures/sample_repo/orders     --source orders-service   --login admin@test.com Test1234!
       python scripts/ingest_repo.py --path fixtures/sample_repo/inventory  --source inventory-service --login admin@test.com Test1234!

8. `DECISIONS.md` — log:
   - Why 3 separate runs (cross-service graph edges require distinct `--source` labels)
   - Why 30 vs 45 days (same domain concept, different numbers → reliable conflict detection trigger)
   - Why flat Python (keeps complexity score < 0.5 → haiku tier)

### Out of scope
- No changes to `scripts/ingest_repo.py`
- No new tests (fixture data, not application code)
- No changes to app models, routers, or services

---

## Fix: idle-in-transaction sessions blocking DDL / hanging the site

**What happened:** Running `alembic upgrade head` while the app is live can deadlock the site. The `ALTER TABLE` needs an `AccessExclusiveLock`; it waits for existing transactions to finish; PostgreSQL queues new queries behind the waiting lock; the frontend's 3s poll loop stacks up connections all stuck "idle in transaction"; everything hangs until manual `pg_terminate_backend()` intervention.

Four fixes to make when ready:

**1. Engine — `app/database.py`**
Add `pool_recycle=300` and `connect_args={"server_settings": {"idle_in_transaction_session_timeout": "30000"}}` to the engine. The timeout tells Postgres to auto-kill any session idle in transaction for >30s — this alone would have resolved today's hang automatically.

**2. Background task sessions — `app/routers/sources.py`, `app/routers/wiki.py`, `app/main.py`**
The bare `async with async_session_factory() as db:` blocks don't explicitly rollback on exception — they rely on pool-level reset behavior. Bigger risk: in `_run_source_ingest`, the `except` block calls `db.commit()` to persist the error state, but if the session is already in a DB error state from an earlier failed flush, that commit also fails and the connection is returned dirty. Fix: call `db.rollback()` first, then open a fresh write for the error state.

**3. Migrations — every `alembic/versions/*.py` touching a busy table**
Add `op.execute("SET lock_timeout = '3s'")` at the top of `upgrade()`. If the lock can't be acquired quickly, the migration raises immediately instead of queuing and cascading.

**4. Process (simplest)**
Stop uvicorn before running migrations: `pkill -f uvicorn` → `alembic upgrade head` → restart. Items 1 and 3 are the highest-leverage code changes.
