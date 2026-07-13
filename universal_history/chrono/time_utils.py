"""
UI-oriented time utilities built on top of JDNTimestamp.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PyQt6.QtCore import QDateTime

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.chrono.python_time_bridge import PythonTimeBridge
from universal_history.chrono.history_time_adapter import history_record_time_text_to_jdn_list


def parse_time_text(text: str) -> Tuple[Optional[JDNTimestamp], Optional[JDNTimestamp], List[str]]:
    """
    Parse natural-language time text and return (since, until, display_strings).

    If the text contains multiple times, since = min, until = max.
    If parsing fails, returns (None, None, []).
    """
    text = text.strip()
    if not text:
        return None, None, []

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


def format_jdn(ts: JDNTimestamp) -> str:
    """User-facing string for a JDNTimestamp."""
    if ts is None:
        return ""
    y, m, d, h, mn, s, _ = ts.to_gregorian()
    if y <= 0:
        display_year = -(y - 1)
        era = "BC"
    else:
        display_year = y
        era = "AD"
    return f"{display_year}-{m:02d}-{d:02d} {h:02d}:{mn:02d}:{s:02d} {era}"


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
