"""Add durable paper ownership, immutable decisions, reservations and projections."""

import sqlalchemy as sa

from alembic import op

revision = "0004_admission_state"
down_revision = "0003_command_ledger"
branch_labels = None
depends_on = None
_TABLES = (
    "paper_sessions",
    "admission_decisions",
    "paper_reservations",
    "paper_positions",
    "paper_native_events",
    "paper_protection_events",
)
_SCHEMA = (
    "\nCREATE TABLE paper_sessions (\n\tid VARCHAR(128) NOT NULL, \n\taccount_ref VARCHAR(128) NOT NULL, \n\towner_id VARCHAR(128) NOT NULL, \n\tconfig_fingerprint VARCHAR(64) NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tprotected INTEGER NOT NULL, \n\tprotection_reason VARCHAR(128), \n\tbalance VARCHAR(128) NOT NULL, \n\taccounting_model VARCHAR(32) NOT NULL, \n\trealized_pnl VARCHAR(128) NOT NULL, \n\tcumulative_fee VARCHAR(128) NOT NULL, \n\tlast_admitted_at_ns INTEGER, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_paper_account UNIQUE (account_ref)\n)\n\n",
    "\nCREATE TABLE admission_decisions (\n\tcommand_id VARCHAR(36) NOT NULL, \n\tsession_id VARCHAR(128) NOT NULL, \n\tallowed INTEGER NOT NULL, \n\tcode VARCHAR(32) NOT NULL, \n\tpolicy_fingerprint VARCHAR(64) NOT NULL, \n\tcontext_fingerprint VARCHAR(64) NOT NULL, \n\treasons_json TEXT NOT NULL, \n\tcontext_generation INTEGER NOT NULL, \n\tevaluated_at_ns INTEGER NOT NULL, \n\texpires_at_ns INTEGER NOT NULL, \n\treservation_price VARCHAR(64) NOT NULL, \n\tPRIMARY KEY (command_id), \n\tFOREIGN KEY(command_id) REFERENCES execution_commands (id), \n\tFOREIGN KEY(session_id) REFERENCES paper_sessions (id)\n)\n\n",
    "\nCREATE TABLE paper_reservations (\n\tcommand_id VARCHAR(36) NOT NULL, \n\tsession_id VARCHAR(128) NOT NULL, \n\tsymbol VARCHAR(128) NOT NULL, \n\tside VARCHAR(8) NOT NULL, \n\tremaining_quantity VARCHAR(64) NOT NULL, \n\tprice VARCHAR(64) NOT NULL, \n\tcumulative_notional VARCHAR(64) NOT NULL, \n\tcumulative_fee VARCHAR(64) NOT NULL, \n\tlast_event_ns INTEGER NOT NULL, \n\tPRIMARY KEY (command_id), \n\tFOREIGN KEY(command_id) REFERENCES execution_commands (id), \n\tFOREIGN KEY(session_id) REFERENCES paper_sessions (id)\n)\n\n",
    "\nCREATE TABLE paper_positions (\n\tsession_id VARCHAR(128) NOT NULL, \n\tsymbol VARCHAR(128) NOT NULL, \n\tquantity VARCHAR(80) NOT NULL, \n\taverage_entry_price VARCHAR(128) NOT NULL, \n\tPRIMARY KEY (session_id, symbol), \n\tFOREIGN KEY(session_id) REFERENCES paper_sessions (id)\n)\n\n",
    "\nCREATE TABLE paper_native_events (\n\tsession_id VARCHAR(128) NOT NULL, \n\tevent_id VARCHAR(128) NOT NULL, \n\tcommand_id VARCHAR(36) NOT NULL, \n\tfingerprint VARCHAR(64) NOT NULL, \n\tstate VARCHAR(32) NOT NULL, \n\tcumulative_filled VARCHAR(64) NOT NULL, \n\tcumulative_notional VARCHAR(64) NOT NULL, \n\tcumulative_fee VARCHAR(64) NOT NULL, \n\toccurred_at_ns INTEGER NOT NULL, \n\tapplied INTEGER NOT NULL, \n\tPRIMARY KEY (session_id, event_id), \n\tFOREIGN KEY(session_id) REFERENCES paper_sessions (id), \n\tFOREIGN KEY(command_id) REFERENCES execution_commands (id)\n)\n\n",
    "\nCREATE TABLE paper_protection_events (\n\tsession_id VARCHAR(128) NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\treason VARCHAR(128) NOT NULL, \n\tPRIMARY KEY (session_id, generation), \n\tFOREIGN KEY(session_id) REFERENCES paper_sessions (id)\n)\n\n",
)


def upgrade() -> None:
    for ddl in _SCHEMA:
        op.execute(sa.text(ddl))
    if op.get_bind().dialect.name == "sqlite":
        for table, identity in (
            ("admission_decisions", "command_id=NEW.command_id"),
            ("paper_native_events", "session_id=NEW.session_id AND event_id=NEW.event_id"),
            ("paper_protection_events", "session_id=NEW.session_id AND generation=NEW.generation"),
        ):
            op.execute(
                sa.text(
                    f"CREATE TRIGGER {table}_no_replace BEFORE INSERT ON {table} "
                    f"WHEN EXISTS (SELECT 1 FROM {table} WHERE {identity}) "
                    "BEGIN SELECT RAISE(ABORT, 'admission evidence is append-only'); END"
                )
            )
            for action in ("UPDATE", "DELETE"):
                op.execute(
                    sa.text(
                        f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} "
                        "BEGIN SELECT RAISE(ABORT, 'admission evidence is append-only'); END"
                    )
                )


def downgrade() -> None:
    for table in _TABLES:
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None:
            raise RuntimeError(f"refusing downgrade: {table} contains user data; preserve its backup first")
    for table in reversed(_TABLES):
        op.drop_table(table)
