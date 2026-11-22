"""Small adapter for AI-cycle operations on the long-lived paper authority."""

from __future__ import annotations

import asyncio
import re
import time
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, cast
from uuid import uuid4

from quant_data.admission_contracts import SessionSnapshot
from quant_data.commands import LedgerConflict
from quant_execution.paper_models import PaperSnapshot
from quant_portfolio import PortfolioPolicy, PositionExposure, TargetProposal, plan_targets
from sqlalchemy.exc import SQLAlchemyError

from .ai_paper_contracts import CycleReceipt, DecisionRequest
from .paper_api_models import SubmitRequest
from .paper_context import selector_inputs
from .paper_order_mapper import map_exposure_delta
from .portfolio import selection_to_proposal
from .strategy_selector import select_strategy
from .synthetic_fixture_registry import PaperFixtureBundle, SyntheticFixtureRegistry

if TYPE_CHECKING:
    from .paper_admission import PaperAdmission


async def planning_snapshot(admission: PaperAdmission) -> tuple[SessionSnapshot, PaperSnapshot]:
    """Return one reconciled synthetic snapshot for account-free planning."""

    def read() -> tuple[SessionSnapshot, PaperSnapshot]:
        with admission._lock:  # type: ignore[union-attr]
            store, _, runtime = admission._required()
            if admission._state != "running":
                from .paper_admission import PaperUnavailable

                raise PaperUnavailable("paper_not_running")
            admission._drain()
            durable = store.snapshot(admission.config.session_id, admission._owner)
            native = runtime.snapshot()
            if (
                durable.protected
                or not native.process_alive
                or native.status != "running"
                or not native.event_stream_complete
                or native.failure_reason is not None
                or {item.symbol: item.quantity for item in durable.positions if item.quantity}
                != {item.symbol: item.position_quantity for item in native.instruments if item.position_quantity}
            ):
                admission._protect("planning_snapshot_unreconciled")
                from .paper_admission import PaperUnavailable

                raise PaperUnavailable("planning_snapshot_unreconciled")
            return durable, native

    return await asyncio.to_thread(read)


async def submit_ai_order(
    admission: PaperAdmission,
    request: SubmitRequest,
    *,
    request_digest: str,
    decision_id: str,
    fixture_digest: str,
):
    """Submit a mapped AI order with durable identity binding."""
    return await admission._submit_async(request, (request_digest, decision_id, fixture_digest))


async def get_by_request(admission: PaperAdmission, request_id: str):
    """Resolve a durable order receipt without reconstructing or resubmitting it."""

    def lookup():
        with admission._lock:
            if admission._store is None:
                from .paper_admission import PaperUnavailable

                raise PaperUnavailable("database_unavailable")
            try:
                return admission._store.get_by_request(request_id, admission.config.session_id, admission._owner)
            except SQLAlchemyError:
                admission._protect("command_read_failed")
                from .paper_admission import PaperUnavailable

                raise PaperUnavailable("command_read_failed") from None

    return await asyncio.to_thread(lookup)


class PaperCycleService:
    """Run a decision through fixture-owned selector, planner, mapper and admission."""

    def __init__(self, admission: PaperAdmission, registry: SyntheticFixtureRegistry) -> None:
        self._admission = admission
        self._registry = registry

    async def submit(self, request: DecisionRequest) -> CycleReceipt:
        admission = self._admission
        receipts = admission._receipt_store
        if receipts is None:
            from .paper_admission import PaperUnavailable

            raise PaperUnavailable("database_unavailable")
        bundle = self._registry.resolve(request.fixture_id, request.bundle_digest)
        header, created = receipts.begin(
            admission.config.session_id,
            admission._owner,
            request.request_id,
            request.payload_digest,
            request.decision.decision_id,
            bundle.digest,
            claim_owner=str(uuid4()),
            claim_deadline_ns=time.time_ns() + 30_000_000_000,
        )
        if not created:
            return _receipt(header)
        try:
            return await self._execute(request, bundle)
        except LedgerConflict:
            raise
        except (ValueError, ArithmeticError) as error:
            header = receipts.append(
                admission.config.session_id,
                admission._owner,
                request.request_id,
                "rejected",
                reason=_reason(str(error)),
            )
            return _receipt(header)
        except Exception as error:  # noqa: BLE001 - unknown failures must fail closed and become recoverable
            header = receipts.append(
                admission.config.session_id,
                admission._owner,
                request.request_id,
                "protected",
                reason="internal_failure:" + _reason(type(error).__name__),
            )
            return _receipt(header)

    async def get(self, request_id: str) -> CycleReceipt:
        receipts = self._admission._receipt_store
        if receipts is None:
            from .paper_admission import PaperUnavailable

            raise PaperUnavailable("database_unavailable")
        return _receipt(receipts.get(self._admission.config.session_id, self._admission._owner, request_id))

    async def _execute(self, request: DecisionRequest, bundle: PaperFixtureBundle) -> CycleReceipt:
        admission = self._admission
        receipts = admission._receipt_store
        assert receipts is not None
        session_id, owner = admission.config.session_id, admission._owner
        now_ns = time.time_ns()
        try:
            snapshot = bundle.snapshot(now_ns=now_ns, ttl_ns=60_000_000_000)
        except ValueError as error:
            return _receipt(
                receipts.append(session_id, owner, request.request_id, "rejected", reason=_reason(str(error)))
            )
        if request.expires_at_ns <= now_ns:
            return _receipt(receipts.append(session_id, owner, request.request_id, "rejected", reason="stale_request"))
        if request.expires_at_ns > cast(int, snapshot["expires_at_ns"]):
            return _receipt(
                receipts.append(
                    session_id, owner, request.request_id, "rejected", reason="request_expires_after_fixture"
                )
            )
        track = request.decision
        if track.action == "abstain":
            return _receipt(receipts.append(session_id, owner, request.request_id, "abstained", reason="ai_abstained"))
        fixture = bundle.resolve(track.symbol)
        market, candidates, registry = selector_inputs(bundle, track.symbol)
        selection = select_strategy(market, candidates, registry, time.time_ns() // 1_000_000)
        evidence = next(
            (
                item
                for item in bundle.evidence_by_symbol[track.symbol]
                if (item.strategy_id, item.version) == (track.strategy_id, track.strategy_version)
            ),
            None,
        )
        if selection.kind == "abstain":
            return _receipt(
                receipts.append(session_id, owner, request.request_id, "abstained", reason="selector_abstained")
            )
        if (selection.strategy_id, selection.version) != (track.strategy_id, track.strategy_version):
            return _receipt(
                receipts.append(session_id, owner, request.request_id, "rejected", reason="selector_identity_mismatch")
            )
        if evidence is None or evidence.evidence_digest != track.evidence_digest or not evidence.ready_signal:
            return _receipt(
                receipts.append(session_id, owner, request.request_id, "rejected", reason="evidence_mismatch")
            )
        if (
            selection.signal is None
            or (track.action == "long" and selection.signal.target_exposure <= 0)
            or (track.action == "short" and selection.signal.target_exposure >= 0)
        ):
            return _receipt(
                receipts.append(session_id, owner, request.request_id, "abstained", reason="selector_signal_mismatch")
            )
        receipts.append(
            session_id,
            owner,
            request.request_id,
            "selected",
            strategy_digest=bundle.digest,
            evidence_digest=evidence.evidence_digest,
        )
        proposal = selection_to_proposal(track.symbol, selection)
        if proposal is None:
            return _receipt(
                receipts.append(session_id, owner, request.request_id, "abstained", reason="selector_abstained")
            )
        proposal = TargetProposal(
            proposal.symbol,
            proposal.strategy_id,
            proposal.strategy_version,
            track.target_exposure,
            proposal.confidence,
            proposal.evidence_ref,
            proposal.expires_at_ms,
        )
        durable, native = await admission.planning_snapshot()
        equity = native.equity
        marks = {item.symbol: max(item.bid, item.ask) for item in native.instruments}
        current = tuple(
            PositionExposure(item.symbol, float(item.quantity * marks[item.symbol] / equity))
            for item in durable.positions
            if item.quantity
        )
        policy = PortfolioPolicy(1.0, 0.5, 0.0, 0.5, time.time_ns() // 1_000_000)
        plan = plan_targets((proposal,), current, policy)
        transition = next((item for item in plan.transitions if item.symbol == track.symbol), None)
        if transition is None or transition.reason in {"hold", "abstain"}:
            return _receipt(
                receipts.append(session_id, owner, request.request_id, "abstained", reason="portfolio_noop")
            )
        if len(transition.steps) != 1 or transition.steps[0].phase == "hold":
            return _receipt(
                receipts.append(session_id, owner, request.request_id, "rejected", reason="reversal_requires_recheck")
            )
        mapped = map_exposure_delta(
            request_id=request.request_id,
            symbol=track.symbol,
            delta_exposure=Decimal(str(transition.steps[0].delta_exposure)),
            equity=equity,
            instrument=fixture.instrument,
            depth=fixture.initial_depth,
            now_ns=time.time_ns(),
            max_age_ns=admission.config.policy.snapshot_ttl_ms * 1_000_000,
        )
        if mapped is None:
            return _receipt(
                receipts.append(session_id, owner, request.request_id, "risk_rejected", reason="mapping_rejected")
            )
        side: Literal["buy", "sell"] = "buy" if mapped.intent.side == "BUY" else "sell"
        submit = SubmitRequest(
            environment="internal_paper",
            session_id=session_id,
            request_id=request.request_id,
            symbol=track.symbol,
            side=side,
            order_type="limit",
            quantity=str(mapped.intent.quantity),
            limit_price=str(mapped.executable_price),
        )
        command = await admission.submit_ai_order(
            submit, request_digest=request.payload_digest, decision_id=track.decision_id, fixture_digest=bundle.digest
        )
        command_state = command.state.value
        generation = (await admission.status()).generation
        if command_state == "risk_rejected":
            header = receipts.append(
                session_id,
                owner,
                request.request_id,
                "risk_rejected",
                reason="independent_risk_veto",
                command_id=command.id,
                client_order_id=command.native_client_order_id,
                generation=generation,
            )
        elif command_state == "rejected":
            header = receipts.append(
                session_id,
                owner,
                request.request_id,
                "rejected",
                reason="synthetic_oms_rejected",
                command_id=command.id,
                client_order_id=command.native_client_order_id,
                generation=generation,
            )
        elif command_state == "reconciliation_required":
            header = receipts.append(
                session_id,
                owner,
                request.request_id,
                "protected",
                reason="oms_reconciliation_required",
                command_id=command.id,
                client_order_id=command.native_client_order_id,
                generation=generation,
            )
        else:
            header = receipts.append(
                session_id,
                owner,
                request.request_id,
                "admitted",
                command_id=command.id,
                client_order_id=command.native_client_order_id,
                generation=generation,
            )
            terminal = {"accepted": "accepted", "partially_filled": "partially_filled", "filled": "filled"}
            if command_state in terminal:
                header = receipts.append(
                    session_id,
                    owner,
                    request.request_id,
                    terminal[command_state],
                    command_id=command.id,
                    client_order_id=command.native_client_order_id,
                    generation=generation,
                )
            elif command_state not in {"admitted", "ready", "dispatching"}:
                header = receipts.append(
                    session_id,
                    owner,
                    request.request_id,
                    "protected",
                    reason="unknown_oms_state",
                    command_id=command.id,
                    client_order_id=command.native_client_order_id,
                    generation=generation,
                )
        return _receipt(header)


def _reason(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]", "_", value)[:120] or "cycle_rejected"


def _receipt(value: dict[str, object]) -> CycleReceipt:
    statuses = {
        "abstained",
        "claimed",
        "rejected",
        "selected",
        "risk_rejected",
        "admitted",
        "accepted",
        "partially_filled",
        "filled",
        "protected",
        "unknown",
    }
    raw_status = value.get("status")
    status = (
        cast(
            Literal[
                "abstained",
                "selected",
                "risk_rejected",
                "admitted",
                "accepted",
                "partially_filled",
                "filled",
                "protected",
                "unknown",
            ],
            raw_status,
        )
        if isinstance(raw_status, str) and raw_status in statuses
        else "unknown"
    )
    reason = value.get("reason")
    command_id = value.get("command_id")
    native_order_id = value.get("native_client_order_id")
    return CycleReceipt(
        schema_version="1",
        request_id=str(value["request_id"]),
        payload_digest=str(value["payload_digest"]),
        decision_id=str(value["decision_id"]),
        status=status,
        reason=reason if isinstance(reason, str) else None,
        command_id=command_id if isinstance(command_id, str) else None,
        native_client_order_id=native_order_id if isinstance(native_order_id, str) else None,
    )
