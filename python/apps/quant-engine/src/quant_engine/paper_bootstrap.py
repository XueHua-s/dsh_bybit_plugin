"""Explicit credential-free synthetic service; migrations are a separate operator action."""

import argparse
import ipaddress
import secrets
import socket
from pathlib import Path

import uvicorn

from .bootstrap import loopback_host
from .paper_api import create_paper_app
from .paper_capability import PaperCapabilityBroker
from .paper_config import Capability, capability_from_fd, synthetic_config
from .synthetic_fixture_registry import builtin_synthetic_fixture_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Explicit synthetic internal-paper service (no exchange)")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--session", required=True)
    provisioning = parser.add_mutually_exclusive_group(required=True)
    provisioning.add_argument("--capability-fd", type=int)
    provisioning.add_argument("--capability-socket")
    parser.add_argument("--host", type=loopback_host, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("invalid_port")
    try:
        config = synthetic_config(args.database, args.session)
        # The deployed paper process owns one immutable, credential-free bundle.
        # No fixture file, network feed, or model input is accepted at startup.
        fixture_registry = builtin_synthetic_fixture_registry(config)
        if args.capability_socket is not None:
            host = str(ipaddress.ip_address(args.host))
            origin_host = f"[{host}]" if ":" in host else host
            capability = Capability(secrets.token_urlsafe(48).encode("ascii"), args.session)
            broker = PaperCapabilityBroker(args.capability_socket, capability, f"http://{origin_host}:{args.port}")
            # Reserve the endpoint before admission/broker publication; never probe then rebind.
            with socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.bind((host, args.port))
                listener.listen(128)
                listener.setblocking(False)
                app = create_paper_app(config, capability, broker=broker, fixture_registry=fixture_registry)
                server = uvicorn.Server(
                    uvicorn.Config(app, access_log=False, log_level="critical", timeout_graceful_shutdown=10)
                )
                server.run(sockets=[listener])
                if not server.started:
                    raise ValueError("private_capability_unavailable")
            return
        capability = capability_from_fd(args.capability_fd, args.session)
        app = create_paper_app(config, capability, fixture_registry=fixture_registry)
    except (ValueError, OSError):
        parser.error("private_capability_or_paper_configuration_unavailable")
    uvicorn.run(
        app, host=args.host, port=args.port, access_log=False, log_level="critical", timeout_graceful_shutdown=10
    )


if __name__ == "__main__":
    main()
