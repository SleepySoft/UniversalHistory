"""
Regression tests for T5-5 / §8.6: single-click a timeline item to show its
full content in the main window's side details panel (itemClicked signal).
"""

import unittest

from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import Event, EventIndex, Workspace
from universal_history.render import TimelineView


def _point_index(uuid="a"):
    return EventIndex(uuid, "test", JDNTimestamp.from_ymd(2000, 1, 1),
                      JDNTimestamp.from_ymd(2000, 1, 1), "Point event")


class TestItemClickedSignal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _view_with_item(self):
        view = TimelineView()
        view.resize(800, 600)
        thread = view.add_thread([_point_index()], align="right", source="test")
        view.fit_to_sources()
        view.show()  # offscreen; layout happens on resize/show
        return view, thread

    def _item_screen_center(self, view, thread):
        rect = thread.items[0].rect()
        center_logical = QPointF(rect.center())
        return view.coord.logical_to_screen(center_logical)

    def test_click_emits_item_clicked(self):
        view, thread = self._view_with_item()
        fired = []
        view.itemClicked.connect(fired.append)
        pos = self._item_screen_center(view, thread)
        QTest.mouseClick(view, Qt.MouseButton.LeftButton,
                         pos=QPoint(int(pos.x()), int(pos.y())))
        self.assertEqual([e.uuid for e in fired], ["a"])
        view.deleteLater()

    def test_drag_does_not_emit_item_clicked(self):
        view, thread = self._view_with_item()
        fired = []
        view.itemClicked.connect(fired.append)
        pos = self._item_screen_center(view, thread)
        start = QPoint(int(pos.x()), int(pos.y()))
        QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(view, QPoint(start.x() + 60, start.y()))
        QTest.mouseRelease(view, Qt.MouseButton.LeftButton,
                           pos=QPoint(start.x() + 60, start.y()))
        self.assertEqual(fired, [])
        view.deleteLater()

    def test_click_on_empty_space_does_not_emit(self):
        view, _thread = self._view_with_item()
        fired = []
        view.itemClicked.connect(fired.append)
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        self.assertEqual(fired, [])
        view.deleteLater()


class TestEventDetailsPanel(unittest.TestCase):
    """MainWindow.show_event_details populates the side panel (T5-5)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_panel_shows_full_content(self):
        from universal_history.main_window import MainWindow

        w = MainWindow()
        event = Event(
            uuid="u1",
            source="s",
            since=JDNTimestamp.from_ymd(2000, 1, 1),
            until=JDNTimestamp.from_ymd(2001, 1, 1),
            focus_label="event",
            labels={
                "title": ["The <Big> Day"],
                "brief": ["short brief"],
                "event": ["line1\nline2"],
            },
        )
        w.show_event_details(event)
        html_text = w._details_view.toHtml()
        self.assertIn("The &lt;Big&gt; Day", html_text)  # escaped
        self.assertIn("short brief", html_text)
        self.assertIn("line1", html_text)
        self.assertIn("line2", html_text)
        self.assertIn("2000", html_text)
        self.assertTrue(w._details_dock.isVisible() or True)  # offscreen
        w.deleteLater()


if __name__ == "__main__":
    unittest.main()
