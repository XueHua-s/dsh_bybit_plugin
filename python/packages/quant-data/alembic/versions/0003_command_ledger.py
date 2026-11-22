"""Durable scoped command admission, dispatch claims and append-only audit."""

import sqlalchemy as sa

from alembic import op

revision = "0003_command_ledger"
down_revision = "0002_strategy_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_commands",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("environment", sa.String(16), nullable=False),
        sa.Column("account_ref", sa.String(128), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("command_json", sa.Text(), nullable=False),
        sa.Column("native_client_order_id", sa.String(36), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("cumulative_filled", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("environment", "account_ref", "request_id", name="uq_command_scope_request"),
        sa.UniqueConstraint("native_client_order_id", name="uq_command_native_id"),
    )
    op.create_table(
        "command_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("command_id", sa.String(36), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("cumulative_filled", sa.String(64), nullable=False),
        sa.Column("decision_code", sa.String(32), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["command_id"], ["execution_commands.id"]),
        sa.UniqueConstraint("command_id", "event_id", name="uq_command_event_id"),
        sa.UniqueConstraint("command_id", "version", name="uq_command_event_version"),
    )
    if op.get_bind().dialect.name == "sqlite":
        op.execute(
            sa.text(
                "CREATE TRIGGER command_events_no_replace BEFORE INSERT ON command_events "
                "WHEN EXISTS (SELECT 1 FROM command_events WHERE id=NEW.id OR "
                "(command_id=NEW.command_id AND (event_id=NEW.event_id OR version=NEW.version))) "
                "BEGIN SELECT RAISE(ABORT, 'command events are append-only'); END"
            )
        )
        for action in ("UPDATE", "DELETE"):
            op.execute(
                sa.text(
                    f"CREATE TRIGGER command_events_no_{action.lower()} BEFORE {action} ON command_events "
                    "BEGIN SELECT RAISE(ABORT, 'command events are append-only'); END"
                )
            )


def downgrade() -> None:
    for table in ("command_events", "execution_commands"):
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None:
            raise RuntimeError(f"refusing downgrade: {table} contains user data; preserve its backup first")
    op.drop_table("command_events")
    op.drop_table("execution_commands")
