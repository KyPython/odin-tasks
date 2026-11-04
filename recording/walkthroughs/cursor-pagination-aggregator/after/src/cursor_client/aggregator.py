"""Aggregate records exposed by a cursor-paginated transport."""

from collections.abc import Callable
from typing import Any

Record = dict[str, Any]
Page = dict[str, Any]
Transport = Callable[[str | None], Page]


def collect_records(transport: Transport) -> list[Record]:
    """Visit each cursor once and retain each record's first server position."""
    records: list[Record] = []
    cursor: str | None = None
    requested_cursors: set[str | None] = set()
    record_ids: set[str] = set()

    while cursor not in requested_cursors:
        requested_cursors.add(cursor)
        page = transport(cursor)
        for record in page["records"]:
            record_id = record["id"]
            if record_id not in record_ids:
                record_ids.add(record_id)
                records.append(record)

        cursor = page.get("next_cursor")
        if cursor is None:
            break

    return records
