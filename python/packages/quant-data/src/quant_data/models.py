"""SQLAlchemy models managed exclusively through Alembic migrations."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared migration metadata."""


class TradeEvent(Base):
    """Append-only execution, risk, and decision audit event."""

    __tablename__ = "trade_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(32))
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StrategyVersion(Base):
    """Immutable candidate strategy metadata and validation state."""

    __tablename__ = "strategy_versions"
    __table_args__ = (UniqueConstraint("strategy_id", "version", name="uq_strategy_versions_id_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    strategy_config_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ExecutionCommand(Base):
    """Durable submit intent; only the ledger may change its lifecycle columns."""

    __tablename__ = "execution_commands"
    __table_args__ = (
        UniqueConstraint("environment", "account_ref", "request_id", name="uq_command_scope_request"),
        UniqueConstraint("native_client_order_id", name="uq_command_native_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    account_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    command_json: Mapped[str] = mapped_column(Text, nullable=False)
    native_client_order_id: Mapped[str] = mapped_column(String(36), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    cumulative_filled: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)


class CommandEvent(Base):
    """Immutable event history; event IDs are scoped to a single command."""

    __tablename__ = "command_events"
    __table_args__ = (
        UniqueConstraint("command_id", "event_id", name="uq_command_event_id"),
        UniqueConstraint("command_id", "version", name="uq_command_event_version"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    command_id: Mapped[str] = mapped_column(String(36), ForeignKey("execution_commands.id"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    cumulative_filled: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_code: Mapped[str | None] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
