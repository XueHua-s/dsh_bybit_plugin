"""Authenticated local paper control; transport cannot construct trusted risk context."""

import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from quant_data.commands import LedgerConflict

from .paper_admission import PaperAdmission, PaperUnavailable
from .paper_api_models import CommandResponse, Opaque, PaperError, PaperStatus, SessionRequest, SubmitRequest
from .paper_config import Capability, PaperConfig


def create_paper_app(config: PaperConfig, capability: Capability, *, service: PaperAdmission | None = None) -> FastAPI:
    """Construct offline; lifespan owns a single explicit paper service and no market network."""
    if capability.session_id != config.session_id:
        raise ValueError("principal_scope_mismatch")
    engine = service or PaperAdmission(config)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await engine.open()
        try:
            yield
        finally:
            await engine.close()

    app = FastAPI(title="Bybit Quant Internal Paper", version="0.1.0", lifespan=lifespan, redirect_slashes=False)
    bearer = HTTPBearer(auto_error=False)

    async def observe(
        request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
    ) -> None:
        if request.headers.get("origin") is not None:
            raise HTTPException(403, "origin_forbidden")
        supplied = b"" if credentials is None else credentials.credentials.encode("utf-8")
        if len(supplied) > 128 or not hmac.compare_digest(supplied, capability.token):
            raise HTTPException(401, "authentication_required")
        if "observe" not in capability.scopes:
            raise HTTPException(403, "scope_forbidden")

    async def control(_principal: Annotated[None, Depends(observe)]) -> None:
        if "control" not in capability.scopes:
            raise HTTPException(403, "scope_forbidden")

    # Bound the actual ASGI bytes, including chunked bodies, before JSON decoding.
    @app.middleware("http")
    async def bounded(request: Request, call_next):  # type: ignore[no-untyped-def]
        lengths = request.headers.getlist("content-length")
        if len(lengths) > 1 or (
            lengths and (len(lengths[0]) > 4 or not lengths[0].isdigit() or int(lengths[0]) > 4096)
        ):
            return JSONResponse({"detail": "request_too_large_or_invalid"}, status_code=413)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 4096:
                return JSONResponse({"detail": "request_too_large_or_invalid"}, status_code=413)
        request._body = bytes(body)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def invalid(_request: Request, _error: RequestValidationError) -> JSONResponse:
        return JSONResponse({"detail": "invalid_request"}, status_code=422)

    @app.exception_handler(PaperUnavailable)
    async def unavailable(_request: Request, _error: PaperUnavailable) -> JSONResponse:
        return JSONResponse({"detail": "paper_unavailable"}, status_code=503)

    @app.exception_handler(LedgerConflict)
    async def conflict(_request: Request, _error: LedgerConflict) -> JSONResponse:
        return JSONResponse({"detail": "request_conflict"}, status_code=409)

    @app.exception_handler(ValueError)
    async def unsafe_value(_request: Request, _error: ValueError) -> JSONResponse:
        return JSONResponse({"detail": "invalid_request"}, status_code=422)

    @app.exception_handler(KeyError)
    async def unknown(_request: Request, _error: KeyError) -> JSONResponse:
        return JSONResponse({"detail": "unknown_command"}, status_code=404)

    def scope(request: SessionRequest) -> None:
        if request.session_id != config.session_id:
            raise HTTPException(403, "session_forbidden")

    def response(record) -> CommandResponse:  # type: ignore[no-untyped-def]
        return CommandResponse(
            command_id=record.id,
            session_id=config.session_id,
            native_client_order_id=record.native_client_order_id,
            state=record.state.value,
            cumulative_filled=str(record.cumulative_filled),
        )

    errors: dict[int | str, dict[str, object]] = {
        401: {"model": PaperError},
        403: {"model": PaperError},
        422: {"model": PaperError},
        503: {"model": PaperError},
    }

    @app.get("/api/v1/trading/status", response_model=PaperStatus, dependencies=[Depends(observe)], responses=errors)
    async def status() -> PaperStatus:
        return await engine.status()

    @app.post("/api/v1/trading/start", response_model=PaperStatus, dependencies=[Depends(control)], responses=errors)
    async def start(request: SessionRequest) -> PaperStatus:
        scope(request)
        return await engine.start()

    @app.post("/api/v1/trading/stop", response_model=PaperStatus, dependencies=[Depends(control)], responses=errors)
    async def stop(request: SessionRequest) -> PaperStatus:
        scope(request)
        return await engine.stop()

    @app.post(
        "/api/v1/trading/commands",
        response_model=CommandResponse,
        status_code=202,
        dependencies=[Depends(control)],
        responses={**errors, 409: {"model": PaperError}},
    )
    async def submit(request: SubmitRequest) -> CommandResponse:
        scope(request)
        return response(await engine.submit(request))

    @app.get(
        "/api/v1/trading/commands/by-request/{request_id}",
        response_model=CommandResponse,
        dependencies=[Depends(observe)],
        responses={**errors, 404: {"model": PaperError}},
    )
    async def by_request(request_id: Opaque) -> CommandResponse:
        if len(request_id) > 128:
            raise HTTPException(404, "unknown_command")
        return response(await engine.get_by_request(request_id))

    @app.get(
        "/api/v1/trading/commands/{command_id}",
        response_model=CommandResponse,
        dependencies=[Depends(observe)],
        responses={**errors, 404: {"model": PaperError}},
    )
    async def command(command_id: Opaque) -> CommandResponse:
        if len(command_id) > 128:
            raise HTTPException(404, "unknown_command")
        return response(await engine.get(command_id))

    return app
