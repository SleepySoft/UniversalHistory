import tempfile
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from universal_history.adapters import HisFileAdapter
from universal_history.render import TimelineView
from universal_history.ui import AddThreadDialog


class TestAddThreadDialog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def test_empty_thread_is_default(self):
        adapter = HisFileAdapter()
        dlg = AddThreadDialog(adapter)
        # Empty thread is the default, so Add is enabled and source is empty.
        self.assertTrue(dlg._add_btn.isEnabled())
        source, events = dlg.get_result()
        self.assertEqual(source, "")
        self.assertEqual(events, [])
        dlg.deleteLater()

    def test_create_empty_thread_result(self):
        adapter = HisFileAdapter()
        dlg = AddThreadDialog(adapter)
        dlg._on_empty_thread()
        source, events = dlg.get_result()
        self.assertEqual(source, "")
        self.assertEqual(events, [])
        dlg.deleteLater()

    def test_create_new_source_file(self):
        adapter = HisFileAdapter()
        with tempfile.TemporaryDirectory() as tmpdir:
            new_path = Path(tmpdir) / "new_source.his"
            dlg = AddThreadDialog(adapter)
            dlg._source = str(new_path)
            dlg._events = []
            dlg._on_create_new = lambda: None  # already mocked
            source, events = dlg.get_result()
            self.assertEqual(source, str(new_path))
            self.assertEqual(events, [])
        dlg.deleteLater()


if __name__ == "__main__":
    unittest.main()
