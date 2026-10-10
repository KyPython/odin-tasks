"""Create labels displayed on a dispatch board."""

from collections.abc import Callable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


Clock = Callable[[], datetime]


def dispatch_label(
    dispatch_id: str,
    location_timezone: str,
    *,
    clock: Clock | None = None,
) -> str:
    """Use one timezone-aware clock reading and the dispatch location's date."""
    instant = datetime.now(timezone.utc) if clock is None else clock()
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("clock must return a timezone-aware datetime")

    location_day = instant.astimezone(ZoneInfo(location_timezone)).date()
    return f"{dispatch_id} | {location_day.isoformat()}"
