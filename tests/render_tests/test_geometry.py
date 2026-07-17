import unittest

from universal_history.render.geometry import AXIS_BREADTH, CoordinateSystem


class TestCoordinateSystem(unittest.TestCase):

    def test_default_axis_offset_is_centered(self):
        coord = CoordinateSystem()
        coord.set_widget_size(800, 600)
        self.assertEqual(coord.axis_offset, 0.5)

        center = coord.axis_screen_center()
        self.assertAlmostEqual(center, AXIS_BREADTH / 2 + 0.5 * (600 - AXIS_BREADTH))

        left, right = coord.thread_budgets()
        self.assertAlmostEqual(left + right, 600 - AXIS_BREADTH, delta=1e-9)
        self.assertAlmostEqual(left, right, delta=1e-9)

    def test_axis_offset_0_gives_all_space_to_right(self):
        coord = CoordinateSystem()
        coord.set_widget_size(800, 600)
        coord.axis_offset = 0.0

        left, right = coord.thread_budgets()
        self.assertAlmostEqual(left, 0.0, delta=1e-9)
        self.assertAlmostEqual(right, 600 - AXIS_BREADTH, delta=1e-9)

    def test_axis_offset_1_gives_all_space_to_left(self):
        coord = CoordinateSystem()
        coord.set_widget_size(800, 600)
        coord.axis_offset = 1.0

        left, right = coord.thread_budgets()
        self.assertAlmostEqual(left, 600 - AXIS_BREADTH, delta=1e-9)
        self.assertAlmostEqual(right, 0.0, delta=1e-9)

    def test_vertical_axis_offset_uses_width_as_breadth(self):
        coord = CoordinateSystem()
        coord.set_widget_size(800, 600)
        coord.is_vertical = True

        # In vertical mode breadth is the widget width.
        center = coord.axis_screen_center()
        self.assertAlmostEqual(center, AXIS_BREADTH / 2 + 0.5 * (800 - AXIS_BREADTH))

        left, right = coord.thread_budgets()
        self.assertAlmostEqual(left + right, 800 - AXIS_BREADTH, delta=1e-9)

    def test_transform_maps_logical_origin_to_axis_center(self):
        coord = CoordinateSystem()
        coord.set_widget_size(800, 600)
        coord.axis_offset = 0.25

        from PyQt6.QtCore import QPointF
        origin_screen = coord.logical_to_screen(QPointF(0, 0))
        self.assertAlmostEqual(origin_screen.x(), 800 / 2, delta=1e-9)
        self.assertAlmostEqual(origin_screen.y(), coord.axis_screen_center(), delta=1e-9)


if __name__ == "__main__":
    unittest.main()
