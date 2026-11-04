"""Synthetic OAuth callback boundary used by the bootcamp exercise."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, MutableMapping


@dataclass(frozen=True)
class CallbackResult:
    status: str
    category: str | None = None
    redirect_to: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        """Return a JSON-friendly response without callback credentials."""
        return asdict(self)


def handle_callback(
    query: dict[str, str],
    session: MutableMapping[str, Any],
    now: int,
) -> CallbackResult:
    """Handle a synthetic authorization response.

    This starter contains a deliberately incomplete validation path for the
    learner to investigate. ``now`` is injected to keep local runs repeatable.
    """
    del now

    if "code" not in query:
        return CallbackResult(status="error", category="missing_code")

    pending = session.pop("oauth_request", None)
    redirect_to = pending.get("return_to", "/") if pending else "/"
    return CallbackResult(status="ok", redirect_to=redirect_to)
