"""Bind an internal-paper decision request to its durable command receipt."""

import sqlalchemy as sa

from alembic import op

revision = "0006_ai_paper_decision_binding"
down_revision = "0005_market_snapshot_projection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_paper_cycle_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("environment", sa.String(16), nullable=False),
        sa.Column("account_ref", sa.String(128), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("decision_id", sa.String(128), nullable=False),
        sa.Column("fixture_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("environment", "account_ref", "request_id", name="uq_ai_paper_cycle_request"),
    )
    op.create_table(
        "ai_paper_cycle_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("receipt_id", sa.Integer(), sa.ForeignKey("ai_paper_cycle_receipts.id"), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(128)),
        sa.Column("strategy_digest", sa.String(64)),
        sa.Column("evidence_digest", sa.String(64)),
        sa.Column("client_order_id", sa.String(36)),
        sa.Column("command_id", sa.String(36), sa.ForeignKey("execution_commands.id")),
        sa.Column("generation", sa.Integer()),
        sa.Column("claim_owner", sa.String(128)),
        sa.Column("claim_deadline_ns", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("receipt_id", "event_id", name="uq_ai_paper_cycle_event_id"),
        sa.UniqueConstraint("receipt_id", "sequence", name="uq_ai_paper_cycle_event_sequence"),
    )
    op.create_index("ix_ai_paper_cycle_event_receipt", "ai_paper_cycle_events", ["receipt_id", "sequence"])
    op.create_index("ix_ai_paper_cycle_event_claim_owner", "ai_paper_cycle_events", ["claim_owner"])
    op.execute(
        "CREATE TRIGGER ai_paper_cycle_receipts_no_update BEFORE UPDATE ON ai_paper_cycle_receipts "
        "BEGIN SELECT RAISE(ABORT, 'cycle receipt headers are immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER ai_paper_cycle_receipts_no_delete BEFORE DELETE ON ai_paper_cycle_receipts "
        "BEGIN SELECT RAISE(ABORT, 'cycle receipt headers are immutable'); END"
    )
    op.execute(
        "CREATE TRIGGER ai_paper_cycle_events_no_update BEFORE UPDATE ON ai_paper_cycle_events "
        "BEGIN SELECT RAISE(ABORT, 'cycle receipt events are append-only'); END"
    )
    op.execute(
        "CREATE TRIGGER ai_paper_cycle_events_no_delete BEFORE DELETE ON ai_paper_cycle_events "
        "BEGIN SELECT RAISE(ABORT, 'cycle receipt events are append-only'); END"
    )
    op.create_table(
        "ai_paper_decision_bindings",
        sa.Column("environment", sa.String(16), primary_key=True),
        sa.Column("account_ref", sa.String(128), primary_key=True),
        sa.Column("request_id", sa.String(128), primary_key=True),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("decision_id", sa.String(128), nullable=False),
        sa.Column("fixture_digest", sa.String(64), nullable=False),
        sa.Column("command_id", sa.String(36), nullable=False),
        sa.Column("native_client_order_id", sa.String(36), nullable=False),
        sa.Column("receipt_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["command_id"], ["execution_commands.id"]),
        sa.UniqueConstraint("command_id", name="uq_ai_paper_binding_command"),
        sa.UniqueConstraint("native_client_order_id", name="uq_ai_paper_binding_native_id"),
    )
    op.create_index("ix_ai_paper_binding_decision_id", "ai_paper_decision_bindings", ["decision_id"])


def downgrade() -> None:
    row = op.get_bind().execute(sa.text("SELECT 1 FROM ai_paper_decision_bindings LIMIT 1")).first()
    if row is not None:
        raise RuntimeError("refusing downgrade: decision bindings contain durable paper receipts")
    row = op.get_bind().execute(sa.text("SELECT 1 FROM ai_paper_cycle_events LIMIT 1")).first()
    if row is not None:
        raise RuntimeError("refusing downgrade: cycle receipts contain durable events")
    op.execute("DROP TRIGGER ai_paper_cycle_events_no_delete")
    op.execute("DROP TRIGGER ai_paper_cycle_events_no_update")
    op.execute("DROP TRIGGER ai_paper_cycle_receipts_no_delete")
    op.execute("DROP TRIGGER ai_paper_cycle_receipts_no_update")
    op.drop_index("ix_ai_paper_cycle_event_receipt", table_name="ai_paper_cycle_events")
    op.drop_index("ix_ai_paper_cycle_event_claim_owner", table_name="ai_paper_cycle_events")
    op.drop_table("ai_paper_cycle_events")
    op.drop_table("ai_paper_cycle_receipts")
    op.drop_index("ix_ai_paper_binding_decision_id", table_name="ai_paper_decision_bindings")
    op.drop_table("ai_paper_decision_bindings")
