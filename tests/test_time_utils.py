"""Tests for time_utils (ISO fast path, format_jdn) and chrono fixes."""
import unittest
import warnings
from datetime import datetime

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.chrono.python_time_bridge import PythonTimeBridge
from universal_history.chrono.tick_stepper import TickStepper
from universal_history.chrono.time_utils import format_jdn, parse_time_text


class TestIsoParsing(unittest.TestCase):
    """Standard YYYY-MM-DD input must be parsed directly, not by the legacy
    natural-language parser (which mangles ISO text)."""

    def test_plain_iso_date(self):
        since, until, _ = parse_time_text("2020-01-01")
        self.assertEqual((since.year, since.month, since.day), (2020, 1, 1))
        self.assertEqual(since, until)

    def test_iso_datetime(self):
        since, _, _ = parse_time_text("2020-06-15 08:30:05")
        self.assertEqual(
            (since.year, since.month, since.day, since.hour, since.minute, since.second),
            (2020, 6, 15, 8, 30, 5),
        )

    def test_iso_bc_suffix_maps_to_astronomical(self):
        since, _, _ = parse_time_text("3000-01-01 BC")
        # 3000 BC -> astronomical year -2999
        self.assertEqual(since.year, -2999)

    def test_iso_negative_year_is_astronomical(self):
        since, _, _ = parse_time_text("-2999-01-01")
        self.assertEqual(since.year, -2999)

    def test_format_roundtrip(self):
        for text in ("2020-01-01", "2020-06-15 08:30:05", "3000-01-01 BC"):
            since, _, displays = parse_time_text(text)
            again, _, _ = parse_time_text(displays[0])
            self.assertEqual(since, again, text)

    def test_natural_language_still_works(self):
        since, _, _ = parse_time_text("BC3000")
        self.assertIsNotNone(since)
        self.assertEqual(since.year, -2999)


class TestFormatJdn(unittest.TestCase):

    def test_none_returns_empty(self):
        self.assertEqual(format_jdn(None), "")

    def test_midnight_omits_time(self):
        ts = JDNTimestamp.from_ymd_hms(2020, 1, 1, 0, 0, 0)
        self.assertEqual(format_jdn(ts), "2020-01-01 AD")

    def test_bc_suffix(self):
        ts = JDNTimestamp.from_ymd_hms(-2999, 3, 2, 0, 0, 0)
        self.assertEqual(format_jdn(ts), "3000-03-02 BC")

    def test_with_time(self):
        ts = JDNTimestamp.from_ymd_hms(2020, 1, 1, 8, 30, 5)
        self.assertEqual(format_jdn(ts), "2020-01-01 08:30:05 AD")


class TestLeapYearBce(unittest.TestCase):
    """Astronomical-year leap semantics (spec/how/98-known-issues.md #10)."""

    def _leap(self, year: int) -> bool:
        return JDNTimestamp.from_year(year).is_leap_year()

    def test_astronomical_leap_years(self):
        self.assertTrue(self._leap(0))      # 1 BC
        self.assertTrue(self._leap(-4))     # 5 BC
        self.assertTrue(self._leap(-400))   # 401 BC
        self.assertTrue(self._leap(2000))
        self.assertTrue(self._leap(2020))

    def test_non_leap_years(self):
        self.assertFalse(self._leap(-100))  # 101 BC (century, not /400)
        self.assertFalse(self._leap(1900))
        self.assertFalse(self._leap(2023))
        self.assertFalse(self._leap(-1))    # 2 BC


class TestWeekSnap(unittest.TestCase):
    """Week level snaps to ISO Monday 00:00 (#11)."""

    def _week_level(self):
        return next(lv for lv in TickStepper.LEVELS if lv.id == "week_1")

    def test_snap_to_monday(self):
        # 2000-01-01 was a Saturday.
        saturday = JDNTimestamp.from_ymd(2000, 1, 1)
        snapped = TickStepper.snap_to_grid(saturday, self._week_level())
        self.assertEqual((snapped.year, snapped.month, snapped.day), (1999, 12, 27))
        self.assertEqual(snapped.weekday, 1)
        self.assertEqual((snapped.hour, snapped.minute, snapped.second), (0, 0, 0))

    def test_monday_snaps_to_itself(self):
        monday = JDNTimestamp.from_ymd_hms(2024, 9, 16, 10, 0, 0)  # Monday
        snapped = TickStepper.snap_to_grid(monday, self._week_level())
        self.assertEqual((snapped.year, snapped.month, snapped.day), (2024, 9, 16))
        self.assertEqual((snapped.hour, snapped.minute), (0, 0))


class TestNaiveDatetimeWarning(unittest.TestCase):
    """Naive datetime assumed UTC must warn (#14)."""

    def test_naive_warns(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            PythonTimeBridge.from_datetime(datetime(2020, 1, 1))
        self.assertTrue(any("UTC" in str(w.message) for w in caught))

    def test_aware_no_warning(self):
        from datetime import timezone
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            PythonTimeBridge.from_datetime(datetime(2020, 1, 1, tzinfo=timezone.utc))
        self.assertFalse(caught)


if __name__ == "__main__":
    unittest.main()
