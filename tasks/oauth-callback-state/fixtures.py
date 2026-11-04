"""Deterministic inputs for observing the starter callback."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

FIXED_NOW = 2_000_000_000
SYNTHETIC_CODE = "fixture-authorization-code"
EXPECTED_STATE = "fixture-state-alpha"

SCENARIOS: dict[str, dict[str, Any]] = {
    "valid": {
        "query": {"code": SYNTHETIC_CODE, "state": EXPECTED_STATE},
        "session": {
            "oauth_request": {
                "state": EXPECTED_STATE,
                "expires_at": FIXED_NOW + 270,
                "return_to": "/dashboard",
            }
        },
    },
    "missing": {
        "query": {"code": SYNTHETIC_CODE},
        "session": {
            "oauth_request": {
                "state": EXPECTED_STATE,
                "expires_at": FIXED_NOW + 270,
                "return_to": "/dashboard",
            }
        },
    },
    "mismatched": {
        "query": {"code": SYNTHETIC_CODE, "state": "fixture-state-beta"},
        "session": {
            "oauth_request": {
                "state": EXPECTED_STATE,
                "expires_at": FIXED_NOW + 270,
                "return_to": "/dashboard",
            }
        },
    },
    "expired": {
        "query": {"code": SYNTHETIC_CODE, "state": EXPECTED_STATE},
        "session": {
            "oauth_request": {
                "state": EXPECTED_STATE,
                "expires_at": FIXED_NOW - 1,
                "return_to": "/dashboard",
            }
        },
    },
    "replayed": {
        "query": {"code": SYNTHETIC_CODE, "state": EXPECTED_STATE},
        "session": {
            "oauth_request": {
                "state": EXPECTED_STATE,
                "expires_at": FIXED_NOW + 270,
                "return_to": "/dashboard",
            }
        },
    },
}


def scenario(name: str) -> dict[str, Any]:
    """Return an isolated copy so one run cannot contaminate another."""
    return deepcopy(SCENARIOS[name])
