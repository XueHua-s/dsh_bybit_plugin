"""Explicit credential-free synthetic service; migrations are a separate operator action."""

import argparse
from pathlib import Path

import uvicorn

from .bootstrap import loopback_host
from .paper_api import create_paper_app
from .paper_config import capability_from_fd, synthetic_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Explicit synthetic internal-paper service (no exchange)")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--capability-fd", type=int, required=True)
    parser.add_argument("--host", type=loopback_host, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("invalid_port")
    try:
        capability = capability_from_fd(args.capability_fd, args.session)
        config = synthetic_config(args.database, args.session)
        app = create_paper_app(config, capability)
    except (ValueError, OSError):
        parser.error("private_capability_or_paper_configuration_unavailable")
    uvicorn.run(
        app, host=args.host, port=args.port, access_log=False, log_level="critical", timeout_graceful_shutdown=10
    )


if __name__ == "__main__":
    main()
