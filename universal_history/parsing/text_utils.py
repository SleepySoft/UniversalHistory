"""
Small text/utility helpers needed by the .his parser.

Ported from History/Utility/history_public.py. Only the functions the parser
actually uses are kept. `traceback` is a plain stdlib import at call sites.

Fixes vs legacy:
- legacy defect #6: ``list_unique`` used ``set`` and scrambled tag order;
  it is now order-preserving.
"""

from __future__ import annotations

import io
import sys


def suppress_print(func):
    """Decorator: swallow stdout produced inside the wrapped function."""

    def wrapper(*args, **kwargs):
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            result = func(*args, **kwargs)
        finally:
            sys.stdout = original_stdout
        return result

    return wrapper


def str_to_int(text: str, default: int = 0) -> int:
    try:
        return int(text)
    except Exception:
        return default


def str_includes(text: str, includes: list) -> bool:
    for sub_str in includes:
        if sub_str in text:
            return True
    return False


def list_unique(list1: list) -> list:
    """Order-preserving de-duplication (legacy defect #6 fix)."""
    return list(dict.fromkeys(list1))
