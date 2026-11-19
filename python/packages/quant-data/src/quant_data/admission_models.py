"""Admission persistence; signed accounting amounts use canonical decimal strings."""

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from quant_data.models import Base


class PaperSession(Base):
    __tablename__ = "paper_sessions"
    __table_args__ = (UniqueConstraint("account_ref", name="uq_paper_account"),)
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    account_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    config_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    protected: Mapped[int] = mapped_column(Integer, nullable=False)
    protection_reason: Mapped[str | None] = mapped_column(String(128))
    balance: Mapped[str] = mapped_column(String(128), nullable=False)
    accounting_model: Mapped[str] = mapped_column(String(32), nullable=False)
    realized_pnl: Mapped[str] = mapped_column(String(128), nullable=False)
    cumulative_fee: Mapped[str] = mapped_column(String(128), nullable=False)
    last_admitted_at_ns: Mapped[int | None] = mapped_column(Integer)


class RiskDecision(Base):
    __tablename__ = "admission_decisions"
    command_id: Mapped[str] = mapped_column(ForeignKey("execution_commands.id"), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("paper_sessions.id"), nullable=False)
    allowed: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    context_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False)
    context_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_at_ns: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at_ns: Mapped[int] = mapped_column(Integer, nullable=False)
    reservation_price: Mapped[str] = mapped_column(String(64), nullable=False)


class Reservation(Base):
    __tablename__ = "paper_reservations"
    command_id: Mapped[str] = mapped_column(ForeignKey("execution_commands.id"), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("paper_sessions.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(128), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    remaining_quantity: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[str] = mapped_column(String(64), nullable=False)
    cumulative_notional: Mapped[str] = mapped_column(String(64), nullable=False)
    cumulative_fee: Mapped[str] = mapped_column(String(64), nullable=False)
    last_event_ns: Mapped[int] = mapped_column(Integer, nullable=False)


class PaperPosition(Base):
    __tablename__ = "paper_positions"
    session_id: Mapped[str] = mapped_column(ForeignKey("paper_sessions.id"), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(128), primary_key=True)
    quantity: Mapped[str] = mapped_column(String(80), nullable=False)
    average_entry_price: Mapped[str] = mapped_column(String(128), nullable=False)


class NativeEvent(Base):
    __tablename__ = "paper_native_events"
    session_id: Mapped[str] = mapped_column(ForeignKey("paper_sessions.id"), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    command_id: Mapped[str] = mapped_column(ForeignKey("execution_commands.id"), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    cumulative_filled: Mapped[str] = mapped_column(String(64), nullable=False)
    cumulative_notional: Mapped[str] = mapped_column(String(64), nullable=False)
    cumulative_fee: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at_ns: Mapped[int] = mapped_column(Integer, nullable=False)
    applied: Mapped[int] = mapped_column(Integer, nullable=False)


class ProtectionEvent(Base):
    __tablename__ = "paper_protection_events"
    session_id: Mapped[str] = mapped_column(ForeignKey("paper_sessions.id"), primary_key=True)
    generation: Mapped[int] = mapped_column(Integer, primary_key=True)
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
