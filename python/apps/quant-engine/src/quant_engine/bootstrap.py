"""Safe local CLI and deterministic offline Pydantic/OpenAPI export."""

from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path

import uvicorn

from .api import create_app, validate_symbols


def loopback_host(value: str) -> str:
    try:
        if ipaddress.ip_address(value).is_loopback:
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("only loopback IP addresses are allowed; remote authentication is not implemented")


def main() -> None:
    parser = argparse.ArgumentParser(description="Public linear Testnet observation service; no trading")
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--host", type=loopback_host, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--stale-after", type=float, default=30.0)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        symbols = validate_symbols(tuple(args.symbols))
        app = create_app(symbols, stale_after=args.stale_after)
    except ValueError as error:
        parser.error(str(error))
    uvicorn.run(app, host=args.host, port=args.port)


def export_openapi() -> None:
    """Generate schema without entering ASGI lifespan or opening network sockets."""
    parser = argparse.ArgumentParser(description="Export deterministic engine OpenAPI without starting ingestion")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--paper", action="store_true", help="Export the separate optional internal-paper application")
    args = parser.parse_args()
    if args.paper:
        from .paper_api import create_paper_app
        from .paper_config import Capability, synthetic_config

        app = create_paper_app(
            synthetic_config(Path("/nonexistent/schema-only"), "schema-session"),
            Capability(b"x" * 32, "schema-session"),
        )
    else:
        app = create_app(("BTCUSDT",))
    serialized = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text() != serialized:
            parser.exit(1, "OpenAPI schema is out of date\n")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)


if __name__ == "__main__":
    main()
