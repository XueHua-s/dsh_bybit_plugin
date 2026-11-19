"""Initial append-only quant audit schema."""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trade_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("environment", sa.String(16), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trade_events_created_at", "trade_events", ["created_at"])
    op.create_table(
        "strategy_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("strategy_id", sa.String(128), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("validation_status", sa.String(32), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("strategy_id", "version"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("strategy_versions", "trade_events"):
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None:
            raise RuntimeError(
                f"refusing downgrade: {table} contains user data; export and explicitly preserve it first"
            )
    op.drop_table("strategy_versions")
    op.drop_index("ix_trade_events_created_at", table_name="trade_events")
    op.drop_table("trade_events")
