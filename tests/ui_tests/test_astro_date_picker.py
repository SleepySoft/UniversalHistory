"""
Regression tests for the BCE-capable astronomical date picker (decision
phase 2 — the hand-rolled year/month/day control beyond Qt's 1-9999 range).
"""

import unittest

from PyQt6.QtWidgets import QApplication, QDialog

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.ui.astro_date_dialog import AstroDatePickerDialog


class TestAstroDatePicker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_initial_bce_date_shows_bc_era(self):
        dlg = AstroDatePickerDialog(JDNTimestamp.from_ymd(-2999, 6, 15))
        self.assertEqual(dlg._year.value(), -2999)
        self.assertIn("3000", dlg._era.text())  # year -2999 = 3000 BC
        self.assertEqual(dlg._month.value(), 6)
        self.assertEqual(dlg._day.value(), 15)
        dlg.deleteLater()

    def test_year_zero_is_1_bc(self):
        dlg = AstroDatePickerDialog(JDNTimestamp.from_ymd(0, 1, 1))
        self.assertIn("1", dlg._era.text())
        dlg.deleteLater()

    def test_accept_returns_timestamp(self):
        dlg = AstroDatePickerDialog(JDNTimestamp.from_ymd(-43, 3, 15))  # 44 BC
        dlg._on_accept()
        self.assertEqual(dlg.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(dlg.selected().to_gregorian()[:3], (-43, 3, 15))
        dlg.deleteLater()

    def test_invalid_day_rejected(self):
        dlg = AstroDatePickerDialog(JDNTimestamp.from_ymd(2000, 1, 1))
        dlg._month.setValue(2)
        dlg._day.setValue(30)
        dlg._on_accept()
        self.assertNotEqual(dlg.result(), QDialog.DialogCode.Accepted)
        self.assertTrue(dlg._error.text())
        dlg.deleteLater()

    def test_time_components_roundtrip(self):
        dlg = AstroDatePickerDialog(JDNTimestamp.from_ymd_hms(-99, 12, 31, 23, 59, 58))
        dlg._on_accept()
        self.assertEqual(dlg.selected().to_gregorian()[:6], (-99, 12, 31, 23, 59, 58))
        dlg.deleteLater()

    def test_editor_calendar_uses_astro_picker_for_bce(self):
        """_on_pick_date routes out-of-Qt-range times to the astro picker."""
        from unittest.mock import patch
        from universal_history.models import Workspace
        from universal_history.ui.editor import EventEditor

        ws = Workspace()
        ed = EventEditor(ws, source="s")
        ed._line_time.setText("3000 BC")
        with patch.object(AstroDatePickerDialog, "exec",
                          return_value=QDialog.DialogCode.Rejected) as m:
            ed._on_pick_date()
        self.assertTrue(m.called)
        ed.deleteLater()


if __name__ == "__main__":
    unittest.main()
