"""Run all local inputs and emit deterministic, credential-free JSON."""

from __future__ import annotations

import json

from callback import handle_callback
from fixtures import FIXED_NOW, SCENARIOS, scenario


def run() -> dict[str, object]:
    observations: dict[str, object] = {}
    for name in sorted(SCENARIOS):
        case = scenario(name)
        first = handle_callback(case["query"], case["session"], FIXED_NOW)
        results = [first.as_dict()]
        if name == "replayed":
            results.append(
                handle_callback(case["query"], case["session"], FIXED_NOW).as_dict()
            )
        observations[name] = results
    return observations


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
