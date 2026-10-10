"""Aggregate records exposed by a cursor-paginated transport."""

from collections.abc import Callable
from typing import Any

Record = dict[str, Any]
Page = dict[str, Any]
Transport = Callable[[str | None], Page]


def collect_records(transport: Transport) -> list[Record]:
    """Fetch pages and return their records in response order."""
    records: list[Record] = []
    cursor: str | None = None

    while True:
        page = transport(cursor)
        page_records = page["records"]
        records.extend(page_records)

        if not page_records:
            break

        cursor = page.get("next_cursor")
        if cursor is None:
            break

    return records
