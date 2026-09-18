"""
UI-oriented time utilities built on top of JDNTimestamp.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from PyQt6.QtCore import QDateTime

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.chrono.python_time_bridge import PythonTimeBridge
from universal_history.chrono.history_time_adapter import history_record_time_text_to_jdn_list


# Standard machine-friendly date/time, e.g.:
#   2020-01-01 | 2020-01-01 15:30:00 | 3000-01-01 BC | -3000-06-15
# The legacy natural-language parser does NOT understand this format, so it
# must be handled before falling back to it (round-trip with format_jdn).
_ISO_RE = re.compile(
    r"^\s*(?P<year>-?\d{1,6})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"
    r"(?:[ T](?P<hour>\d{1,2}):(?P<minute>\d{1,2})(?::(?P<second>\d{1,2}))?)?"
    r"\s*(?P<era>BC|AD)?\s*$",
    re.IGNORECASE,
)


def _parse_iso(text: str) -> Optional[JDNTimestamp]:
    """Parse the standard `YYYY-MM-DD[ HH:MM[:SS]][ AD|BC]` format.

    Returns None when the text is not in this format (caller then falls back
    to the natural-language parser). Negative years are already astronomical;
    `BC` maps `N BC` to astronomical year `-(N-1)`.
    """
    m = _ISO_RE.match(text)
    if not m:
        return None
    year = int(m.group("year"))
    era = (m.group("era") or "").upper()
    if era == "BC" and year > 0:
        year = -(year - 1)
    month = int(m.group("month"))
    day = int(m.group("day"))
    hour = int(m.group("hour") or 0)
    minute = int(m.group("minute") or 0)
    second = int(m.group("second") or 0)
    try:
        return JDNTimestamp.from_ymd_hms(year, month, day, hour, minute, second)
    except (ValueError, OverflowError):
        return None


def parse_time_text(text: str) -> Tuple[Optional[JDNTimestamp], Optional[JDNTimestamp], List[str]]:
    """
    Parse time text and return (since, until, display_strings).

    Standard `YYYY-MM-DD[ HH:MM[:SS]][ AD|BC]` input is handled directly;
    anything else falls back to the legacy natural-language parser.
    If the text contains multiple times, since = min, until = max.
    If parsing fails, returns (None, None, []).
    """
    text = text.strip()
    if not text:
        return None, None, []

    iso = _parse_iso(text)
    if iso is not None:
        return iso, iso, [format_jdn(iso)]

    try:
        timestamps = history_record_time_text_to_jdn_list(text)
    except Exception:
        return None, None, []

    if not timestamps:
        return None, None, []

    since = min(timestamps)
    until = max(timestamps)
    displays = [format_jdn(ts) for ts in timestamps]
    return since, until, displays


def format_jdn(ts: Optional[JDNTimestamp]) -> str:
    """User-facing string for a JDNTimestamp.

    Always carries a BC/AD era suffix. The HH:MM:SS part is omitted when the
    time is exactly midnight (date-only display); the output stays round-trip
    parseable by `parse_time_text` either way.
    """
    if ts is None:
        return ""
    y, m, d, h, mn, s, _ = ts.to_gregorian()
    if y <= 0:
        display_year = -(y - 1)
        era = "BC"
    else:
        display_year = y
        era = "AD"
    date_part = f"{display_year}-{m:02d}-{d:02d}"
    if h == 0 and mn == 0 and s == 0:
        return f"{date_part} {era}"
    return f"{date_part} {h:02d}:{mn:02d}:{s:02d} {era}"


def jdn_to_qdatetime(ts: JDNTimestamp) -> Optional[QDateTime]:
    """Convert a JDNTimestamp to QDateTime if it falls in Python datetime range."""
    try:
        dt = PythonTimeBridge.to_datetime(ts)
    except (OverflowError, ValueError):
        return None
    return QDateTime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def qdatetime_to_jdn(qdt: QDateTime) -> JDNTimestamp:
    """Convert a QDateTime to JDNTimestamp."""
    from datetime import timezone
    dt = qdt.toPyDateTime()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return PythonTimeBridge.from_datetime(dt)
