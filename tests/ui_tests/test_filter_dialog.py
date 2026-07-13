import unittest

from PyQt6.QtWidgets import QApplication

from universal_history.models import Workspace
from universal_history.ui import FilterDialog


class TestFilterDialogParsing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dialog = FilterDialog(Workspace())

    def test_parse_label_text_single_tag(self):
        result = self.dialog._parse_label_text("tags: tag5")
        self.assertEqual(result, {"tags": ["tag5"]})

    def test_parse_label_text_multiple_labels(self):
        result = self.dialog._parse_label_text("tags: tag5, draft; author: Sleepy")
        self.assertEqual(result, {"tags": ["tag5", "draft"], "author": ["Sleepy"]})

    def test_parse_label_text_empty(self):
        self.assertIsNone(self.dialog._parse_label_text(""))
        self.assertIsNone(self.dialog._parse_label_text("   "))

    def test_parse_time_range_both(self):
        self.dialog._line_time_from.setText("2000")
        self.dialog._line_time_to.setText("2020")
        since, until = self.dialog._parse_time_range()
        self.assertIsNotNone(since)
        self.assertIsNotNone(until)
        self.assertLessEqual(since, until)

    def test_parse_time_range_empty(self):
        self.assertIsNone(self.dialog._parse_time_range())


if __name__ == "__main__":
    unittest.main()
