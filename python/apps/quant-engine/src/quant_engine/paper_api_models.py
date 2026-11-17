"""Canonical bounded paper HTTP schema; proposals contain no trusted account truth."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Opaque = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$", max_length=128)]
DecimalText = Annotated[str, Field(pattern=r"^(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?$", max_length=21)]


class PaperModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


class SessionRequest(PaperModel):
    environment: Literal["internal_paper"]
    session_id: Opaque


class SubmitRequest(SessionRequest):
    request_id: Opaque
    symbol: Literal["BTCUSDT"]
    side: Literal["buy", "sell"]
    order_type: Literal["limit"]
    quantity: DecimalText
    limit_price: DecimalText


class CommandResponse(PaperModel):
    command_id: Opaque
    environment: Literal["internal_paper"] = "internal_paper"
    session_id: Opaque
    native_client_order_id: Opaque
    state: Literal[
        "admitted",
        "ready",
        "risk_rejected",
        "dispatching",
        "accepted",
        "partially_filled",
        "filled",
        "cancelled",
        "rejected",
        "reconciliation_required",
    ]
    cumulative_filled: DecimalText


class PaperStatus(PaperModel):
    environment: Literal["internal_paper"] = "internal_paper"
    synthetic: Literal[True] = True
    session_id: Opaque
    state: Literal["idle", "running", "protected", "stopping", "stopped"]
    ready: bool
    native_process_alive: bool
    generation: Annotated[int, Field(ge=0)]
    pending_reservations: Annotated[int, Field(ge=0)]


class PaperError(PaperModel):
    detail: str
