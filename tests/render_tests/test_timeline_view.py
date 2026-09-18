import unittest

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render import TimelineView


class TestTimelineView(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def test_can_instantiate_and_add_thread(self):
        view = TimelineView()
        view.resize(800, 600)

        events = [
            EventIndex("a", "test", JDNTimestamp.from_ymd(2000, 1, 1),
                       JDNTimestamp.from_ymd(2000, 1, 1), "Point event"),
            EventIndex("b", "test", JDNTimestamp.from_ymd(2000, 3, 1),
                       JDNTimestamp.from_ymd(2000, 9, 1), "Period event"),
        ]
        thread = view.add_thread(events, align="right")
        self.assertIsNotNone(thread)
        self.assertEqual(len(thread.items), 2)

        # Toggle orientation should not crash.
        view.toggle_orientation()
        self.assertTrue(view.coord.is_vertical)

        # Cleanup to avoid leaking widgets in batch tests.
        view.deleteLater()

    def test_axis_offset_changes_side_budgets(self):
        view = TimelineView()
        view.resize(800, 600)

        events = [
            EventIndex("a", "test", JDNTimestamp.from_ymd(2000, 1, 1),
                       JDNTimestamp.from_ymd(2000, 1, 1), "Point"),
        ]
        left_thread = view.add_thread(events, align="left")
        right_thread = view.add_thread(events, align="right")

        # Default offset 0.5 -> sides should be roughly equal.
        default_left_width = abs(left_thread.y1 - left_thread.y0)
        default_right_width = abs(right_thread.y1 - right_thread.y0)
        self.assertAlmostEqual(default_left_width, default_right_width, delta=30)

        # Push axis to the left -> right side gets more space.
        view.coord.axis_offset = 0.2
        view._arrange_threads()
        self.assertGreater(
            abs(right_thread.y1 - right_thread.y0), default_right_width
        )
        self.assertLess(
            abs(left_thread.y1 - left_thread.y0), default_left_width
        )

        view.deleteLater()

    def test_set_thread_share_renormalizes_side(self):
        view = TimelineView()
        view.resize(800, 600)
        events = [
            EventIndex("a", "test", JDNTimestamp.from_ymd(2000, 1, 1),
                       JDNTimestamp.from_ymd(2000, 1, 1), "A"),
        ]
        t1 = view.add_thread(events, align="right")
        t2 = view.add_thread(events, align="right")

        view.set_thread_share(t1, 0.75)
        self.assertAlmostEqual(t1.share + t2.share, 1.0, delta=1e-9)
        self.assertAlmostEqual(t1.share, 0.75, delta=1e-9)

        # Geometry should reflect the new shares.
        w1 = abs(t1.y1 - t1.y0)
        w2 = abs(t2.y1 - t2.y0)
        self.assertAlmostEqual(w1 / (w1 + w2), 0.75, delta=0.01)

        view.deleteLater()

    def test_automatic_palette_colors(self):
        view = TimelineView()
        view.resize(800, 600)
        events = [
            EventIndex("a", "test", JDNTimestamp.from_ymd(2000, 1, 1),
                       JDNTimestamp.from_ymd(2000, 1, 1), "Point"),
        ]
        t1 = view.add_thread(events, align="right")
        t2 = view.add_thread(events, align="left")
        self.assertIsNotNone(t1.track_color)
        self.assertIsNotNone(t2.track_color)
        self.assertNotEqual(t1.track_color.name(), t2.track_color.name())

        view.deleteLater()

    def test_vertical_orientation_keeps_right_thread_on_right(self):
        from PyQt6.QtCore import QPointF

        view = TimelineView()
        view.resize(800, 600)
        events = [
            EventIndex("r", "test", JDNTimestamp.from_ymd(2000, 1, 1),
                       JDNTimestamp.from_ymd(2000, 1, 1), "Right"),
        ]
        view.add_thread(events, align="right")
        view.coord.is_vertical = True
        view._arrange_threads()

        axis_center = view.coord.axis_screen_center()
        # The right thread should appear to the right of the vertical axis.
        mid_y = (view.right_threads()[0].y0 + view.right_threads()[0].y1) / 2
        screen_pos = view.coord.logical_to_screen(QPointF(0, mid_y))
        self.assertGreater(screen_pos.x(), axis_center)

        view.deleteLater()

    def test_thread_shares_sum_to_one(self):
        view = TimelineView()
        view.resize(800, 600)
        events = [
            EventIndex("a", "test", JDNTimestamp.from_ymd(2000, 1, 1),
                       JDNTimestamp.from_ymd(2000, 1, 1), "A"),
        ]
        t1 = view.add_thread(events, align="right")
        t2 = view.add_thread(events, align="right")

        self.assertAlmostEqual(t1.share + t2.share, 1.0, delta=1e-9)
        self.assertAlmostEqual(t1.share, 0.5, delta=1e-9)

        view.deleteLater()

    def test_refresh_source_skips_empty_source(self):
        view = TimelineView()
        view.resize(800, 600)
        # Adding an empty-source thread should not crash refresh_source("").
        view.add_thread([], align="right", source="")
        view.refresh_source("")  # should be a no-op
        self.assertEqual(len(view.right_threads()), 1)
        view.deleteLater()

    def test_fit_to_sources_all_none_time_does_not_crash(self):
        """Regression #23: datasets where every event lacks time must not
        raise ValueError."""
        view = TimelineView()
        view.resize(800, 600)
        events = [
            EventIndex("a", "test", None, None, "No time"),
            EventIndex("b", "test", None, None, "No time either"),
        ]
        view.add_thread(events, align="right", source="test")
        view.fit_to_sources()  # must not raise
        view.deleteLater()

    def test_fit_to_sources_same_instant_events(self):
        """Regression #23: a dataset where all events sit at the same instant
        still centers on it with a minimum range."""
        view = TimelineView()
        view.resize(800, 600)
        t = JDNTimestamp.from_ymd(2000, 6, 15)
        events = [
            EventIndex("a", "test", t, t, "A"),
            EventIndex("b", "test", t, t, "B"),
        ]
        view.add_thread(events, align="right", source="test")
        view.fit_to_sources()
        self.assertEqual(view.coord.center_time.value, t.value)
        self.assertGreater(view.coord.scale, 0)
        view.deleteLater()

    def test_event_removed_refreshes_only_owning_source(self):
        """Regression #24: removal refreshes just the thread whose event
        list contains the uuid."""
        view = TimelineView()
        view.resize(800, 600)
        t = JDNTimestamp.from_ymd(2000, 1, 1)
        view.add_thread([EventIndex("a", "src1", t, t, "A")], align="left", source="src1")
        view.add_thread([EventIndex("b", "src2", t, t, "B")], align="right", source="src2")

        refreshed = []
        view.refresh_source = refreshed.append  # observe calls
        view._on_event_removed("a")
        self.assertEqual(refreshed, ["src1"])
        view.deleteLater()


class TestTickLevelVisibility(unittest.TestCase):
    """Regression #17/#18: tick level visibility ranges and Deep Time labels."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def _coord_at_year(self, year: int, px: float = 800.0):
        from universal_history.render.geometry import CoordinateSystem

        view = TimelineView()
        view.resize(int(px), 600)
        coord = view.coord
        coord.center_time = JDNTimestamp.from_year(year)
        return view, coord

    def test_deep_time_excludes_day_month_levels(self):
        from universal_history.render.painter import _visible_ticks

        # Zoomed to show ~1 billion years around year 1_000_000: Day/Week/
        # Month levels are outside their ±10000y visibility range.
        view, coord = self._coord_at_year(1_000_000)
        coord.scale = 800.0 / (2_000_000_000 * 365.2425 * 86400 * 1_000_000)
        level, ticks = _visible_ticks(coord)
        self.assertEqual(level.unit, "Year")
        self.assertGreaterEqual(level.step_count, 10_000)
        self.assertTrue(ticks)
        view.deleteLater()

    def test_deep_time_label_uses_magnitude(self):
        from universal_history.chrono.tick_stepper import TickStepper
        from universal_history.render.painter import _format_tick_label

        level_ma = next(lv for lv in TickStepper.LEVELS if lv.step_count == 5_000_000)
        tick = JDNTimestamp.from_year(5_000_000)
        self.assertEqual(_format_tick_label(tick, level_ma), "5 Ma")

        level_ka = next(lv for lv in TickStepper.LEVELS if lv.step_count == 10_000)
        tick = JDNTimestamp.from_year(20_000)
        self.assertEqual(_format_tick_label(tick, level_ka), "20 ka")

    def test_historical_range_still_uses_day_levels(self):
        from universal_history.render.painter import _visible_ticks

        view, coord = self._coord_at_year(2020)
        # Show ~5 days: Day-level ticks within the ±10000y range.
        coord.scale = 800.0 / (5 * 86400 * 1_000_000)
        level, ticks = _visible_ticks(coord)
        self.assertEqual(level.unit, "Day")
        self.assertEqual(level.step_count, 1)
        self.assertTrue(ticks)
        view.deleteLater()


if __name__ == "__main__":
    unittest.main()
