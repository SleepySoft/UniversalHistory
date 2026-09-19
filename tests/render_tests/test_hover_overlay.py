"""
Tests for the self-drawn hover overlay (legacy real-time tips mechanism):
crosshair + floating info box following the cursor.

Covers the legacy feature set (viewer_ex.paint_real_time_tips /
HistoryIndexBar.get_tip_text):
- time under the cursor is always the first line;
- hovering an item appends the item tip (abstract + date / period range);
- period events show the cursor-year progress "(N/M)";
- the overlay hides while dragging, when disabled, and after leaveEvent.
"""

import unittest

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render import TimelineView

_ONE_YEAR_US = int(365.2425 * 24 * 3600 * 1_000_000)


def _period(start_year: int, end_year: int, uuid: str = "u1") -> EventIndex:
    return EventIndex(
        uuid=uuid, source="s",
        since=JDNTimestamp.from_year(start_year),
        until=JDNTimestamp.from_year(end_year),
        abstract="demo event",
    )


def _point(year: int, uuid: str = "u2") -> EventIndex:
    t = JDNTimestamp.from_year(year)
    return EventIndex(uuid=uuid, source="s", since=t, until=t,
                      abstract="point event")


class Base(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _view(self, events):
        view = TimelineView()
        view.resize(800, 600)
        view.coord.center_time = JDNTimestamp.from_year(2000)
        view.coord.scale = 800 / (40 * _ONE_YEAR_US)  # ~20 px/year
        view.add_thread(events, align="right")
        return view

    def _hover_item(self, view, index=0):
        item = view.right_threads()[0].items[index]
        c = item.screen_rect(view.coord).center()
        view._update_hover(QPointF(c.x(), c.y()))
        return item


class TestOverlayVisibility(Base):

    def test_no_cursor_no_overlay(self):
        view = self._view([_period(1990, 2010)])
        self.assertIsNone(view._hover_overlay_lines())
        view.deleteLater()

    def test_overlay_hidden_while_dragging(self):
        view = self._view([_period(1990, 2010)])
        self._hover_item(view)
        self.assertIsNotNone(view._hover_overlay_lines())
        view._drag_last_pos = QPointF(1, 1)  # left button pressed
        self.assertIsNone(view._hover_overlay_lines())
        view.deleteLater()

    def test_overlay_toggle(self):
        view = self._view([_period(1990, 2010)])
        self._hover_item(view)
        view.set_real_time_tips_enabled(False)
        self.assertIsNone(view._hover_overlay_lines())
        view.set_real_time_tips_enabled(True)
        self.assertIsNotNone(view._hover_overlay_lines())
        view.deleteLater()

    def test_leave_event_clears_overlay(self):
        view = self._view([_period(1990, 2010)])
        self._hover_item(view)
        view.leaveEvent(None)
        self.assertIsNone(view._hover_overlay_lines())
        self.assertIsNone(view._hover_item)
        view.deleteLater()


class TestTipContent(Base):

    def test_cursor_time_is_first_line(self):
        view = self._view([_period(1990, 2010)])
        # Hover an empty area: only the cursor-time line.
        view._update_hover(QPointF(10, 590))
        lines = view._hover_overlay_lines()
        self.assertEqual(len(lines), 1)
        # 800px across 40 years centred on 2000: x=10 is ~1990.5.
        self.assertRegex(lines[0], r"^\(19\d\d/\d\d/\d\d\)$")
        view.deleteLater()

    def test_bce_cursor_time_is_era_aware(self):
        view = self._view([_period(1990, 2010)])
        view.coord.center_time = JDNTimestamp.from_year(-2999)  # 3000 BC
        view._set_center_time(JDNTimestamp.from_year(-2999))
        view._arrange_threads()
        view._update_hover(QPointF(400, 300))
        lines = view._hover_overlay_lines()
        self.assertTrue(lines[0].startswith("(3000 BC/"), lines[0])
        view.deleteLater()

    def test_period_item_tip_has_progress_and_range(self):
        view = self._view([_period(1990, 2010)])
        item = self._hover_item(view)
        lines = view._hover_overlay_lines()
        self.assertEqual(len(lines), 2)
        tip = lines[1]
        self.assertIn("demo event", tip)
        self.assertIn(" : [1990 - 2010]", tip)
        # Cursor sits at the item centre (~2000): progress (11/21).
        self.assertIn("(11/21)", tip)
        view.deleteLater()

    def test_period_progress_follows_cursor(self):
        view = self._view([_period(1990, 2010)])
        item = view.right_threads()[0].items[0]
        rect = item.screen_rect(view.coord)
        view._update_hover(QPointF(rect.left() + 5, rect.center().y()))
        left_tip = view._hover_overlay_lines()[1]
        view._update_hover(QPointF(rect.right() - 1, rect.center().y()))
        right_tip = view._hover_overlay_lines()[1]
        self.assertIn("(1/21)", left_tip)
        # until = 2010-01-01: the last pixel inside the bar is still in 2009,
        # so the right-edge progress is (20/21); (21/21) only at the exact
        # 2010-01-01 boundary.
        self.assertIn("(20/21)", right_tip)
        view.deleteLater()

    def test_point_item_tip_has_date(self):
        view = self._view([_point(2000)])
        self._hover_item(view)
        lines = view._hover_overlay_lines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[1], "point event : [2000-01-01]")
        view.deleteLater()

    def test_bce_period_range_is_era_aware(self):
        view = self._view([_period(-2999, -2900)])  # 3000-2901 BC
        view._set_center_time(JDNTimestamp.from_year(-2950))
        view._arrange_threads()
        self._hover_item(view)
        lines = view._hover_overlay_lines()
        self.assertIn(" : [3000 BC - 2901 BC]", lines[1])
        view.deleteLater()


if __name__ == "__main__":
    unittest.main()
