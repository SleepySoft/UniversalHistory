"""
Regression tests for T5-2: after a new event is saved, the view jumps to it
(TimelineView.reveal_time) — but never moves when the time is already visible.
"""

import unittest

from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.render import TimelineView


class TestRevealTime(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _view(self):
        view = TimelineView()
        view.resize(800, 600)
        view.coord.center_time = JDNTimestamp.from_year(2000)
        # 800 px across ~400 years: 800 / (400 * 365.2425 * 86400 * 1e6).
        view.coord.scale = 800 / (400 * 365.2425 * 86400 * 1e6)
        return view

    def test_visible_time_does_not_move_view(self):
        view = self._view()
        before = view.coord.center_time.value
        view.reveal_time(JDNTimestamp.from_year(2005))
        self.assertEqual(view.coord.center_time.value, before)
        view.deleteLater()

    def test_far_time_centers_view(self):
        view = self._view()
        target = JDNTimestamp.from_year(5000)
        view.reveal_time(target)
        self.assertEqual(view.coord.center_time.value, target.value)
        view.deleteLater()

    def test_past_far_time_centers_view(self):
        view = self._view()
        target = JDNTimestamp.from_year(-2999)  # 3000 BC
        view.reveal_time(target)
        self.assertEqual(view.coord.center_time.value, target.value)
        view.deleteLater()


if __name__ == "__main__":
    unittest.main()
