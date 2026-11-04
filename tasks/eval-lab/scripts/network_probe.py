"""Synthetic numeric-address connection control; no provider or application data."""

from __future__ import annotations

import argparse
import errno
import json
import socket

PORT = 49175


def probe(host: str, *, blocked: bool = False) -> dict:
    try:
        with socket.create_connection((host, PORT), timeout=3) as connection:
            connection.sendall(b"synthetic-network-control")
            received = connection.recv(16)
    except OSError as exc:
        denied = exc.errno in (
            errno.ENETUNREACH,
            errno.EHOSTUNREACH,
            errno.EPERM,
            errno.EACCES,
        )
        if not blocked or not denied:
            raise RuntimeError(
                f"Network control did not produce the required evidence: errno={exc.errno}"
            ) from None
        return {"host": host, "port": PORT, "blocked": True, "errno": exc.errno}
    if blocked or received != b"control-ok":
        raise RuntimeError(
            "Network control unexpectedly connected or returned the wrong protocol"
        )
    return {"host": host, "port": PORT, "connected": True}


def serve() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("0.0.0.0", PORT))
        server.listen(8)
        while True:
            connection, _ = server.accept()
            with connection:
                connection.settimeout(3)
                if connection.recv(128) == b"synthetic-network-control":
                    connection.sendall(b"control-ok")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("serve", "connect", "blocked"))
    parser.add_argument("--host")
    args = parser.parse_args()
    if args.mode == "serve":
        serve()
    else:
        if not args.host:
            parser.error("--host is required")
        print(json.dumps(probe(args.host, blocked=args.mode == "blocked")))
