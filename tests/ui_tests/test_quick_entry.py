"""
Regression tests for T5-4: quick entry — double-click an empty thread band
creates an event in one step (title + time prefilled from the clicked spot).
"""

import unittest

from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render import TimelineView
from universal_history.ui.quick_entry_dialog import QuickEntryDialog


class TestQuickEntryDialog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_empty_title_rejected(self):
        dlg = QuickEntryDialog(preset_time_text="2020-01-01 AD")
        dlg._on_accept()
        self.assertNotEqual(dlg.result(), QDialog.DialogCode.Accepted)
        self.assertTrue(dlg._error.text())
        dlg.deleteLater()

    def test_bad_time_rejected(self):
        dlg = QuickEntryDialog(preset_time_text="not a time at all ##")
        dlg._line_title.setText("My event")
        dlg._on_accept()
        self.assertNotEqual(dlg.result(), QDialog.DialogCode.Accepted)
        dlg.deleteLater()

    def test_valid_input_accepted(self):
        dlg = QuickEntryDialog(preset_time_text="2020-01-01 AD")
        dlg._line_title.setText("My event")
        dlg._on_accept()
        self.assertEqual(dlg.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(dlg.get_result(), ("My event", "2020-01-01 AD"))
        dlg.deleteLater()


class TestQuickEntrySignal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _view_with_thread(self):
        view = TimelineView()
        view.resize(800, 600)
        events = [
            EventIndex("a", "test", JDNTimestamp.from_ymd(2000, 1, 1),
                       JDNTimestamp.from_ymd(2000, 1, 1), "Point event"),
        ]
        thread = view.add_thread(events, align="right", source="test")
        view.fit_to_sources()
        view.show()
        return view, thread

    def test_band_hit_detection(self):
        view, thread = self._view_with_thread()
        rect = thread.items[0].rect()
        in_band = view.coord.logical_to_screen(
            QPointF(rect.center().x(), (thread.y0 + thread.y1) / 2)
        )
        self.assertIs(view.thread_band_at_screen(in_band), thread)
        # Far above the band (logical y well below y0) -> no thread.
        outside = view.coord.logical_to_screen(
            QPointF(rect.center().x(), thread.y0 - 500)
        )
        self.assertIsNone(view.thread_band_at_screen(outside))
        view.deleteLater()

    def test_double_click_empty_band_requests_quick_entry(self):
        view, thread = self._view_with_thread()
        fired = []
        view.quickEntryRequested.connect(
            lambda th, t: fired.append((th, t))
        )
        # A band position far along the axis from the single item (empty area).
        empty = view.coord.logical_to_screen(
            QPointF(thread.items[0].rect().right() + 3000,
                    (thread.y0 + thread.y1) / 2)
        )
        QTest.mouseDClick(view, Qt.MouseButton.LeftButton,
                          pos=QPoint(int(empty.x()), int(empty.y())))
        self.assertEqual(len(fired), 1)
        self.assertIs(fired[0][0], thread)
        self.assertIsInstance(fired[0][1], JDNTimestamp)
        view.deleteLater()


if __name__ == "__main__":
    unittest.main()
