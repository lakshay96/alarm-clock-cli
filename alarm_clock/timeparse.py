from __future__ import annotations

import re
from datetime import time

_RE_24H = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
_RE_12H = re.compile(r"^(0?[1-9]|1[0-2]):([0-5]\d)\s*([AaPp][Mm])$")


class TimeParseError(ValueError):
    pass


def parse_time(raw: str) -> time:
    """Parse a user-supplied time string in 24h or 12h format.

    Accepts:
        "HH:MM"     — 24-hour, e.g. "07:05", "23:59"
        "h:MM AM/PM" — 12-hour, e.g. "7:05 AM", "11:59 pm"
    """
    if not isinstance(raw, str) or not raw.strip():
        raise TimeParseError("Time is empty. Use 'HH:MM' (24h) or 'h:MM AM/PM' (12h).")

    s = raw.strip()

    m = _RE_24H.match(s)
    if m:
        return time(int(m.group(1)), int(m.group(2)))

    m = _RE_12H.match(s)
    if m:
        hour = int(m.group(1)) % 12
        if m.group(3).lower() == "pm":
            hour += 12
        return time(hour, int(m.group(2)))

    raise TimeParseError(
        f"Invalid time: {raw!r}. Use 'HH:MM' (24h) or 'h:MM AM/PM' (12h)."
    )


def format_time(t: time) -> str:
    return t.strftime("%H:%M")
