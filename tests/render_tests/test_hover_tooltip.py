"""
Regression tests: hover tooltip must be shown *actively* (legacy behaviour —
the popup follows the cursor and appears immediately while moving), not via
the passive widget toolTip property that only pops up after the cursor rests.

The passive-property version read to users as "hover info is missing".
"""

import unittest
from unittest.mock import patch

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render import TimelineView


def _period(start_year: int, end_year: int) -> EventIndex:
    return EventIndex(
        uuid="u1",
        source="s",
        since=JDNTimestamp.from_year(start_year),
        until=JDNTimestamp.from_year(end_year),
        abstract="demo event",
    )


class TestHoverTooltipActive(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _view(self):
        view = TimelineView()
        view.resize(800, 600)
        view.coord.center_time = JDNTimestamp.from_year(2000)
        one_year_us = int(365.2425 * 24 * 3600 * 1_000_000)
        view.coord.scale = 800 / (40 * one_year_us)
        view.add_thread([_period(1990, 2010)], align="right")
        return view

    def test_hover_shows_tooltip_immediately(self):
        view = self._view()
        item = view.right_threads()[0].items[0]
        center = item.screen_rect(view.coord).center()

        with patch("universal_history.render.timeline_view.QToolTip") as tip:
            view._update_hover(QPointF(center.x(), center.y()))
            tip.showText.assert_called_once()
            text = tip.showText.call_args[0][1]
            self.assertIn("demo event", text)
            self.assertIn("Year", text)  # period progress line
        view.deleteLater()

    def test_tooltip_follows_cursor_within_item(self):
        view = self._view()
        item = view.right_threads()[0].items[0]
        rect = item.screen_rect(view.coord)

        with patch("universal_history.render.timeline_view.QToolTip") as tip:
            view._update_hover(QPointF(rect.left() + 10, rect.center().y()))
            view._update_hover(QPointF(rect.right() - 10, rect.center().y()))
            # Re-shown on every move so the popup tracks the cursor.
            self.assertEqual(tip.showText.call_count, 2)
        view.deleteLater()

    def test_leaving_item_hides_tooltip(self):
        view = self._view()
        item = view.right_threads()[0].items[0]
        center = item.screen_rect(view.coord).center()

        with patch("universal_history.render.timeline_view.QToolTip") as tip:
            view._update_hover(QPointF(center.x(), center.y()))
            # Move to an empty area (far below all threads).
            view._update_hover(QPointF(10, 590))
            tip.hideText.assert_called_once()
            self.assertIsNone(view._hover_item)
        view.deleteLater()

    def test_leave_event_hides_tooltip(self):
        view = self._view()
        item = view.right_threads()[0].items[0]
        center = item.screen_rect(view.coord).center()

        with patch("universal_history.render.timeline_view.QToolTip") as tip:
            view._update_hover(QPointF(center.x(), center.y()))
            view.leaveEvent(None)
            tip.hideText.assert_called_once()
            self.assertIsNone(view._hover_item)
        view.deleteLater()


if __name__ == "__main__":
    unittest.main()
