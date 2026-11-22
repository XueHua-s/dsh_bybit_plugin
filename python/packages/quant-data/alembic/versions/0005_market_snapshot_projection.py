"""Persist the latest validated public market observation per symbol."""

import sqlalchemy as sa

from alembic import op

revision = "0005_market_snapshot_projection"
down_revision = "0004_admission_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_snapshot_projections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("environment", sa.String(16), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("last_price", sa.String(128), nullable=True),
        sa.Column("bid_price", sa.String(128), nullable=True),
        sa.Column("ask_price", sa.String(128), nullable=True),
        sa.Column("event_time_ms", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.String(64), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("environment", "symbol", name="uq_market_snapshot_environment_symbol"),
    )
    op.create_index("ix_market_snapshot_updated_at", "market_snapshot_projections", ["updated_at"])


def downgrade() -> None:
    if op.get_bind().execute(sa.text("SELECT 1 FROM market_snapshot_projections LIMIT 1")).first() is not None:
        raise RuntimeError(
            "refusing downgrade: market snapshot projections contain user data; preserve its backup first"
        )
    op.drop_index("ix_market_snapshot_updated_at", table_name="market_snapshot_projections")
    op.drop_table("market_snapshot_projections")
