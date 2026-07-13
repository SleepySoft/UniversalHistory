import unittest
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

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


if __name__ == "__main__":
    unittest.main()
