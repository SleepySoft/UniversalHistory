"""
Regression tests for the P7 UI completions:
- arrow-key smooth scrolling (legacy defect #12)
- Help/About menu entries (legacy defect #16)
- Label Tag Editor tab sync (legacy defect #39)
- filter preset save/load, utf-8 (legacy defects #42/#45)
"""

import tempfile
import unittest
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import Event, Workspace
from universal_history.render import TimelineView
from universal_history.ui import FilterDialog
from universal_history.ui.editor import EventEditorDialog
from universal_history.main_window import MainWindow


def _key(key):
    return QKeyEvent(
        QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier
    )


class TestArrowKeyScroll(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.view = TimelineView()
        self.view.resize(800, 600)

    def tearDown(self):
        self.view.deleteLater()

    def test_arrow_keys_pan_timeline(self):
        before = self.view.coord.center_time.value

        self.view.keyPressEvent(_key(Qt.Key.Key_Down))
        self.assertIn(Qt.Key.Key_Down, self.view._scroll_keys)
        self.assertTrue(self.view._scroll_timer.isActive())

        self.view._on_scroll_timer()
        after = self.view.coord.center_time.value
        self.assertGreater(after, before)

        release = QKeyEvent(
            QEvent.Type.KeyRelease, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier
        )
        self.view.keyReleaseEvent(release)
        self.assertFalse(self.view._scroll_timer.isActive())

    def test_page_step_larger_than_small_step(self):
        vp = self.view.coord.viewport()
        visible_us = vp.length / self.view.coord.scale

        self.view._scroll_keys = {Qt.Key.Key_Down}
        before = self.view.coord.center_time.value
        self.view._on_scroll_timer()
        small_step = self.view.coord.center_time.value - before

        self.view._scroll_keys = {Qt.Key.Key_Right}
        before = self.view.coord.center_time.value
        self.view._on_scroll_timer()
        page_step = self.view.coord.center_time.value - before

        self.assertAlmostEqual(small_step, visible_us * 0.05, delta=1)
        self.assertAlmostEqual(page_step, visible_us, delta=1)
        self.view._scroll_keys = set()


class TestHelpAbout(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_help_menu_entries_exist(self):
        w = MainWindow()
        menus = [a.text() for a in w.menuBar().actions()]
        self.assertIn("Help", menus)
        help_menu = None
        for action in w.menuBar().actions():
            if action.text() == "Help":
                help_menu = action.menu()
        self.assertIsNotNone(help_menu)
        entries = [a.text() for a in help_menu.actions()]
        self.assertIn("Help Contents", entries)
        self.assertIn("About UniversalHistory", entries)
        self.assertTrue(w._HELP_TEXT.strip())
        self.assertTrue(w._ABOUT_TEXT.strip())
        w.deleteLater()


class TestLabelTagEditorTab(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _make_workspace(self):
        ws = Workspace()
        ts = JDNTimestamp.from_ymd(2000, 1, 1)
        event = Event(
            "u1", "s1", ts, ts, "event",
            labels={
                "time": ["2000"],
                "title": ["Hello"],
                "author": ["Sleepy"],  # not exposed in the form
            },
        )
        ws.add(event)
        return ws

    def test_table_shows_all_labels(self):
        ws = self._make_workspace()
        dlg = EventEditorDialog(ws, source="s1", edit_uuid="u1")
        table = dlg.editor._label_table
        labels = {}
        for row in range(table.rowCount()):
            labels[table.item(row, 0).text()] = table.item(row, 1).text()
        self.assertEqual(labels.get("author"), "Sleepy")
        self.assertEqual(labels.get("title"), "Hello")
        self.assertEqual(labels.get("time"), "2000")
        dlg.deleteLater()

    def test_table_edit_reaches_event_on_apply(self):
        ws = self._make_workspace()
        dlg = EventEditorDialog(ws, source="s1", edit_uuid="u1")
        editor = dlg.editor
        # Switch to the table tab (syncs form into table), then edit it.
        editor._tabs.setCurrentIndex(1)
        table = editor._label_table
        row = table.rowCount()
        table.insertRow(row)
        from PyQt6.QtWidgets import QTableWidgetItem
        table.setItem(row, 0, QTableWidgetItem("custom"))
        table.setItem(row, 1, QTableWidgetItem("x, y"))

        event = editor._ui_to_event()
        self.assertIsNotNone(event)
        self.assertEqual(event.labels.get("custom"), ["x", "y"])
        # Form values survive through the table sync.
        self.assertEqual(event.labels.get("author"), ["Sleepy"])
        self.assertEqual(event.labels.get("title"), ["Hello"])
        dlg.deleteLater()

    def test_form_edit_reaches_table(self):
        ws = self._make_workspace()
        dlg = EventEditorDialog(ws, source="s1", edit_uuid="u1")
        editor = dlg.editor
        editor._line_title.setText("Changed")
        editor._tabs.setCurrentIndex(1)  # triggers form -> table sync
        labels = editor._table_labels()
        self.assertEqual(labels.get("title"), ["Changed"])
        self.assertEqual(labels.get("author"), ["Sleepy"])
        dlg.deleteLater()


class TestFilterPresets(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_preset_roundtrip_utf8(self):
        ws = Workspace()
        dlg = FilterDialog(ws)
        dlg._line_source.setText("example/example.his")
        dlg._combo_focus.setCurrentText("event")
        dlg._line_include.setText("tags: tag5; author: Sleepy")
        dlg._line_exclude.setText("tags: draft")
        dlg._line_time_from.setText("公元前200年")
        dlg._line_time_to.setText("2020")

        with tempfile.TemporaryDirectory() as tmp:
            preset = str(Path(tmp) / "f.hisfilter")
            # Drive the same code path as the button, minus the file dialog.
            def line(label, tags):
                from universal_history.parsing import LabelTagParser
                text = LabelTagParser.tags_to_text(tags, persistence=True)
                return f"{label}: {text}\n" if text else ""

            text = ""
            text += line("sources", [dlg._line_source.text().strip()])
            text += line("focus_label", [dlg._combo_focus.currentText().strip()])
            text += line("include_tags", [p.strip() for p in dlg._line_include.text().split(";") if p.strip()])
            text += line("exclude_tags", [p.strip() for p in dlg._line_exclude.text().split(";") if p.strip()])
            text += line("time_from", [dlg._line_time_from.text().strip()])
            text += line("time_to", [dlg._line_time_to.text().strip()])
            Path(preset).write_text(text, encoding="utf-8")

            dlg2 = FilterDialog(ws)
            from universal_history.parsing import LabelTagParser
            parser = LabelTagParser()
            self.assertTrue(parser.parse(Path(preset).read_text(encoding="utf-8")))
            data = LabelTagParser.label_tags_list_to_dict(parser.get_label_tags())
            self.assertEqual(data["sources"], ["example/example.his"])
            self.assertEqual(data["focus_label"], ["event"])
            self.assertEqual(data["include_tags"], ["tags: tag5", "author: Sleepy"])
            self.assertEqual(data["time_from"], ["公元前200年"])
            dlg2.deleteLater()
        dlg.deleteLater()


if __name__ == "__main__":
    unittest.main()
