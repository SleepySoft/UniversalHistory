"""
.his parsing package.

Native port of the legacy History repository's parser (core.py,
Utility/HistoryTime.py, Utility/to_arab.py) so UniversalHistory no longer
depends on the sibling History codebase via sys.path injection.

Behaviour is byte-for-byte compatible with the legacy parser except for the
documented bug fixes listed in each module's docstring (legacy defects
#1-#7, #9 of docs/history_legacy_spec/how/98-known-defects.md).
"""

from .token_parser import (
    TokenParser,
    LABEL_TAG_TOKENS,
    LABEL_TAG_WRAPPERS,
    LABEL_TAG_ESCAPES_SYMBOLS,
)
from .label_tag import LabelTagParser, LabelTag
from .history_record import HistoryRecord, HistoryRecordLoader
from . import history_time

__all__ = [
    "TokenParser",
    "LABEL_TAG_TOKENS",
    "LABEL_TAG_WRAPPERS",
    "LABEL_TAG_ESCAPES_SYMBOLS",
    "LabelTagParser",
    "LabelTag",
    "HistoryRecord",
    "HistoryRecordLoader",
    "history_time",
]
