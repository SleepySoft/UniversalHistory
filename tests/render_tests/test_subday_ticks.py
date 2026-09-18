"""
Regression tests for sub-day tick levels (hour/minute/second, legacy
sub-scale restoration) and the three-tier display degradation
(core_design.md §5.2 — deep-time BP labels).
"""

import unittest

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.chrono.tick_stepper import TickStepper
from universal_history.render.painter import _format_tick_label


def _level(level_id):
    return next(l for l in TickStepper.LEVELS if l.id == level_id)


class TestSubDayLevels(unittest.TestCase):

    def test_levels_registered_fine_to_coarse(self):
        ids = [l.id for l in TickStepper.LEVELS]
        for lid in ("second_10", "minute_1", "minute_10", "hour_1", "hour_6"):
            self.assertIn(lid, ids)
        # Sub-day levels sit before day_1 (fine -> coarse ordering).
        self.assertLess(ids.index("hour_6"), ids.index("day_1"))

    def test_hour_snap_floors_to_hour(self):
        snapped = TickStepper.snap_to_grid(
            JDNTimestamp.from_ymd_hms(2020, 5, 4, 13, 47, 22), _level("hour_1")
        )
        self.assertEqual(snapped.to_gregorian()[:6], (2020, 5, 4, 13, 0, 0))

    def test_hour6_snaps_to_six_hour_blocks(self):
        snapped = TickStepper.snap_to_grid(
            JDNTimestamp.from_ymd_hms(2020, 5, 4, 13, 47, 22), _level("hour_6")
        )
        self.assertEqual(snapped.to_gregorian()[:6], (2020, 5, 4, 12, 0, 0))

    def test_minute10_snap_and_next(self):
        level = _level("minute_10")
        snapped = TickStepper.snap_to_grid(
            JDNTimestamp.from_ymd_hms(2020, 5, 4, 13, 47, 22), level
        )
        self.assertEqual(snapped.to_gregorian()[:6], (2020, 5, 4, 13, 40, 0))
        nxt = TickStepper.get_next_tick(snapped, level)
        self.assertEqual(nxt.to_gregorian()[:6], (2020, 5, 4, 13, 50, 0))

    def test_hour_next_crosses_midnight(self):
        level = _level("hour_6")
        snapped = TickStepper.snap_to_grid(
            JDNTimestamp.from_ymd_hms(2020, 5, 4, 22, 5, 0), level
        )
        self.assertEqual(snapped.to_gregorian()[:6], (2020, 5, 4, 18, 0, 0))
        nxt = TickStepper.get_next_tick(snapped, level)
        self.assertEqual(nxt.to_gregorian()[:6], (2020, 5, 5, 0, 0, 0))


class TestTieredTickLabels(unittest.TestCase):

    def test_hour_label(self):
        label = _format_tick_label(
            JDNTimestamp.from_ymd_hms(2020, 5, 4, 13, 0, 0), _level("hour_1")
        )
        self.assertEqual(label, "13:00")

    def test_minute_label(self):
        label = _format_tick_label(
            JDNTimestamp.from_ymd_hms(2020, 5, 4, 13, 40, 0), _level("minute_10")
        )
        self.assertEqual(label, "13:40")

    def test_midnight_shows_date_context(self):
        label = _format_tick_label(
            JDNTimestamp.from_ymd_hms(2020, 5, 4, 0, 0, 0), _level("hour_6")
        )
        self.assertEqual(label, "2020-05-04")

    def test_modern_years_keep_calendar_labels(self):
        label = _format_tick_label(
            JDNTimestamp.from_ymd(2020, 1, 1), _level("year_1")
        )
        self.assertEqual(label, "2020")

    def test_prehistoric_year_keeps_plain_year(self):
        # Tier 2: before written history but above the BP threshold.
        label = _format_tick_label(
            JDNTimestamp.from_ymd(-9999, 1, 1), _level("year_1k")
        )
        self.assertEqual(label, "10000 BC")

    def test_deep_time_switches_to_bp(self):
        # Tier 3: astronomical year < -10000 -> BP (epoch 1950).
        label = _format_tick_label(
            JDNTimestamp.from_ymd(-10050, 1, 1), _level("year_1k")
        )
        self.assertEqual(label, "12 ka BP")

    def test_deep_time_ma_and_ga_bp(self):
        label = _format_tick_label(
            JDNTimestamp.from_ymd(-64_998_050, 1, 1), _level("year_100000000")
        )
        self.assertEqual(label, "65 Ma BP")
        label = _format_tick_label(
            JDNTimestamp.from_ymd(-999_998_050, 1, 1), _level("year_1000000000")
        )
        self.assertEqual(label, "1 Ga BP")


if __name__ == "__main__":
    unittest.main()
