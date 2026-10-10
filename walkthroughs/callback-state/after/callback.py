"""Synthetic OAuth callback boundary used by the bootcamp exercise."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hmac import compare_digest
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
    """Validate this local callback before consuming its pending request."""
    if "code" not in query:
        return CallbackResult(status="error", category="missing_code")

    state = query.get("state")
    if not isinstance(state, str) or not state:
        return CallbackResult(status="error", category="missing_state")

    pending = session.get("oauth_request")
    if not isinstance(pending, dict):
        used_state = session.get("oauth_used_state")
        if isinstance(used_state, str) and compare_digest(
            state.encode("utf-8"), used_state.encode("utf-8")
        ):
            return CallbackResult(status="error", category="state_replayed")
        return CallbackResult(status="error", category="state_mismatch")

    expected_state = pending.get("state")
    if not isinstance(expected_state, str) or not expected_state or not compare_digest(
        state.encode("utf-8"), expected_state.encode("utf-8")
    ):
        return CallbackResult(status="error", category="state_mismatch")

    expires_at = pending.get("expires_at")
    if type(expires_at) is not int or now >= expires_at:
        return CallbackResult(status="error", category="state_expired")

    redirect_to = pending.get("return_to", "/")
    session.pop("oauth_request")
    session["oauth_used_state"] = expected_state
    return CallbackResult(status="ok", redirect_to=redirect_to)
