"""
Regression tests for the period-event hover progress hint (legacy feature
「第N年/共M年」, restored as "Year N of M" in the tooltip).
"""

import unittest

from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render.timeline_view import TimelineView


def _index(since_year, until_year):
    return EventIndex(
        uuid="u",
        source="s",
        since=JDNTimestamp.from_year(since_year),
        until=JDNTimestamp.from_year(until_year),
        abstract="demo",
    )


class TestHoverProgress(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_point_event_has_no_progress(self):
        ev = _index(2000, 2000)
        text = TimelineView._tooltip_text(ev, hover_year=2000)
        self.assertNotIn("Year", text.split("\n")[-1])

    def test_period_progress_at_cursor(self):
        ev = _index(2000, 2009)  # 10 years
        text = TimelineView._tooltip_text(ev, hover_year=2004)
        self.assertIn("Year 5 of 10", text)

    def test_progress_clamped_into_range(self):
        ev = _index(2000, 2009)
        self.assertIn("Year 1 of 10",
                      TimelineView._tooltip_text(ev, hover_year=1995))
        self.assertIn("Year 10 of 10",
                      TimelineView._tooltip_text(ev, hover_year=2020))

    def test_progress_across_era_boundary(self):
        # 10 BC (astronomical -9) .. 1 BC (astronomical 0): 10 years.
        ev = _index(-9, 0)
        # 5 BC = astronomical -4 -> 6th year.
        self.assertIn("Year 6 of 10",
                      TimelineView._tooltip_text(ev, hover_year=-4))

    def test_no_hover_year_keeps_old_tooltip(self):
        ev = _index(2000, 2009)
        text = TimelineView._tooltip_text(ev)
        self.assertEqual(len(text.split("\n")), 2)


if __name__ == "__main__":
    unittest.main()
