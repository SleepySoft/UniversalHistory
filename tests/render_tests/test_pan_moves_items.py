"""
Regression test: panning must move event bars together with the axis.

Root cause of the original bug: ThreadLayout cached item rects in
center-relative logical coordinates, and panning skipped re-layout
(known-issues #21 optimization) — so bars stayed pinned to their stale
screen positions while the axis moved (they only appeared/disappeared via
visibility culling).  The fix introduces a layout *anchor*: cached geometry
is anchor-relative and the pan drift is applied inside
CoordinateSystem.transform().
"""

import unittest

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render import TimelineView

_ONE_YEAR_US = int(365.2425 * 24 * 3600 * 1_000_000)


def _period(start_year: int, end_year: int) -> EventIndex:
    return EventIndex(
        uuid=f"u-{start_year}",
        source="s",
        since=JDNTimestamp.from_year(start_year),
        until=JDNTimestamp.from_year(end_year),
        abstract=f"{start_year}-{end_year}",
    )


class TestPanMovesItems(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _view(self):
        view = TimelineView()
        view.resize(800, 600)
        view.coord.center_time = JDNTimestamp.from_year(2000)
        # 800 px across ~40 years.
        view.coord.scale = 800 / (40 * _ONE_YEAR_US)
        view.add_thread([_period(1990, 2010)], align="right")
        return view

    def _only_item(self, view):
        threads = view.left_threads() + view.right_threads()
        self.assertEqual(len(threads), 1)
        self.assertEqual(len(threads[0].items), 1)
        return threads[0].items[0]

    def test_pan_shifts_item_on_screen(self):
        view = self._view()
        item = self._only_item(view)
        before = item.screen_rect(view.coord)

        # Pan right by 100 screen px (view centre moves earlier in time, so
        # the content shifts right — matching drag behaviour).
        delta_px = 100.0
        delta_us = int(delta_px / view.coord.scale)
        view._set_center_time(
            JDNTimestamp(view.coord.center_time.value - delta_us)
        )

        after = item.screen_rect(view.coord)
        self.assertAlmostEqual(after.left() - before.left(), delta_px, delta=1.0)
        self.assertAlmostEqual(after.right() - before.right(), delta_px, delta=1.0)
        view.deleteLater()

    def test_hit_testing_follows_panned_item(self):
        view = self._view()
        item = self._only_item(view)

        delta_px = 100.0
        delta_us = int(delta_px / view.coord.scale)
        view._set_center_time(
            JDNTimestamp(view.coord.center_time.value - delta_us)
        )

        rect = item.screen_rect(view.coord)
        center = rect.center()
        hit = view._item_at_screen(QPointF(center.x(), center.y()))
        self.assertIsNotNone(hit)
        self.assertEqual(hit.event.uuid, item.event.uuid)
        view.deleteLater()

    def test_time_at_screen_tracks_pan(self):
        view = self._view()
        mid = QPointF(400, 300)
        before = view.time_at_screen(mid).value

        delta_px = 100.0
        delta_us = int(delta_px / view.coord.scale)
        view._set_center_time(
            JDNTimestamp(view.coord.center_time.value - delta_us)
        )

        after = view.time_at_screen(mid).value
        self.assertAlmostEqual(after - before, -delta_us, delta=2)
        view.deleteLater()

    def test_large_drift_reanchors_without_jump(self):
        view = self._view()
        item = self._only_item(view)
        before = item.screen_rect(view.coord)

        # Pan beyond the re-anchor threshold (4 viewport lengths).
        delta_us = int(800 * 10 / view.coord.scale)
        view._set_center_time(
            JDNTimestamp(view.coord.center_time.value + delta_us)
        )
        # Anchor must have been re-synced.
        self.assertAlmostEqual(view.coord.center_logical_x(), 0.0, delta=1.0)

        # Pan back; the item must return to its original screen position.
        view._set_center_time(JDNTimestamp.from_year(2000))
        after = item.screen_rect(view.coord)
        self.assertAlmostEqual(after.left(), before.left(), delta=1.0)
        view.deleteLater()


if __name__ == "__main__":
    unittest.main()
