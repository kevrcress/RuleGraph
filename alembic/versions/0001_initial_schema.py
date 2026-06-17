"""Initial schema — all tables and enums for Stage 1.

Revision ID: 0001
Revises:
Create Date: 2026-05-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    # --- Create PostgreSQL enum types FIRST ---
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE rule_status AS ENUM (
                'proposed', 'under_review', 'approved', 'active',
                'drift', 'needs_update', 'deprecated'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE environment_type AS ENUM ('dev', 'uat', 'prod');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ingest_error_source AS ENUM (
                'llm_extraction', 'cognee_ingest', 'source_connector',
                'document_parse', 'webhook'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.Text, unique=True, nullable=False),
        sa.Column("email", sa.Text, unique=True, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("aad_object_id", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=True),
    )

    # --- connected_accounts ---
    op.create_table(
        "connected_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("pat_encrypted", sa.Text, nullable=False),
        sa.Column("org", sa.Text, nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # --- services ---
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, unique=True, nullable=False),
        sa.Column("source_name", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # --- rules ---
    op.create_table(
        "rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("definition", sa.Text, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", postgresql.ENUM("proposed", "under_review", "approved", "active", "drift", "needs_update", "deprecated", name="rule_status", create_type=False), nullable=False, server_default="proposed"),
        sa.Column("environment", postgresql.ENUM("dev", "uat", "prod", name="environment_type", create_type=False), nullable=True),
        sa.Column("extraction_confidence", sa.Float, nullable=True),
        sa.Column("graph_quality_score", sa.Float, nullable=True),
        sa.Column("source_type", sa.Text, nullable=True),
        sa.Column("cognee_node_id", sa.Text, nullable=True),
        sa.Column("workitem_id", sa.Text, nullable=True),
        sa.Column("workitem_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- rule_versions ---
    op.create_table(
        "rule_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rules.id"), nullable=True),
        sa.Column("definition", sa.Text, nullable=False),
        sa.Column("status", postgresql.ENUM("proposed", "under_review", "approved", "active", "drift", "needs_update", "deprecated", name="rule_status", create_type=False), nullable=True),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("change_note", sa.Text, nullable=True),
        sa.Column("rejection_note", sa.Text, nullable=True),
    )

    # --- rule_services ---
    op.create_table(
        "rule_services",
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rules.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
    )

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("file_type", sa.Text, nullable=False),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="sandbox"),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_note", sa.Text, nullable=True),
    )

    # --- rule_documents ---
    op.create_table(
        "rule_documents",
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rules.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    )

    # --- subscriptions ---
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("target_type", sa.Text, nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # --- notifications ---
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rules.id"), nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("read", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # --- ingest_errors ---
    op.create_table(
        "ingest_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_name", sa.Text, nullable=True),
        sa.Column("file_path", sa.Text, nullable=True),
        sa.Column("error_source", postgresql.ENUM("llm_extraction", "cognee_ingest", "source_connector", "document_parse", "webhook", name="ingest_error_source", create_type=False), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("raw_content", sa.Text, nullable=True),
        sa.Column("stack_trace", sa.Text, nullable=True),
        sa.Column("ingest_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_note", sa.Text, nullable=True),
    )

    # --- ingest_runs ---
    op.create_table(
        "ingest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text, nullable=True),
        sa.Column("last_processed_file", sa.Text, nullable=True),
        sa.Column("source_name", sa.Text, nullable=True),
        sa.Column("files_processed", sa.Integer, server_default="0"),
        sa.Column("files_errored", sa.Integer, server_default="0"),
    )

    # --- audit_log ---
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("target_type", sa.Text, nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("detail", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # --- system_settings ---
    op.create_table(
        "system_settings",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("audit_log")
    op.drop_table("ingest_runs")
    op.drop_table("ingest_errors")
    op.drop_table("notifications")
    op.drop_table("subscriptions")
    op.drop_table("rule_documents")
    op.drop_table("documents")
    op.drop_table("rule_services")
    op.drop_table("rule_versions")
    op.drop_table("rules")
    op.drop_table("services")
    op.drop_table("connected_accounts")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS ingest_error_source")
    op.execute("DROP TYPE IF EXISTS environment_type")
    op.execute("DROP TYPE IF EXISTS rule_status")
