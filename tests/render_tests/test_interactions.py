"""
Interaction tests: drag pan, click vs drag discrimination, wheel pan,
Ctrl+wheel zoom anchoring, arrow-key scrolling, double-click edit,
context-menu and quick-entry signals — all driven by synthesised events
delivered through QApplication.sendEvent (tier-2 injection, see
docs/testing.md §3).
"""

import unittest
from unittest.mock import patch

from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QContextMenuEvent, QKeyEvent, QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render import TimelineView

_ONE_YEAR_US = int(365.2425 * 24 * 3600 * 1_000_000)


def _period(start_year: int, end_year: int, uuid: str = "u1") -> EventIndex:
    return EventIndex(
        uuid=uuid,
        source="s",
        since=JDNTimestamp.from_year(start_year),
        until=JDNTimestamp.from_year(end_year),
        abstract=f"event {uuid}",
    )


def _mouse(view, etype, pos: QPointF, button=Qt.MouseButton.LeftButton,
           buttons=Qt.MouseButton.LeftButton) -> QMouseEvent:
    return QMouseEvent(etype, pos, QPointF(view.mapToGlobal(pos.toPoint())),
                       button, buttons, Qt.KeyboardModifier.NoModifier)


def _wheel(view, pos: QPointF, angle: int = 120) -> QWheelEvent:
    return QWheelEvent(pos, QPointF(view.mapToGlobal(pos.toPoint())),
                       QPoint(0, 0), QPoint(0, angle),
                       Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                       Qt.ScrollPhase.NoScrollPhase, False)


class Base(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _view(self):
        view = TimelineView()
        view.resize(800, 600)
        view.coord.center_time = JDNTimestamp.from_year(2000)
        view.coord.scale = 800 / (40 * _ONE_YEAR_US)  # 800 px across ~40 years
        view.add_thread([_period(1990, 2010)], align="right")
        return view

    def _item_center(self, view) -> QPointF:
        c = view.right_threads()[0].items[0].screen_rect(view.coord).center()
        return QPointF(c.x(), c.y())


class TestDragPan(Base):

    def test_drag_pans_view_and_items_follow(self):
        view = self._view()
        item = view.right_threads()[0].items[0]
        before_rect = item.screen_rect(view.coord)
        before_center = view.coord.center_time.value

        QApplication.sendEvent(view, _mouse(view, QEvent.Type.MouseButtonPress,
                                            QPointF(400, 300)))
        QApplication.sendEvent(view, _mouse(view, QEvent.Type.MouseMove,
                                            QPointF(550, 300)))
        QApplication.sendEvent(view, _mouse(view, QEvent.Type.MouseButtonRelease,
                                            QPointF(550, 300)))

        # Centre moved earlier in time; the item followed by the same 150 px.
        self.assertLess(view.coord.center_time.value, before_center)
        after_rect = item.screen_rect(view.coord)
        self.assertAlmostEqual(after_rect.left() - before_rect.left(), 150.0, delta=2.0)
        view.deleteLater()

    def test_drag_does_not_emit_itemClicked(self):
        view = self._view()
        fired = []
        view.itemClicked.connect(fired.append)
        start = self._item_center(view)

        QApplication.sendEvent(view, _mouse(view, QEvent.Type.MouseButtonPress, start))
        QApplication.sendEvent(view, _mouse(view, QEvent.Type.MouseMove,
                                            QPointF(start.x() + 80, start.y())))
        QApplication.sendEvent(view, _mouse(view, QEvent.Type.MouseButtonRelease,
                                            QPointF(start.x() + 80, start.y())))
        self.assertEqual(fired, [])
        view.deleteLater()

    def test_click_on_item_emits_itemClicked(self):
        view = self._view()
        fired = []
        view.itemClicked.connect(fired.append)
        pos = self._item_center(view)

        QApplication.sendEvent(view, _mouse(view, QEvent.Type.MouseButtonPress, pos))
        QApplication.sendEvent(view, _mouse(view, QEvent.Type.MouseButtonRelease, pos,
                                            buttons=Qt.MouseButton.NoButton))
        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0].uuid, "u1")
        view.deleteLater()


class TestWheelPanAndZoom(Base):

    def test_wheel_pans_without_ctrl(self):
        view = self._view()
        before = view.coord.center_time.value
        before_scale = view.coord.scale

        QApplication.sendEvent(view, _wheel(view, QPointF(400, 300), 120))

        self.assertNotEqual(view.coord.center_time.value, before)
        self.assertEqual(view.coord.scale, before_scale)  # wheel pan keeps zoom
        view.deleteLater()

    def test_ctrl_wheel_zooms_anchored_at_cursor(self):
        view = self._view()
        pos = QPointF(600, 300)
        time_before = view.time_at_screen(pos).value
        scale_before = view.coord.scale

        # wheelEvent reads QApplication.keyboardModifiers() (global state),
        # so inject the modifier at the source.
        with patch.object(QApplication, "keyboardModifiers",
                          return_value=Qt.KeyboardModifier.ControlModifier):
            QApplication.sendEvent(view, _wheel(view, pos, 120))

        self.assertGreater(view.coord.scale, scale_before)
        # The time under the cursor is preserved by the zoom anchor.
        time_after = view.time_at_screen(pos).value
        self.assertAlmostEqual(time_after - time_before, 0,
                               delta=abs(time_before) * 1e-6 + 5000)
        view.deleteLater()


class TestArrowKeyScroll(Base):

    def test_arrow_keys_register_and_scroll(self):
        view = self._view()
        press = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Right,
                          Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(view, press)
        self.assertIn(Qt.Key.Key_Right, view._scroll_keys)
        self.assertTrue(view._scroll_timer.isActive())

        before = view.coord.center_time.value
        view._on_scroll_timer()  # timer effect (timer itself tested implicitly)
        self.assertGreater(view.coord.center_time.value, before)

        release = QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Right,
                            Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(view, release)
        self.assertNotIn(Qt.Key.Key_Right, view._scroll_keys)
        self.assertFalse(view._scroll_timer.isActive())
        view.deleteLater()


class TestDoubleClickAndContextMenu(Base):

    def test_double_click_item_emits_signal(self):
        view = self._view()
        fired = []
        view.itemDoubleClicked.connect(fired.append)
        pos = self._item_center(view)

        dbl = _mouse(view, QEvent.Type.MouseButtonDblClick, pos)
        QApplication.sendEvent(view, dbl)
        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0].uuid, "u1")
        view.deleteLater()

    def test_double_click_empty_band_requests_quick_entry(self):
        view = self._view()
        fired = []
        view.quickEntryRequested.connect(lambda *args: fired.append(args))

        # Empty area inside the thread band: directly under the item-free
        # part of the band (right thread band top area near the left edge).
        thread = view.right_threads()[0]
        # Logical (x far from any item, y inside the band) -> screen.
        logical = QPointF(-10_000.0, (thread.y0 + thread.y1) / 2)
        pos = view.coord.logical_to_screen(logical)

        dbl = _mouse(view, QEvent.Type.MouseButtonDblClick, pos)
        QApplication.sendEvent(view, dbl)
        self.assertEqual(len(fired), 1)
        thread_arg, time_arg = fired[0]
        self.assertIs(thread_arg, thread)
        self.assertIsInstance(time_arg, JDNTimestamp)
        view.deleteLater()

    def test_context_menu_on_item_carries_event(self):
        view = self._view()
        fired = []
        view.contextMenuRequested.connect(lambda *args: fired.append(args))
        pos = self._item_center(view)

        ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, pos.toPoint(),
                               view.mapToGlobal(pos.toPoint()))
        QApplication.sendEvent(view, ev)
        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0][1].uuid, "u1")  # (globalPos, EventIndex)
        view.deleteLater()

    def test_context_menu_on_empty_area_carries_none(self):
        view = self._view()
        fired = []
        view.contextMenuRequested.connect(lambda *args: fired.append(args))

        ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(10, 590),
                               view.mapToGlobal(QPoint(10, 590)))
        QApplication.sendEvent(view, ev)
        self.assertEqual(len(fired), 1)
        self.assertIsNone(fired[0][1])
        view.deleteLater()


if __name__ == "__main__":
    unittest.main()
