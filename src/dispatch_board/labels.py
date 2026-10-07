"""Create labels displayed on a dispatch board."""

from datetime import datetime
from zoneinfo import ZoneInfo


def dispatch_label(dispatch_id: str, location_timezone: str) -> str:
    """Return a dated label for a dispatch at the named location."""
    local_day = datetime.now().astimezone().date()
    location_day = datetime.now(ZoneInfo(location_timezone)).date()

    if local_day == location_day:
        day_text = local_day.isoformat()
    else:
        day_text = local_day.isoformat()

    return f"{dispatch_id} | {day_text}"
