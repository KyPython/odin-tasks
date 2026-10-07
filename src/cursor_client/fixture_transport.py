"""Deterministic transport backed by a JSON response transcript."""

import json
from pathlib import Path
from typing import Any


class ProtocolError(RuntimeError):
    """Raised when a request is absent from the fixture transcript."""


class FixtureTransport:
    """Replay ordered responses and validate the requested cursor."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = responses
        self._position = 0
        self.requested_cursors: list[str | None] = []

    @classmethod
    def from_path(cls, path: str | Path) -> "FixtureTransport":
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(document["responses"])

    def __call__(self, cursor: str | None) -> dict[str, Any]:
        self.requested_cursors.append(cursor)
        if self._position >= len(self._responses):
            raise ProtocolError(f"no fixture response for cursor {cursor!r}")

        exchange = self._responses[self._position]
        expected_cursor = exchange["request_cursor"]
        if cursor != expected_cursor:
            raise ProtocolError(
                f"expected cursor {expected_cursor!r}, received {cursor!r}"
            )

        self._position += 1
        return exchange["response"]
