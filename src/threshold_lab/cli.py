"""Command-line interface for producing a threshold evaluation report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluation import build_report
from .io import load_observations, load_policy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(load_observations(args.observations), load_policy(args.policy))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
