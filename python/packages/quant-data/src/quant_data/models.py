"""SQLAlchemy models managed exclusively through Alembic migrations."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared migration metadata."""


class TradeEvent(Base):
    """Append-only execution, risk, and decision audit event."""

    __tablename__ = "trade_events"
    __table_args__ = (Index("ix_trade_events_created_at", "created_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(32))
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MarketSnapshotProjection(Base):
    """Latest validated public market observation per environment and symbol.

    This is a mutable read projection, deliberately separate from append-only
    audit events. Prices remain canonical decimal strings so restoring a
    snapshot never introduces binary-float rounding.
    """

    __tablename__ = "market_snapshot_projections"
    __table_args__ = (
        UniqueConstraint("environment", "symbol", name="uq_market_snapshot_environment_symbol"),
        Index("ix_market_snapshot_updated_at", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    last_price: Mapped[str | None] = mapped_column(String(128))
    bid_price: Mapped[str | None] = mapped_column(String(128))
    ask_price: Mapped[str | None] = mapped_column(String(128))
    event_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    received_at: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StrategyVersion(Base):
    """Immutable candidate strategy metadata and validation state."""

    __tablename__ = "strategy_versions"
    __table_args__ = (UniqueConstraint("strategy_id", "version"),)

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


class AiPaperDecisionBinding(Base):
    """Durable idempotency binding for internal synthetic-paper decisions."""

    __tablename__ = "ai_paper_decision_bindings"
    __table_args__ = (
        UniqueConstraint("command_id", name="uq_ai_paper_binding_command"),
        UniqueConstraint("native_client_order_id", name="uq_ai_paper_binding_native_id"),
        Index("ix_ai_paper_binding_decision_id", "decision_id"),
    )

    environment: Mapped[str] = mapped_column(String(16), primary_key=True)
    account_ref: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fixture_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    command_id: Mapped[str] = mapped_column(String(36), ForeignKey("execution_commands.id"), nullable=False)
    native_client_order_id: Mapped[str] = mapped_column(String(36), nullable=False)
    receipt_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AiPaperCycleReceipt(Base):
    """Immutable idempotency header shared by order and no-order AI cycles."""

    __tablename__ = "ai_paper_cycle_receipts"
    __table_args__ = (UniqueConstraint("environment", "account_ref", "request_id", name="uq_ai_paper_cycle_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    account_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fixture_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AiPaperCycleEvent(Base):
    """Append-only state events; latest receipt state is a query projection."""

    __tablename__ = "ai_paper_cycle_events"
    __table_args__ = (
        UniqueConstraint("receipt_id", "event_id", name="uq_ai_paper_cycle_event_id"),
        UniqueConstraint("receipt_id", "sequence", name="uq_ai_paper_cycle_event_sequence"),
        Index("ix_ai_paper_cycle_event_receipt", "receipt_id", "sequence"),
        Index("ix_ai_paper_cycle_event_claim_owner", "claim_owner"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_paper_cycle_receipts.id"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(128))
    strategy_digest: Mapped[str | None] = mapped_column(String(64))
    evidence_digest: Mapped[str | None] = mapped_column(String(64))
    client_order_id: Mapped[str | None] = mapped_column(String(36))
    command_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("execution_commands.id"))
    generation: Mapped[int | None] = mapped_column(Integer)
    claim_owner: Mapped[str | None] = mapped_column(String(128))
    claim_deadline_ns: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AccountSession(Base):
    """Durable identity and protection fence for one authenticated account generation."""

    __tablename__ = "account_sessions"
    __table_args__ = (
        UniqueConstraint("environment", "account_ref", name="uq_account_session_scope"),
        Index("ix_account_session_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    account_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    expected_uid: Mapped[str | None] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    protected: Mapped[int] = mapped_column(Integer, nullable=False)
    protection_reason: Mapped[str | None] = mapped_column(String(128))
    reconciliation_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    config_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReconciliationSnapshot(Base):
    """Immutable, redacted account evidence joined at one reconciliation revision."""

    __tablename__ = "reconciliation_snapshots"
    __table_args__ = (
        UniqueConstraint("session_id", "revision", name="uq_reconciliation_revision"),
        Index("ix_reconciliation_observed_at", "observed_at_ns"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), ForeignKey("account_sessions.id"), nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    wallet_json: Mapped[str] = mapped_column(Text, nullable=False)
    positions_json: Mapped[str] = mapped_column(Text, nullable=False)
    orders_json: Mapped[str] = mapped_column(Text, nullable=False)
    executions_json: Mapped[str] = mapped_column(Text, nullable=False)
    complete: Mapped[int] = mapped_column(Integer, nullable=False)
    protected_reason: Mapped[str | None] = mapped_column(String(128))
    observed_at_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NativeExecutionEvent(Base):
    """Append-only private venue event; payload is redacted before persistence."""

    __tablename__ = "native_execution_events"
    __table_args__ = (
        UniqueConstraint("session_id", "event_id", name="uq_native_execution_event"),
        Index("ix_native_execution_client_order", "client_order_id"),
        Index("ix_native_execution_occurred_at", "occurred_at_ns"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), ForeignKey("account_sessions.id"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    command_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("execution_commands.id"))
    client_order_id: Mapped[str | None] = mapped_column(String(36))
    venue_order_id: Mapped[str | None] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    applied: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ExecutionReservation(Base):
    """Server-owned exposure reservation shared by native admission and reconciliation."""

    __tablename__ = "execution_reservations"
    command_id: Mapped[str] = mapped_column(String(36), ForeignKey("execution_commands.id"), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), ForeignKey("account_sessions.id"), nullable=False)
    account_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    reconciliation_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol: Mapped[str] = mapped_column(String(128), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    remaining_quantity: Mapped[str] = mapped_column(String(64), nullable=False)
    reserved_notional: Mapped[str] = mapped_column(String(64), nullable=False)
    reserved_at_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)


class NativeAdmissionDecision(Base):
    """Immutable, generation-bound risk result for a native Testnet command."""

    __tablename__ = "native_admission_decisions"
    command_id: Mapped[str] = mapped_column(String(36), ForeignKey("execution_commands.id"), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), ForeignKey("account_sessions.id"), nullable=False)
    allowed: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_code: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    context_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    account_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    reconciliation_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_at_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reservation_price: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmergencyState(Base):
    """Current durable emergency fence; transitions are recorded separately."""

    __tablename__ = "emergency_states"
    session_id: Mapped[str] = mapped_column(String(128), ForeignKey("account_sessions.id"), primary_key=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(128))
    command_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("execution_commands.id"))
    updated_at_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)


class EmergencyEvent(Base):
    """Append-only emergency command history."""

    __tablename__ = "emergency_events"
    __table_args__ = (
        UniqueConstraint("session_id", "event_id", name="uq_emergency_event"),
        UniqueConstraint("session_id", "sequence", name="uq_emergency_event_sequence"),
        Index("ix_emergency_event_session", "session_id", "sequence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), ForeignKey("account_sessions.id"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(128))
    command_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("execution_commands.id"))
    occurred_at_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
