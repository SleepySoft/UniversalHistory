"""
Tests for the point-event "lollipop" redesign (2026-09-19): the card's left
edge IS the event instant, and the painter connects it to the axis with a
stem + dot. Replaces the centred chip with an unexplained middle pin.
"""

import unittest

from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render import TimelineView
from universal_history.render.layout import POINT_EVENT_PIXEL_WIDTH

_ONE_YEAR_US = int(365.2425 * 24 * 3600 * 1_000_000)


def _point(year: int, uuid: str = "u") -> EventIndex:
    t = JDNTimestamp.from_year(year)
    return EventIndex(uuid=uuid, source="s", since=t, until=t,
                      abstract="point")


class TestPointLollipop(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _view(self):
        view = TimelineView()
        view.resize(800, 600)
        view.coord.center_time = JDNTimestamp.from_year(2000)
        view.coord.scale = 800 / (10 * _ONE_YEAR_US)  # 80 px/year
        view.add_thread([_point(2000)], align="right")
        return view

    def test_card_left_edge_is_the_instant(self):
        view = self._view()
        item = view.right_threads()[0].items[0]
        time_x = view.coord.time_to_logical_x(item.event.since)
        self.assertAlmostEqual(item.x0, time_x, delta=1e-6)
        self.assertAlmostEqual(item.x1 - item.x0, POINT_EVENT_PIXEL_WIDTH,
                               delta=1e-6)
        view.deleteLater()

    def test_axis_dot_screen_x_matches_instant(self):
        view = self._view()
        item = view.right_threads()[0].items[0]
        # The stem/dot sit at logical x = x0, i.e. the same screen X as the
        # card's left edge (horizontal mode).
        rect = item.screen_rect(view.coord)
        logical_dot = view.coord.logical_to_screen(
            __import__("PyQt6.QtCore", fromlist=["QPointF"]).QPointF(item.x0, 0)
        )
        self.assertAlmostEqual(logical_dot.x(), rect.left(), delta=1.0)
        view.deleteLater()

    def test_left_side_thread_also_anchors_left_edge(self):
        view = TimelineView()
        view.resize(800, 600)
        view.coord.center_time = JDNTimestamp.from_year(2000)
        view.coord.scale = 800 / (10 * _ONE_YEAR_US)
        view.add_thread([_point(2000)], align="left")
        item = view.left_threads()[0].items[0]
        time_x = view.coord.time_to_logical_x(item.event.since)
        self.assertAlmostEqual(item.x0, time_x, delta=1e-6)
        # Card sits above the axis (negative logical y) — stem targets y=0.
        self.assertLess(item.y1, 0)
        view.deleteLater()


if __name__ == "__main__":
    unittest.main()
