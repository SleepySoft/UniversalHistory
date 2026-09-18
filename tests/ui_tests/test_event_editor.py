import unittest
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from universal_history.models import Workspace
from universal_history.ui import EventEditor


class TestEventEditorModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.workspace = Workspace()
        self.editor = EventEditor(self.workspace, source="test.his")

    def test_build_event_with_location_focus(self):
        self.editor._line_time.setText("2020")
        self.editor._line_location.setText("Shanghai")
        self.editor._line_people.setText("Alice, Bob")
        self.editor._line_organization.setText("Org1")
        self.editor._line_tags.setText("tag1, tag2")
        self.editor._line_title.setText("Title")
        self.editor._text_brief.setPlainText("Brief text")
        self.editor._text_event.setPlainText("Event text")
        self.editor._radio_location.setChecked(True)

        event = self.editor._ui_to_event()
        self.assertIsNotNone(event)
        self.assertEqual(event.focus_label, "location")
        self.assertIn("Shanghai", event.labels.get("location", []))
        self.assertEqual(event.labels.get("people"), ["Alice", "Bob"])
        self.assertEqual(event.labels.get("tags"), ["tag1", "tag2"])
        self.assertEqual(event.title(), "Title")
        self.assertEqual(event.brief(), "Brief text")
        self.assertEqual(event.event_text(), "Event text")

    def test_location_focus_requires_location(self):
        self.editor._line_time.setText("2020")
        self.editor._line_location.setText("")
        self.editor._radio_location.setChecked(True)

        # Patch away the modal message box so the test can run headless.
        with patch("universal_history.ui.editor.QMessageBox.information", lambda *a, **k: None):
            event = self.editor._ui_to_event()
        self.assertIsNone(event)

    def test_apply_preserves_unexposed_labels(self):
        """Regression: Apply must not drop labels the UI does not expose
        (author, custom labels). See spec/how/98-known-issues.md #26."""
        from universal_history.models import Event

        event = Event(
            uuid="u1",
            source="test.his",
            since=None,
            until=None,
            focus_label="event",
            labels={
                "author": ["historian"],
                "custom_label": ["keep-me"],
                "time": ["2020"],
                "title": ["Old title"],
            },
        )
        self.editor._current_event = event
        self.editor._event_to_ui(event)
        self.editor._line_title.setText("New title")

        new_event = self.editor._ui_to_event()
        self.assertIsNotNone(new_event)
        self.assertEqual(new_event.labels.get("author"), ["historian"])
        self.assertEqual(new_event.labels.get("custom_label"), ["keep-me"])
        self.assertEqual(new_event.title(), "New title")

    def test_clearing_ui_field_removes_label(self):
        """Explicitly cleared UI-exposed fields are removed, not kept stale."""
        from universal_history.models import Event

        event = Event(
            uuid="u2",
            source="test.his",
            since=None,
            until=None,
            focus_label="event",
            labels={"time": ["2020"], "title": ["T"], "location": ["Paris"]},
        )
        self.editor._current_event = event
        self.editor._event_to_ui(event)
        self.editor._line_location.setText("")

        new_event = self.editor._ui_to_event()
        self.assertIsNotNone(new_event)
        self.assertNotIn("location", new_event.labels)


class TestEventEditorDirtyFlag(unittest.TestCase):
    """Dirty flag + unsaved-changes prompt (decision 2026-09-18,
    spec/how/98-known-issues.md #28)."""

    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.workspace = Workspace()
        self.editor = EventEditor(self.workspace, source="test.his")

    def test_clean_after_new_record_and_dirty_after_edit(self):
        self.assertFalse(self.editor.is_dirty())
        self.editor._line_title.setText("Something")
        self.assertTrue(self.editor.is_dirty())

    def test_confirm_returns_true_when_clean(self):
        with patch("universal_history.ui.editor.QMessageBox.question") as q:
            self.assertTrue(self.editor.confirm_discard_or_save())
            q.assert_not_called()

    def test_discard_proceeds(self):
        self.editor._line_title.setText("Draft")
        with patch(
            "universal_history.ui.editor.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Discard,
        ):
            self.assertTrue(self.editor.confirm_discard_or_save())

    def test_cancel_blocks(self):
        self.editor._line_title.setText("Draft")
        with patch(
            "universal_history.ui.editor.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Cancel,
        ):
            self.assertFalse(self.editor.confirm_discard_or_save())
        # Still dirty afterwards.
        self.assertTrue(self.editor.is_dirty())

    def test_save_applies_and_clears_dirty(self):
        self.editor._line_time.setText("2020")
        self.editor._line_title.setText("Saved title")
        with patch(
            "universal_history.ui.editor.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Save,
        ), patch.object(self.editor, "_save_source", lambda: None):
            self.assertTrue(self.editor.confirm_discard_or_save())
        self.assertFalse(self.editor.is_dirty())
        saved = self.workspace.get_by_uuid(self.editor._current_event.uuid)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.title(), "Saved title")

    def test_record_switch_reverts_on_cancel(self):
        from universal_history.models import Event

        for uid, title in (("r1", "First"), ("r2", "Second")):
            self.workspace.add(
                Event(
                    uuid=uid,
                    source="test.his",
                    since=None,
                    until=None,
                    focus_label="event",
                    labels={"time": ["2020"], "title": [title]},
                )
            )
        self.editor._refresh_record_list()
        self.editor._load_event("r1")
        self.assertEqual(self.editor._current_event.uuid, "r1")

        # Dirty the form, then try to switch to r2 but cancel the prompt.
        self.editor._line_title.setText("Unsaved edit")
        with patch(
            "universal_history.ui.editor.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Cancel,
        ):
            index = self.editor._combo_records.findData("r2")
            self.assertGreaterEqual(index, 0)
            self.editor._combo_records.setCurrentIndex(index)

        self.assertEqual(self.editor._current_event.uuid, "r1")
        self.assertEqual(
            self.editor._combo_records.currentData(), "r1"
        )


if __name__ == "__main__":
    unittest.main()
