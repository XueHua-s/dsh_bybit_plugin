"""Add durable account, native-event, reconciliation and emergency projections.

The revision is additive. It stores only redacted evidence and never stores API
keys, secrets or OAuth tokens. Append-only tables are protected at the database
boundary on SQLite; the service still owns the transition invariants.
"""

import sqlalchemy as sa

from alembic import op

revision = "0007_native_execution_state"
down_revision = "0006_ai_paper_decision_binding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_sessions",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("environment", sa.String(16), nullable=False),
        sa.Column("account_ref", sa.String(128), nullable=False),
        sa.Column("expected_uid", sa.String(128)),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("protected", sa.Integer(), nullable=False),
        sa.Column("protection_reason", sa.String(128)),
        sa.Column("reconciliation_revision", sa.Integer(), nullable=False),
        sa.Column("config_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("environment", "account_ref", name="uq_account_session_scope"),
    )
    op.create_index("ix_account_session_status", "account_sessions", ["status"])

    op.create_table(
        "reconciliation_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(128), sa.ForeignKey("account_sessions.id"), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("evidence_digest", sa.String(64), nullable=False),
        sa.Column("wallet_json", sa.Text(), nullable=False),
        sa.Column("positions_json", sa.Text(), nullable=False),
        sa.Column("orders_json", sa.Text(), nullable=False),
        sa.Column("executions_json", sa.Text(), nullable=False),
        sa.Column("complete", sa.Integer(), nullable=False),
        sa.Column("protected_reason", sa.String(128)),
        sa.Column("observed_at_ns", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("session_id", "revision", name="uq_reconciliation_revision"),
    )
    op.create_index("ix_reconciliation_observed_at", "reconciliation_snapshots", ["observed_at_ns"])

    op.create_table(
        "native_execution_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(128), sa.ForeignKey("account_sessions.id"), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("command_id", sa.String(36), sa.ForeignKey("execution_commands.id")),
        sa.Column("client_order_id", sa.String(36)),
        sa.Column("venue_order_id", sa.String(128)),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("occurred_at_ns", sa.BigInteger(), nullable=False),
        sa.Column("applied", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("session_id", "event_id", name="uq_native_execution_event"),
    )
    op.create_index("ix_native_execution_client_order", "native_execution_events", ["client_order_id"])
    op.create_index("ix_native_execution_occurred_at", "native_execution_events", ["occurred_at_ns"])

    op.create_table(
        "execution_reservations",
        sa.Column("command_id", sa.String(36), sa.ForeignKey("execution_commands.id"), primary_key=True),
        sa.Column("session_id", sa.String(128), sa.ForeignKey("account_sessions.id"), nullable=False),
        sa.Column("account_generation", sa.Integer(), nullable=False),
        sa.Column("reconciliation_revision", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(128), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("remaining_quantity", sa.String(64), nullable=False),
        sa.Column("reserved_notional", sa.String(64), nullable=False),
        sa.Column("reserved_at_ns", sa.BigInteger(), nullable=False),
    )

    op.create_table(
        "native_admission_decisions",
        sa.Column("command_id", sa.String(36), sa.ForeignKey("execution_commands.id"), primary_key=True),
        sa.Column("session_id", sa.String(128), sa.ForeignKey("account_sessions.id"), nullable=False),
        sa.Column("allowed", sa.Integer(), nullable=False),
        sa.Column("decision_code", sa.String(32), nullable=False),
        sa.Column("policy_fingerprint", sa.String(64), nullable=False),
        sa.Column("context_fingerprint", sa.String(64), nullable=False),
        sa.Column("account_generation", sa.Integer(), nullable=False),
        sa.Column("reconciliation_revision", sa.Integer(), nullable=False),
        sa.Column("evaluated_at_ns", sa.BigInteger(), nullable=False),
        sa.Column("expires_at_ns", sa.BigInteger(), nullable=False),
        sa.Column("reservation_price", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "emergency_states",
        sa.Column("session_id", sa.String(128), sa.ForeignKey("account_sessions.id"), primary_key=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(128)),
        sa.Column("command_id", sa.String(36), sa.ForeignKey("execution_commands.id")),
        sa.Column("updated_at_ns", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "emergency_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(128), sa.ForeignKey("account_sessions.id"), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(128)),
        sa.Column("command_id", sa.String(36), sa.ForeignKey("execution_commands.id")),
        sa.Column("occurred_at_ns", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("session_id", "event_id", name="uq_emergency_event"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_emergency_event_sequence"),
    )
    op.create_index("ix_emergency_event_session", "emergency_events", ["session_id", "sequence"])

    if op.get_bind().dialect.name == "sqlite":
        for table, identity, message in (
            (
                "reconciliation_snapshots",
                "session_id=NEW.session_id AND revision=NEW.revision",
                "reconciliation snapshots are append-only",
            ),
            (
                "native_execution_events",
                "session_id=NEW.session_id AND event_id=NEW.event_id",
                "native execution events are append-only",
            ),
            (
                "emergency_events",
                "session_id=NEW.session_id AND (event_id=NEW.event_id OR sequence=NEW.sequence)",
                "emergency events are append-only",
            ),
            (
                "native_admission_decisions",
                "command_id=NEW.command_id",
                "native admission decisions are immutable",
            ),
        ):
            op.execute(
                sa.text(
                    f"CREATE TRIGGER {table}_no_replace BEFORE INSERT ON {table} "
                    f"WHEN EXISTS (SELECT 1 FROM {table} WHERE {identity}) "
                    f"BEGIN SELECT RAISE(ABORT, '{message}'); END"
                )
            )
            for action in ("UPDATE", "DELETE"):
                op.execute(
                    sa.text(
                        f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} "
                        f"BEGIN SELECT RAISE(ABORT, '{message}'); END"
                    )
                )


def downgrade() -> None:
    tables = (
        "emergency_events",
        "emergency_states",
        "native_admission_decisions",
        "execution_reservations",
        "native_execution_events",
        "reconciliation_snapshots",
        "account_sessions",
    )
    bind = op.get_bind()
    for table in tables:
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None:
            raise RuntimeError(f"refusing downgrade: {table} contains user data; preserve its backup first")
    if bind.dialect.name == "sqlite":
        for table in (
            "emergency_events",
            "native_execution_events",
            "reconciliation_snapshots",
            "native_admission_decisions",
        ):
            for suffix in ("no_delete", "no_update", "no_replace"):
                op.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_{suffix}"))
    op.drop_index("ix_emergency_event_session", table_name="emergency_events")
    op.drop_table("emergency_events")
    op.drop_table("emergency_states")
    op.drop_table("native_admission_decisions")
    op.drop_table("execution_reservations")
    op.drop_index("ix_native_execution_occurred_at", table_name="native_execution_events")
    op.drop_index("ix_native_execution_client_order", table_name="native_execution_events")
    op.drop_table("native_execution_events")
    op.drop_index("ix_reconciliation_observed_at", table_name="reconciliation_snapshots")
    op.drop_table("reconciliation_snapshots")
    op.drop_index("ix_account_session_status", table_name="account_sessions")
    op.drop_table("account_sessions")
