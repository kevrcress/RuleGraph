#!/usr/bin/env python3
"""
Seed the database with realistic fixture data for local testing.
No AI API calls required — all data is static.

Usage:
    python scripts/seed_fixtures.py           # seed (skips if tables already have data)
    python scripts/seed_fixtures.py --reset   # truncate all tables first, then seed

Seeded credentials:
    admin@acme.com   / admin123   (admin)
    sarah@acme.com   / tech123    (tech_lead)
    mark@acme.com    / biz123     (business_admin)
    jane@acme.com    / user123    (user)
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import bcrypt
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.models import (
    User, Rule, RuleVersion, Service, RuleService,
    Document, RuleDocument, Notification, AuditLog,
    IngestError, IngestRun, IngestSource, SystemSetting, Conflict,
    TerminologyInconsistency, Feedback,
)
from app.models.rule import RuleStatusEnum, EnvironmentTypeEnum
from app.models.ingest import IngestErrorSourceEnum


def _pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _dt(offset_days: float = 0, offset_minutes: float = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=offset_days, minutes=offset_minutes)


TRUNCATE_ORDER = [
    "feedback", "audit_log", "notifications", "subscriptions",
    "rule_documents", "documents", "rule_services", "rule_versions",
    "rules", "services", "ingest_errors", "ingest_runs",
    "ingest_sources", "connected_accounts", "users",
    "terminology_inconsistencies", "conflicts", "system_settings",
]


async def seed(session: AsyncSession, reset: bool = False) -> None:
    if reset:
        print("Truncating tables...")
        for table in TRUNCATE_ORDER:
            await session.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
        await session.commit()
        print("Tables cleared.\n")
    else:
        result = await session.execute(select(User))
        if result.scalars().first() is not None:
            print("Users table already has data. Run with --reset to wipe and re-seed.")
            return

    # ── Users ──────────────────────────────────────────────────────────────
    uid = {k: uuid.uuid4() for k in ("admin", "tech", "biz", "user")}

    session.add_all([
        User(id=uid["admin"], username="admin", email="admin@acme.com", name="Kevin Admin",
             password_hash=_pw("admin123"), role="admin", created_at=_dt(-90)),
        User(id=uid["tech"], username="sarah_tech", email="sarah@acme.com", name="Sarah Tech",
             password_hash=_pw("tech123"), role="tech_lead", created_at=_dt(-80)),
        User(id=uid["biz"], username="mark_biz", email="mark@acme.com", name="Mark Business",
             password_hash=_pw("biz123"), role="business_admin", created_at=_dt(-75)),
        User(id=uid["user"], username="jane_user", email="jane@acme.com", name="Jane User",
             password_hash=_pw("user123"), role="user", created_at=_dt(-60)),
    ])
    await session.flush()
    print("Created 4 users")

    # ── Services ────────────────────────────────────────────────────────────
    sid = {k: uuid.uuid4() for k in ("payment", "order", "inventory", "auth", "notification")}

    session.add_all([
        Service(id=sid["payment"],      name="PaymentService",      source_name="payment-service"),
        Service(id=sid["order"],        name="OrderService",        source_name="order-service"),
        Service(id=sid["inventory"],    name="InventoryService",    source_name="inventory-service"),
        Service(id=sid["auth"],         name="AuthService",         source_name="auth-service"),
        Service(id=sid["notification"], name="NotificationService", source_name="notification-service"),
    ])
    await session.flush()
    print("Created 5 services")

    # ── Rules ───────────────────────────────────────────────────────────────
    # source_type="code" matches what ingest_service.store_rule() writes for repo ingests.
    # "github_repo" is only used in the ingest_sources table, not on rule records.
    # For proposed/under_review rules, code_behavior == definition (fresh extraction, not yet
    # split by a BA). For drift/needs_update, code_behavior reflects what the LLM re-extracted
    # from code while definition holds the policy text — the canonical drift pattern.
    rid = {k: uuid.uuid4() for k in (
        "cvv", "order_approval", "inventory_buffer", "lockout",
        "email_notify", "refunds", "discount_expiry", "email_verify",
        "gateway_timeout", "backorder", "admin_override", "two_fa",
        "tax_calc", "low_inventory", "cancel_window",
    )}

    # Stub cognee_node_ids for rules that completed a successful ingest
    # (Cognee is non-fatal so some rules won't have one, but most active rules would)
    cnode = {k: str(uuid.uuid4()) for k in (
        "cvv", "order_approval", "inventory_buffer", "lockout", "email_notify",
        "refunds", "discount_expiry", "email_verify", "gateway_timeout",
        "backorder", "tax_calc", "cancel_window",
    )}

    session.add_all([
        Rule(
            id=rid["cvv"],
            title="Credit card validation requires CVV",
            definition=(
                "All credit card transactions must include a valid CVV code. "
                "Transactions submitted without a CVV are rejected with error code PAYMENT_CVV_MISSING."
            ),
            owner_id=uid["tech"], status=RuleStatusEnum.active,
            environment=EnvironmentTypeEnum.prod,
            extraction_confidence=0.97, graph_quality_score=0.91,
            source_type="code", source_file="src/payment/validators.py",
            cognee_node_id=cnode["cvv"], coverage_status="covered",
            code_behavior=(
                "PaymentValidator.validate_card() raises CardValidationError "
                "when cvv is None or empty."
            ),
            created_at=_dt(-85), updated_at=_dt(-10),
        ),
        Rule(
            id=rid["order_approval"],
            title="Orders above $500 require manager approval",
            definition=(
                "Any order with a total value exceeding $500 USD must pass through a manager "
                "approval workflow before being submitted to fulfillment. The approval request "
                "is automatically routed to the responsible team manager."
            ),
            owner_id=uid["biz"], status=RuleStatusEnum.active,
            environment=EnvironmentTypeEnum.prod,
            extraction_confidence=0.94, graph_quality_score=0.88,
            source_type="code", source_file="src/orders/approval_workflow.py",
            cognee_node_id=cnode["order_approval"], coverage_status="covered",
            code_behavior=(
                "OrderWorkflow.submit() routes to manager_approval_queue when order total > 500."
            ),
            created_at=_dt(-80), updated_at=_dt(-5),
        ),
        Rule(
            id=rid["inventory_buffer"],
            title="Inventory buffer minimum is 10 units",
            definition=(
                "Each product SKU must maintain a minimum buffer of 10 units in the warehouse. "
                "Products falling below this threshold trigger an automatic reorder request."
            ),
            owner_id=uid["biz"], status=RuleStatusEnum.active,
            environment=EnvironmentTypeEnum.prod,
            extraction_confidence=0.89, graph_quality_score=0.82,
            source_type="code", source_file="src/inventory/threshold_monitor.py",
            cognee_node_id=cnode["inventory_buffer"], coverage_status="covered",
            code_behavior=(
                "ThresholdMonitor.check() emits reorder_requested event when stock < 10."
            ),
            created_at=_dt(-75), updated_at=_dt(-3),
        ),
        Rule(
            id=rid["lockout"],
            title="Failed login attempts trigger account lockout after 5 tries",
            definition=(
                "After 5 consecutive failed authentication attempts, a user account is temporarily "
                "locked for 30 minutes. An automated unlock email is sent to the account holder."
            ),
            owner_id=uid["tech"], status=RuleStatusEnum.active,
            environment=EnvironmentTypeEnum.prod,
            extraction_confidence=0.98, graph_quality_score=0.95,
            source_type="code", source_file="src/auth/login_handler.py",
            cognee_node_id=cnode["lockout"], coverage_status="covered",
            code_behavior=(
                "LoginHandler.authenticate() raises AccountLockedException after 5 failures "
                "and sets locked_until = now + 30 minutes."
            ),
            created_at=_dt(-70), updated_at=_dt(-1),
        ),
        Rule(
            id=rid["email_notify"],
            title="Email notifications sent within 30 seconds of order placement",
            definition=(
                "Order confirmation emails must be dispatched within 30 seconds of a successful "
                "order placement. Delays beyond 30 seconds trigger a retry via the dead-letter queue."
            ),
            owner_id=uid["tech"], status=RuleStatusEnum.active,
            environment=EnvironmentTypeEnum.prod,
            extraction_confidence=0.85, graph_quality_score=0.79,
            source_type="code", source_file="src/notifications/email_dispatcher.py",
            cognee_node_id=cnode["email_notify"], coverage_status="covered",
            code_behavior=(
                "EmailDispatcher.send_order_confirmation() uses SQS with 30s visibility timeout "
                "and a DLQ fallback for retries."
            ),
            created_at=_dt(-65), updated_at=_dt(-2),
        ),
        Rule(
            id=rid["refunds"],
            title="Refunds must be processed within 48 hours",
            definition=(
                "Customer refund requests must be processed and funds returned within 48 business "
                "hours of approval. Refunds still in pending state after 48 hours are automatically "
                "escalated to the finance team."
            ),
            owner_id=uid["biz"], status=RuleStatusEnum.drift,
            environment=EnvironmentTypeEnum.prod,
            extraction_confidence=0.91, graph_quality_score=0.76,
            source_type="code", source_file="src/payment/refund_processor.py",
            cognee_node_id=cnode["refunds"], coverage_status="partial",
            code_behavior=(
                "RefundProcessor.process() runs async but 48h escalation logic is not implemented "
                "in the current codebase — policy drift detected."
            ),
            created_at=_dt(-60), updated_at=_dt(-7),
        ),
        Rule(
            id=rid["discount_expiry"],
            title="Discount codes expire after 30 days",
            definition=(
                "All promotional discount codes have a maximum validity period of 30 days from the "
                "date of issuance. Codes past their expiry date must return error DISCOUNT_EXPIRED."
            ),
            owner_id=uid["biz"], status=RuleStatusEnum.needs_update,
            environment=EnvironmentTypeEnum.prod,
            extraction_confidence=0.88, graph_quality_score=0.71,
            source_type="code", source_file="src/orders/discount_validator.py",
            cognee_node_id=cnode["discount_expiry"], coverage_status="partial",
            code_behavior=(
                "DiscountValidator.apply() checks expiry but uses a 45-day window — mismatches the "
                "30-day policy."
            ),
            created_at=_dt(-55), updated_at=_dt(-4),
        ),
        Rule(
            id=rid["email_verify"],
            title="New user registration requires email verification",
            definition=(
                "Every new user account must verify their email address before gaining access to "
                "order placement features. Verification links expire after 24 hours."
            ),
            owner_id=uid["tech"], status=RuleStatusEnum.active,
            environment=EnvironmentTypeEnum.prod,
            extraction_confidence=0.96, graph_quality_score=0.93,
            source_type="code", source_file="src/auth/registration.py",
            cognee_node_id=cnode["email_verify"], coverage_status="covered",
            code_behavior=(
                "RegistrationService.register() sets email_verified=False and sends a verification "
                "email. Order placement is blocked until email_verified=True."
            ),
            created_at=_dt(-50), updated_at=_dt(-6),
        ),
        Rule(
            id=rid["gateway_timeout"],
            title="Payment gateway timeout is 10 seconds",
            definition=(
                "All outbound payment gateway requests must have a maximum timeout of 10 seconds. "
                "Requests exceeding this limit are retried once before returning PAYMENT_TIMEOUT."
            ),
            owner_id=uid["tech"], status=RuleStatusEnum.drift,
            environment=EnvironmentTypeEnum.prod,
            extraction_confidence=0.92, graph_quality_score=0.84,
            source_type="code", source_file="src/payment/gateway_client.py",
            cognee_node_id=cnode["gateway_timeout"], coverage_status="partial",
            code_behavior=(
                "GatewayClient sets a 15s timeout (not 10s) and has no retry logic — "
                "both are policy violations."
            ),
            created_at=_dt(-45), updated_at=_dt(-8),
        ),
        Rule(
            id=rid["backorder"],
            title="Backorder items display estimated restock date",
            definition=(
                "Products with zero inventory that are available for backorder must display an "
                "estimated restock date. If no restock date is known, display 'Unknown restock date'."
            ),
            owner_id=uid["biz"], status=RuleStatusEnum.active,
            environment=EnvironmentTypeEnum.prod,
            extraction_confidence=0.87, graph_quality_score=0.80,
            source_type="code", source_file="src/inventory/product_presenter.py",
            cognee_node_id=cnode["backorder"], coverage_status="covered",
            code_behavior=(
                "ProductPresenter.render() shows restock_date or 'Unknown restock date' "
                "when inventory == 0 and is_backorderable is True."
            ),
            created_at=_dt(-40), updated_at=_dt(-9),
        ),
        Rule(
            id=rid["admin_override"],
            title="Admin users can override order limits",
            definition=(
                "Users with the admin role may bypass standard order value limits and minimum "
                "quantity requirements. All override actions must be logged with justification text."
            ),
            # Freshly proposed: code_behavior == definition (raw LLM extraction, not yet BA-edited)
            code_behavior=(
                "Users with the admin role may bypass standard order value limits and minimum "
                "quantity requirements. All override actions must be logged with justification text."
            ),
            owner_id=uid["biz"], status=RuleStatusEnum.proposed,
            environment=None,
            extraction_confidence=0.72, graph_quality_score=None,
            source_type="code", source_file="src/orders/order_service.py",
            cognee_node_id=None, coverage_status="uncovered",
            created_at=_dt(-15), updated_at=_dt(-15),
        ),
        Rule(
            id=rid["two_fa"],
            title="Two-factor authentication required for admin accounts",
            definition=(
                "All users with admin or tech_lead roles must have 2FA enabled. Accounts without "
                "2FA are downgraded to read-only access after a 7-day grace period."
            ),
            # Under review: BA refined the definition wording; code_behavior is the original extraction
            code_behavior=(
                "Admin and tech_lead users must have two-factor authentication configured. "
                "Users lacking 2FA become read-only after a grace period."
            ),
            owner_id=uid["tech"], status=RuleStatusEnum.under_review,
            environment=None,
            extraction_confidence=0.90, graph_quality_score=None,
            source_type="code", source_file="src/auth/access_control.py",
            cognee_node_id=None, coverage_status="uncovered",
            created_at=_dt(-20), updated_at=_dt(-3),
        ),
        Rule(
            id=rid["tax_calc"],
            title="Product pricing includes tax calculation",
            definition=(
                "All displayed product prices must include applicable tax calculated at checkout "
                "based on the customer's shipping address. Tax rates are fetched from TaxService "
                "at order submission time."
            ),
            owner_id=uid["biz"], status=RuleStatusEnum.approved,
            environment=EnvironmentTypeEnum.uat,
            extraction_confidence=0.93, graph_quality_score=0.86,
            source_type="code", source_file="src/orders/pricing_calculator.py",
            cognee_node_id=cnode["tax_calc"], coverage_status="partial",
            code_behavior=(
                "PricingCalculator.calculate_total() calls TaxService.get_rate() but only for "
                "US addresses — international tax is not handled."
            ),
            created_at=_dt(-30), updated_at=_dt(-2),
        ),
        Rule(
            id=rid["low_inventory"],
            title="Low inventory alert triggers at 5% of max capacity",
            definition=(
                "When a warehouse's available inventory for a product falls below 5% of its maximum "
                "storage capacity, an alert is dispatched to the operations team via Slack and email."
            ),
            owner_id=uid["tech"], status=RuleStatusEnum.approved,
            environment=EnvironmentTypeEnum.uat,
            extraction_confidence=0.86, graph_quality_score=0.78,
            source_type="code", source_file="src/inventory/alert_manager.py",
            cognee_node_id=None, coverage_status="uncovered",
            created_at=_dt(-25), updated_at=_dt(-1),
        ),
        Rule(
            id=rid["cancel_window"],
            title="Order cancellation allowed within 1 hour of placement",
            definition=(
                "Customers may cancel an order without penalty within 60 minutes of order placement. "
                "Cancellations after this window require customer service intervention."
            ),
            owner_id=uid["biz"], status=RuleStatusEnum.deprecated,
            environment=EnvironmentTypeEnum.prod,
            extraction_confidence=0.82, graph_quality_score=0.74,
            source_type="code", source_file="src/orders/cancellation_handler.py",
            cognee_node_id=cnode["cancel_window"], coverage_status="covered",
            code_behavior=(
                "CancellationHandler.cancel() is deprecated — replaced by a configurable window "
                "managed via admin settings."
            ),
            deprecated_at=_dt(-5),
            created_at=_dt(-90), updated_at=_dt(-5),
        ),
    ])
    await session.flush()
    print("Created 15 rules")

    # ── Rule ↔ Service links ─────────────────────────────────────────────────
    rule_svc_pairs = [
        (rid["cvv"],              sid["payment"]),
        (rid["order_approval"],   sid["order"]),
        (rid["inventory_buffer"], sid["inventory"]),
        (rid["lockout"],          sid["auth"]),
        (rid["email_notify"],     sid["notification"]),
        (rid["email_notify"],     sid["order"]),
        (rid["refunds"],          sid["payment"]),
        (rid["refunds"],          sid["order"]),
        (rid["discount_expiry"],  sid["order"]),
        (rid["email_verify"],     sid["auth"]),
        (rid["gateway_timeout"],  sid["payment"]),
        (rid["backorder"],        sid["inventory"]),
        (rid["admin_override"],   sid["order"]),
        (rid["two_fa"],           sid["auth"]),
        (rid["tax_calc"],         sid["order"]),
        (rid["tax_calc"],         sid["payment"]),
        (rid["low_inventory"],    sid["inventory"]),
        (rid["cancel_window"],    sid["order"]),
    ]
    for rule_id, svc_id in rule_svc_pairs:
        session.add(RuleService(rule_id=rule_id, service_id=svc_id))
    await session.flush()
    print(f"Created {len(rule_svc_pairs)} rule-service links")

    # ── Rule Versions ────────────────────────────────────────────────────────
    session.add_all([
        RuleVersion(
            id=uuid.uuid4(), rule_id=rid["cvv"],
            definition="All credit card transactions must include a CVV code.",
            status=RuleStatusEnum.proposed, changed_by=uid["tech"],
            changed_at=_dt(-85), change_note="Initial extraction from payment-service codebase",
        ),
        RuleVersion(
            id=uuid.uuid4(), rule_id=rid["cvv"],
            definition=(
                "All credit card transactions must include a valid CVV code. "
                "Transactions without CVV are rejected."
            ),
            status=RuleStatusEnum.active, changed_by=uid["admin"],
            changed_at=_dt(-80), change_note="Clarified rejection behavior and error code",
        ),
        RuleVersion(
            id=uuid.uuid4(), rule_id=rid["refunds"],
            definition="Refunds must be processed within 72 hours of approval.",
            status=RuleStatusEnum.active, changed_by=uid["biz"],
            changed_at=_dt(-60), change_note="Original SLA was 72 hours per legacy policy",
        ),
        RuleVersion(
            id=uuid.uuid4(), rule_id=rid["refunds"],
            definition="Refunds must be processed within 48 hours. Escalate at 48h mark.",
            status=RuleStatusEnum.drift, changed_by=uid["biz"],
            changed_at=_dt(-30), change_note="SLA tightened to 48h per Q3 customer agreement",
        ),
        RuleVersion(
            id=uuid.uuid4(), rule_id=rid["gateway_timeout"],
            definition="Payment gateway timeout is 15 seconds.",
            status=RuleStatusEnum.active, changed_by=uid["tech"],
            changed_at=_dt(-45), change_note="Initial policy extracted from legacy docs",
        ),
        RuleVersion(
            id=uuid.uuid4(), rule_id=rid["gateway_timeout"],
            definition="Payment gateway timeout reduced to 10 seconds to improve user experience.",
            status=RuleStatusEnum.drift, changed_by=uid["tech"],
            changed_at=_dt(-20),
            change_note="Policy updated — code still uses 15s, flagged as drift",
        ),
    ])
    await session.flush()
    print("Created 6 rule versions")

    # ── Ingest Sources ───────────────────────────────────────────────────────
    isrc = {k: uuid.uuid4() for k in ("payment", "order")}

    session.add_all([
        IngestSource(
            id=isrc["payment"], name="payment-service", source_type="github_repo",
            repo_url="https://github.com/acme/payment-service", branch="main",
            paths=["src/payment/", "src/billing/"],
            exclude=["tests/", "**/__pycache__/"],
            test_paths=["tests/"],
            created_by=uid["admin"], last_ingested_at=_dt(-10),
            status="active", ingest_status="idle",
        ),
        IngestSource(
            id=isrc["order"], name="order-service", source_type="github_repo",
            repo_url="https://github.com/acme/order-service", branch="main",
            paths=["src/orders/", "src/pricing/"],
            exclude=["tests/", "docs/"],
            test_paths=["tests/unit/", "tests/integration/"],
            created_by=uid["admin"], last_ingested_at=_dt(-7),
            status="active", ingest_status="idle",
        ),
    ])
    await session.flush()
    print("Created 2 ingest sources")

    # ── Ingest Runs ──────────────────────────────────────────────────────────
    run = [uuid.uuid4() for _ in range(3)]

    session.add_all([
        IngestRun(
            id=run[0], started_at=_dt(-10),
            completed_at=_dt(-10, offset_minutes=4.5),
            status="completed", source_name="payment-service",
            files_processed=47, files_errored=2,
        ),
        IngestRun(
            id=run[1], started_at=_dt(-7),
            completed_at=_dt(-7, offset_minutes=6.2),
            status="completed", source_name="order-service",
            files_processed=63, files_errored=1,
        ),
        IngestRun(
            id=run[2], started_at=_dt(-1),
            completed_at=None,
            status="running", source_name="payment-service",
            files_processed=12, files_errored=0,
        ),
    ])
    await session.flush()
    print("Created 3 ingest runs")

    # ── Ingest Errors ────────────────────────────────────────────────────────
    session.add_all([
        IngestError(
            id=uuid.uuid4(), source_name="payment-service",
            file_path="src/payment/legacy_adapter.py",
            error_source=IngestErrorSourceEnum.llm_extraction,
            error_message=(
                "Unable to extract a clear rule boundary — file contains too many nested "
                "conditionals for reliable extraction."
            ),
            raw_content="# Legacy adapter — do not modify\ndef process(txn):\n    if txn.type == 'refund':\n        ...",
            ingest_run_id=run[0], created_at=_dt(-10),
        ),
        IngestError(
            id=uuid.uuid4(), source_name="payment-service",
            file_path="src/payment/deprecated_validator.py",
            error_source=IngestErrorSourceEnum.document_parse,
            error_message="File encoding error — non-UTF-8 characters detected in source file.",
            ingest_run_id=run[0], created_at=_dt(-10),
            resolved_at=_dt(-9), resolved_by=uid["tech"],
            resolution_note="File was a binary artifact — added to exclude list.",
        ),
        IngestError(
            id=uuid.uuid4(), source_name="order-service",
            file_path="src/orders/legacy_discount.js",
            error_source=IngestErrorSourceEnum.llm_extraction,
            error_message=(
                "JavaScript file — extraction confidence below threshold (0.42). "
                "Insufficient structural context for reliable rule identification."
            ),
            ingest_run_id=run[1], created_at=_dt(-7),
        ),
    ])
    await session.flush()
    print("Created 3 ingest errors")

    # ── Conflicts ────────────────────────────────────────────────────────────
    session.add_all([
        Conflict(
            id=uuid.uuid4(),
            description=(
                "Payment gateway timeout conflict: PaymentService policy mandates 10s timeout "
                "but OrderService integration tests assert a 15s timeout is acceptable."
            ),
            services=["PaymentService", "OrderService"],
            rule_ids=[str(rid["gateway_timeout"])],
            severity="high", created_at=_dt(-8), ingest_run_id=run[1],
        ),
        Conflict(
            id=uuid.uuid4(),
            description=(
                "Discount expiry window mismatch: business policy requires 30-day expiry "
                "but OrderService code enforces a 45-day window."
            ),
            services=["OrderService"],
            rule_ids=[str(rid["discount_expiry"])],
            severity="medium", created_at=_dt(-4), ingest_run_id=run[1],
        ),
    ])
    await session.flush()
    print("Created 2 conflicts")

    # ── Terminology Inconsistencies ──────────────────────────────────────────
    session.add_all([
        TerminologyInconsistency(
            id=uuid.uuid4(),
            canonical_term="order_value",
            variants=["order_total", "order_amount", "order_value", "cart_total"],
            services=["OrderService", "PaymentService", "InventoryService"],
            status="approved",
            definition=(
                "The total monetary value of an order including all line items, "
                "before tax and shipping are applied."
            ),
            definition_confidence=0.91, definition_status="accepted",
            detected_at=_dt(-10), created_at=_dt(-10),
        ),
        TerminologyInconsistency(
            id=uuid.uuid4(),
            canonical_term="sku",
            variants=["sku", "product_code", "item_id", "product_id"],
            services=["InventoryService", "OrderService"],
            status="pending",
            detected_at=_dt(-7), created_at=_dt(-7),
        ),
        TerminologyInconsistency(
            id=uuid.uuid4(),
            canonical_term="refund_window",
            variants=["refund_period", "refund_window", "return_period", "return_window"],
            services=["PaymentService", "OrderService"],
            status="pending",
            detected_at=_dt(-4), created_at=_dt(-4),
        ),
    ])
    await session.flush()
    print("Created 3 terminology inconsistencies")

    # ── Documents ────────────────────────────────────────────────────────────
    doc = [uuid.uuid4(), uuid.uuid4()]

    session.add_all([
        Document(
            id=doc[0], filename="payment_policy_v3.pdf", file_type="pdf",
            storage_path="uploads/payment_policy_v3.pdf", status="approved",
            owner_id=uid["biz"], tags=["payment", "policy", "compliance"],
            uploaded_at=_dt(-30), approved_at=_dt(-28),
        ),
        Document(
            id=doc[1], filename="order_sla_handbook.docx", file_type="docx",
            storage_path="uploads/order_sla_handbook.docx", status="sandbox",
            owner_id=uid["user"], tags=["orders", "sla", "draft"],
            uploaded_at=_dt(-2),
        ),
    ])
    await session.flush()
    session.add(RuleDocument(rule_id=rid["refunds"], document_id=doc[0]))
    await session.flush()
    print("Created 2 documents")

    # ── Notifications ────────────────────────────────────────────────────────
    session.add_all([
        Notification(
            id=uuid.uuid4(), user_id=uid["user"], type="rule_status_change",
            rule_id=rid["refunds"],
            message="Rule 'Refunds must be processed within 48 hours' changed status to Drift.",
            read=False, created_at=_dt(-7),
        ),
        Notification(
            id=uuid.uuid4(), user_id=uid["user"], type="conflict_detected",
            rule_id=rid["gateway_timeout"],
            message="A new conflict was detected involving 'Payment gateway timeout is 10 seconds'.",
            read=True, created_at=_dt(-8),
        ),
        Notification(
            id=uuid.uuid4(), user_id=uid["biz"], type="rule_pending_review",
            rule_id=rid["two_fa"],
            message="Rule 'Two-factor authentication required for admin accounts' is pending your review.",
            read=False, created_at=_dt(-3),
        ),
    ])
    await session.flush()
    print("Created 3 notifications")

    # ── Audit Log ────────────────────────────────────────────────────────────
    session.add_all([
        AuditLog(
            id=uuid.uuid4(), user_id=uid["admin"], action="user_created",
            target_type="user", target_id=uid["tech"],
            detail={"username": "sarah_tech", "role": "tech_lead"},
            ip_address="10.0.0.1", created_at=_dt(-80),
        ),
        AuditLog(
            id=uuid.uuid4(), user_id=uid["tech"], action="rule_approved",
            target_type="rule", target_id=rid["cvv"],
            detail={"new_status": "active", "previous_status": "proposed"},
            ip_address="10.0.0.5", created_at=_dt(-80),
        ),
        AuditLog(
            id=uuid.uuid4(), user_id=uid["biz"], action="rule_reviewed",
            target_type="rule", target_id=rid["refunds"],
            detail={"action": "approved", "change_note": "SLA tightened to 48h"},
            ip_address="10.0.0.8", created_at=_dt(-30),
        ),
        AuditLog(
            id=uuid.uuid4(), user_id=uid["admin"], action="ingest_started",
            target_type="ingest_run", target_id=run[0],
            detail={"source": "payment-service", "branch": "main"},
            ip_address="10.0.0.1", created_at=_dt(-10),
        ),
        AuditLog(
            id=uuid.uuid4(), user_id=uid["tech"], action="conflict_resolved",
            target_type="conflict", target_id=None,
            detail={"source": "order-service", "severity": "medium"},
            ip_address="10.0.0.5", created_at=_dt(-3),
        ),
    ])
    await session.flush()
    print("Created 5 audit log entries")

    # ── Feedback ─────────────────────────────────────────────────────────────
    session.add_all([
        Feedback(
            id=uuid.uuid4(), user_id=uid["user"], rule_id=rid["cvv"],
            signal_type="thumbs_up", weight=1.0, created_at=_dt(-5),
        ),
        Feedback(
            id=uuid.uuid4(), user_id=uid["biz"], rule_id=rid["refunds"],
            signal_type="thumbs_down", weight=-1.0, created_at=_dt(-4),
        ),
        Feedback(
            id=uuid.uuid4(), user_id=uid["tech"], rule_id=rid["gateway_timeout"],
            signal_type="thumbs_down", weight=-1.0, created_at=_dt(-3),
        ),
        Feedback(
            id=uuid.uuid4(), user_id=uid["user"], rule_id=rid["lockout"],
            signal_type="thumbs_up", weight=1.0, created_at=_dt(-2),
        ),
    ])
    await session.flush()
    print("Created 4 feedback records")

    # ── System Settings ───────────────────────────────────────────────────────
    session.add_all([
        SystemSetting(key="review_queue_notify",   value="true",        updated_by=uid["admin"]),
        SystemSetting(key="auto_promote_threshold", value="0.95",        updated_by=uid["admin"]),
        SystemSetting(key="ingest_schedule",        value="0 2 * * *",   updated_by=uid["admin"]),
        SystemSetting(key="max_ingest_file_size_mb", value="10",         updated_by=uid["admin"]),
    ])
    await session.flush()
    print("Created 4 system settings")

    await session.commit()
    print("\n[seed_fixtures] Done. Login credentials:")
    print("  admin@acme.com   / admin123  (admin)")
    print("  sarah@acme.com   / tech123   (tech_lead)")
    print("  mark@acme.com    / biz123    (business_admin)")
    print("  jane@acme.com    / user123   (user)")


async def main() -> None:
    reset = "--reset" in sys.argv
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        await seed(session, reset=reset)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
