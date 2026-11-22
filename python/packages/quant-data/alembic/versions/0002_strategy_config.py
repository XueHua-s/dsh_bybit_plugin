"""Extract strategy configuration while preserving historical strategy rows."""

import sqlalchemy as sa

from alembic import op

revision = "0002_strategy_config"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("strategy_versions", sa.Column("strategy_config_json", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE strategy_versions SET strategy_config_json = metadata_json"))


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("strategy_versions", "trade_events"):
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None:
            raise RuntimeError(
                f"refusing downgrade: {table} contains user data; export and explicitly preserve it first"
            )
    op.drop_column("strategy_versions", "strategy_config_json")
