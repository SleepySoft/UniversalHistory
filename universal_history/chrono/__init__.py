"""
Time foundation for UniversalHistory.

This package exposes the JDN timestamp, bridges to Python/lunar calendars,
tick stepping for axis rendering, and adapters to the legacy History parser.
"""

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.chrono.lunar_date_bridge import LunarDateBridge
from universal_history.chrono.python_time_bridge import PythonTimeBridge
from universal_history.chrono.tick_stepper import TickLevel, TickStepper
from universal_history.chrono.history_time_adapter import (
    history_year_to_jdn_year,
    history_tick_to_jdn,
    history_record_time_range,
    history_record_time_text_to_jdn_list,
)
from universal_history.chrono.time_utils import (
    parse_time_text,
    format_jdn,
    jdn_to_qdatetime,
    qdatetime_to_jdn,
)

__all__ = [
    "JDNTimestamp",
    "LunarDateBridge",
    "PythonTimeBridge",
    "TickLevel",
    "TickStepper",
    "history_year_to_jdn_year",
    "history_tick_to_jdn",
    "history_record_time_range",
    "history_record_time_text_to_jdn_list",
    "parse_time_text",
    "format_jdn",
    "jdn_to_qdatetime",
    "qdatetime_to_jdn",
]
