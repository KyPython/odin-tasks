"""Command-line fixture runner for the synthetic client."""

import json
import sys

from .aggregator import collect_records
from .fixture_transport import FixtureTransport, ProtocolError


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print("usage: python -m cursor_client.cli FIXTURE.json", file=sys.stderr)
        return 2

    transport = FixtureTransport.from_path(arguments[0])
    try:
        records = collect_records(transport)
    except (KeyError, ProtocolError) as error:
        print(f"pagination failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(records, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
