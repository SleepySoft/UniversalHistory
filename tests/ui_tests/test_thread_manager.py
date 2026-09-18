import unittest
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from universal_history.adapters import HisFileAdapter
from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render import TimelineView
from universal_history.ui import ThreadManagerDialog


class TestThreadManagerDialog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def _make_events(self):
        return [
            EventIndex("a", "src", JDNTimestamp.from_ymd(2000, 1, 1),
                       JDNTimestamp.from_ymd(2000, 1, 1), "A"),
        ]

    def test_dialog_lists_left_and_right_threads(self):
        view = TimelineView()
        view.resize(800, 600)
        view.add_thread(self._make_events(), align="left")
        view.add_thread(self._make_events(), align="right")

        dlg = ThreadManagerDialog(view, adapter=HisFileAdapter())
        self.assertEqual(dlg._left_list.count(), 1)
        self.assertEqual(dlg._right_list.count(), 1)

        view.deleteLater()
        dlg.deleteLater()

    def test_remove_thread(self):
        view = TimelineView()
        view.resize(800, 600)
        thread = view.add_thread(self._make_events(), align="left")

        dlg = ThreadManagerDialog(view, adapter=HisFileAdapter())
        dlg._left_list.setCurrentRow(0)
        with patch(
            "universal_history.ui.thread_manager.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            dlg._on_remove()

        self.assertNotIn(thread, view.left_threads())
        self.assertEqual(dlg._left_list.count(), 0)

        view.deleteLater()
        dlg.deleteLater()

    def test_remove_thread_cancelled_keeps_thread(self):
        view = TimelineView()
        view.resize(800, 600)
        thread = view.add_thread(self._make_events(), align="left")

        dlg = ThreadManagerDialog(view, adapter=HisFileAdapter())
        dlg._left_list.setCurrentRow(0)
        with patch(
            "universal_history.ui.thread_manager.QMessageBox.question",
            return_value=QMessageBox.StandardButton.No,
        ):
            dlg._on_remove()

        self.assertIn(thread, view.left_threads())
        self.assertEqual(dlg._left_list.count(), 1)

        view.deleteLater()
        dlg.deleteLater()

    def test_switch_side(self):
        view = TimelineView()
        view.resize(800, 600)
        thread = view.add_thread(self._make_events(), align="left")

        dlg = ThreadManagerDialog(view, adapter=HisFileAdapter())
        dlg._left_list.setCurrentRow(0)
        dlg._on_switch_side()

        self.assertNotIn(thread, view.left_threads())
        self.assertIn(thread, view.right_threads())
        self.assertEqual(thread.align, "right")

        view.deleteLater()
        dlg.deleteLater()

    def test_axis_offset_slider_updates_view(self):
        view = TimelineView()
        view.resize(800, 600)
        view.coord.axis_offset = 0.5

        dlg = ThreadManagerDialog(view, adapter=HisFileAdapter())
        dlg._offset_slider.setValue(25)
        dlg._on_offset_changed(25)

        self.assertAlmostEqual(view.coord.axis_offset, 0.25, delta=1e-9)

        view.deleteLater()
        dlg.deleteLater()

    def test_share_spin_updates_selected_thread(self):
        view = TimelineView()
        view.resize(800, 600)
        thread = view.add_thread(self._make_events(), align="right")
        view.add_thread(self._make_events(), align="right")

        dlg = ThreadManagerDialog(view, adapter=HisFileAdapter())
        dlg._right_list.setCurrentRow(0)
        dlg._share_spin.setValue(0.75)
        dlg._on_share_changed(0.75)

        self.assertEqual(thread.share, 0.75)

        view.deleteLater()
        dlg.deleteLater()


if __name__ == "__main__":
    unittest.main()
