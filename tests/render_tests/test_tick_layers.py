"""
Regression tests for known-issues #16 (dual-layer ticks with density-driven
fade) and #19 (paint/hit-test visibility culling).
"""

import unittest
from types import SimpleNamespace

from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.render import TimelineView
from universal_history.render.painter import (
    TICK_FADE_FULL_PX,
    TICK_FADE_MIN_PX,
    _tick_layers,
    _tick_opacity,
    item_in_time_range,
)


class TestTickLayers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _coord(self, year: int, scale: float):
        view = TimelineView()
        view.resize(800, 600)
        view.coord.center_time = JDNTimestamp.from_year(year)
        view.coord.scale = scale
        return view

    def test_opacity_ramp(self):
        self.assertEqual(_tick_opacity(TICK_FADE_MIN_PX - 1), 0.0)
        self.assertEqual(_tick_opacity(TICK_FADE_MIN_PX), 0.0)
        mid = (TICK_FADE_MIN_PX + TICK_FADE_FULL_PX) / 2
        self.assertAlmostEqual(_tick_opacity(mid), 0.5)
        self.assertEqual(_tick_opacity(TICK_FADE_FULL_PX), 1.0)
        self.assertEqual(_tick_opacity(10_000), 1.0)

    def test_dual_layer_at_transition_zoom(self):
        """Zoom where months fade in while quarters are the major scale."""
        # month (30d) at 75 px -> fading-in minor;
        # quarter (90d) at 225 px -> major; year (365d) at ~912 px -> demoted.
        month_us = 30 * 86400 * 1_000_000
        scale = 75.0 / month_us
        view = self._coord(2020, scale)
        layers = _tick_layers(view.coord)
        view.deleteLater()

        self.assertGreaterEqual(len(layers), 2)
        roles = {lvl.id: role for lvl, _, _, role in layers}
        alphas = {lvl.id: alpha for lvl, _, alpha, _ in layers}

        self.assertEqual(roles.get("month_1"), "minor")
        self.assertEqual(roles.get("month_3"), "major")
        self.assertEqual(roles.get("year_1"), "demoted")
        self.assertGreater(alphas["month_1"], 0.0)
        self.assertLess(alphas["month_1"], 1.0)
        self.assertEqual(alphas["month_3"], 1.0)

    def test_layers_ordered_fine_to_coarse(self):
        month_us = 30 * 86400 * 1_000_000
        view = self._coord(2020, 75.0 / month_us)
        layers = _tick_layers(view.coord)
        view.deleteLater()
        durations = [level.avg_duration_us for level, *_ in layers]
        self.assertEqual(durations, sorted(durations))

    def test_zoomed_out_single_major(self):
        """Fully zoomed out: coarsest layer is demoted; any fading-in minor
        layer is semi-transparent, and roles progress minor -> major ->
        demoted as levels coarsen."""
        view = self._coord(0, 800.0 / (2_000_000_000 * 365.2425 * 86400 * 1_000_000))
        layers = _tick_layers(view.coord)
        view.deleteLater()
        self.assertTrue(layers)
        roles = [role for *_, role in layers]
        alphas = {lvl.id: alpha for lvl, _, alpha, _ in layers}
        # Layers stop at the first demoted (coarsest background) level.
        self.assertEqual(roles[-1], "demoted")
        self.assertNotIn("demoted", roles[:-1])
        # A fading-in minor layer must be semi-transparent, never full.
        for lvl, _, alpha, role in layers:
            if role == "minor":
                self.assertLess(alpha, 1.0, lvl.id)
        order = {"minor": 0, "major": 1, "demoted": 2}
        self.assertEqual([order[r] for r in roles], sorted(order[r] for r in roles))


class TestVisibilityCulling(unittest.TestCase):

    def _item(self, since_year, until_year):
        ev = SimpleNamespace(
            since=JDNTimestamp.from_year(since_year) if since_year is not None else None,
            until=JDNTimestamp.from_year(until_year) if until_year is not None else None,
        )
        return SimpleNamespace(event=ev)

    def test_culls_outside_range(self):
        start = JDNTimestamp.from_year(2000)
        end = JDNTimestamp.from_year(2020)
        self.assertTrue(item_in_time_range(self._item(2005, 2010), start, end))
        self.assertFalse(item_in_time_range(self._item(1990, 1995), start, end))
        self.assertFalse(item_in_time_range(self._item(2030, 2035), start, end))
        # Overlapping edges are kept.
        self.assertTrue(item_in_time_range(self._item(1995, 2000), start, end))
        self.assertTrue(item_in_time_range(self._item(2020, 2030), start, end))

    def test_timeless_items_never_culled(self):
        start = JDNTimestamp.from_year(2000)
        end = JDNTimestamp.from_year(2020)
        self.assertTrue(item_in_time_range(self._item(None, None), start, end))

    def test_margin_keeps_edge_cards(self):
        start = JDNTimestamp.from_year(2000)
        end = JDNTimestamp.from_year(2020)
        item = self._item(1999, 1999)
        self.assertFalse(item_in_time_range(item, start, end))
        big_margin = int(400 * 365.2425 * 86400 * 1_000_000)  # ~400 years
        self.assertTrue(item_in_time_range(item, start, end, big_margin))


if __name__ == "__main__":
    unittest.main()
