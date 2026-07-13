"""
Adapter between History's legacy time representation and UniversalHistory's
JDNTimestamp.

History stores time internally as a custom "TICK" (seconds since 0001-01-01
00:00:00), but it is only produced during natural-language parsing at load
time. No data is persisted as TICK.

This module provides a pragmatic bridge: take the parsed TICK, convert it
back to (year, month, day, ...), then build a JDNTimestamp. It does not need
rigorous astronomical equivalence; it only needs to preserve the user-facing
calendar date produced by HistoryTime's parser.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Tuple

# Make the old History project importable so we can reuse its parser.
_HISTORY_ROOT = Path(__file__).resolve().parents[3] / "History"
_HISTORY_ROOT = _HISTORY_ROOT.resolve()
if str(_HISTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_HISTORY_ROOT))

from Utility import HistoryTime  # noqa: E402
from universal_history.chrono.jdn_timestamp import JDNTimestamp  # noqa: E402


def history_year_to_jdn_year(history_year: int) -> int:
    """
    Map History's year numbering (no year 0; -1 = 1 BC) to JDNTimestamp's
    astronomical numbering (0 = 1 BC).
    """
    return history_year + 1 if history_year < 0 else history_year


def history_tick_to_jdn(tick: int) -> JDNTimestamp:
    """
    Convert a History TICK (seconds) to JDNTimestamp.

    The conversion goes through calendar components to avoid epoch-mismatch
    errors between the two systems.
    """
    year, month, day, hour, minute, second = HistoryTime.tick_to_date_time_data(tick)
    jdn_year = history_year_to_jdn_year(year)
    return JDNTimestamp.from_ymd_hms(jdn_year, month, day, hour, minute, second)


def history_record_time_range(record) -> Tuple[Optional[JDNTimestamp], Optional[JDNTimestamp]]:
    """
    Extract since/until from a History HistoryRecord as JDNTimestamps.

    Returns (None, None) when the record has no parseable time text.
    """
    # HistoryRecord stores 0.0 for "no time parsed". Use the original time
    # label list to distinguish "no time" from a genuine AD 1 date.
    if not record.time():
        return None, None

    since = record.since()
    until = record.until()

    # Guard against the degenerate case where the parser produced no ticks.
    if since == 0 and until == 0:
        return None, None

    return history_tick_to_jdn(since), history_tick_to_jdn(until)


def history_record_time_text_to_jdn_list(time_text: str) -> list:
    """
    Parse natural-language time text exactly as History does and return a list
    of JDNTimestamps.
    """
    ticks = HistoryTime.time_text_to_ticks(time_text)
    return [history_tick_to_jdn(t) for t in ticks]
