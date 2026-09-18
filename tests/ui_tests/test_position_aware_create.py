"""
Regression tests for T5-1 position-aware event creation: the time under the
right-click position is prefilled into the editor's Time field.
"""

import unittest

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import Workspace
from universal_history.render import TimelineView
from universal_history.ui.editor import EventEditor, EventEditorDialog


class TestTimeAtScreen(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_axis_center_maps_to_center_time(self):
        view = TimelineView()
        view.resize(800, 600)
        center = JDNTimestamp.from_year(2000)
        view.coord.center_time = center
        view.coord.scale = 1e-10
        t = view.time_at_screen(QPointF(400, 100))
        self.assertEqual(t.value, center.value)
        view.deleteLater()

    def test_right_of_center_is_later(self):
        view = TimelineView()
        view.resize(800, 600)
        view.coord.center_time = JDNTimestamp.from_year(2000)
        view.coord.scale = 1e-10
        self.assertGreater(
            view.time_at_screen(QPointF(600, 100)).value,
            view.time_at_screen(QPointF(200, 100)).value,
        )
        view.deleteLater()


class TestPresetTimeText(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_new_record_prefilled_and_dirty(self):
        ws = Workspace()
        ed = EventEditor(ws, source="s", preset_time_text="2020-01-01 AD")
        self.assertEqual(ed._line_time.text(), "2020-01-01 AD")
        self.assertTrue(ed.is_dirty())
        ed.deleteLater()

    def test_no_preset_stays_blank_and_clean(self):
        ws = Workspace()
        ed = EventEditor(ws, source="s")
        self.assertEqual(ed._line_time.text(), "")
        self.assertFalse(ed.is_dirty())
        ed.deleteLater()

    def test_dialog_passes_preset_through(self):
        ws = Workspace()
        dlg = EventEditorDialog(ws, source="s", preset_time_text="1999-12-31 AD")
        self.assertEqual(dlg.editor._line_time.text(), "1999-12-31 AD")
        dlg.deleteLater()


if __name__ == "__main__":
    unittest.main()
