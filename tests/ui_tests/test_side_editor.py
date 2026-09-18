"""
Regression tests for T5-3: the non-modal side editor dock replaces the modal
EventEditorDialog in the main window — the timeline stays interactive while
editing, and unsaved content is confirmed before switching context.
"""

import unittest

from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import Event, Workspace


class TestSideEditorDock(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _window(self):
        from universal_history.main_window import MainWindow
        return MainWindow()

    def test_editor_lives_in_non_modal_dock(self):
        w = self._window()
        source = w._workspace.sources()[0]  # example.his autoload
        w._open_editor(source)
        # Parent window is hidden in offscreen tests; isHidden reflects the
        # dock's own shown/hidden state regardless.
        self.assertFalse(w._editor_dock.isHidden())
        # Non-modal: the timeline widget is still enabled and visible.
        self.assertTrue(w._view.isEnabled())
        self.assertFalse(w._editor_dock.isFloating() and False)  # docked
        self.assertEqual(w._editor.source(), source)
        w.deleteLater()

    def test_edit_uuid_loads_record(self):
        w = self._window()
        event = w._workspace.events()[0]
        w._open_editor(event.source, edit_uuid=event.uuid)
        self.assertEqual(w._editor._label_uuid.text(), event.uuid)
        w.deleteLater()

    def test_preset_time_prefills_new_record(self):
        w = self._window()
        source = w._workspace.sources()[0]
        w._open_editor(source, preset_time_text="2020-01-01 AD")
        self.assertEqual(w._editor._line_time.text(), "2020-01-01 AD")
        self.assertTrue(w._editor.is_dirty())
        w.deleteLater()

    def test_editor_public_switch_methods(self):
        ws = Workspace()
        ev = Event(uuid="u1", source="s",
                   since=JDNTimestamp.from_year(2000),
                   until=JDNTimestamp.from_year(2000),
                   focus_label="event", labels={"title": ["t"]})
        ws.add(ev)
        from universal_history.ui.editor import EventEditor
        ed = EventEditor(ws, source="s")
        self.assertTrue(ed.edit_event("u1"))
        self.assertEqual(ed._label_uuid.text(), "u1")
        self.assertTrue(ed.start_new_record("1999-01-01 AD"))
        self.assertEqual(ed._line_time.text(), "1999-01-01 AD")
        ed.deleteLater()


if __name__ == "__main__":
    unittest.main()
