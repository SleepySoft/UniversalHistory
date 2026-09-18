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

    def test_parse_time_range_open_ended(self):
        """Single-end input yields an open range, not a point interval (#31)."""
        self.dialog._line_time_from.setText("2000")
        since, until = self.dialog._parse_time_range()
        self.assertIsNotNone(since)
        self.assertIsNone(until)

        self.dialog._line_time_from.setText("")
        self.dialog._line_time_to.setText("2020")
        since, until = self.dialog._parse_time_range()
        self.assertIsNone(since)
        self.assertIsNotNone(until)

    def test_parse_time_range_invalid_raises(self):
        from unittest.mock import patch

        self.dialog._line_time_from.setText("@@@not-a-time@@@")
        self.assertRaises(ValueError, self.dialog._parse_time_range)


class TestOpenRangeSelect(unittest.TestCase):
    """Workspace.select must treat None range ends as unbounded (#31)."""

    def test_open_ended_ranges(self):
        from universal_history.chrono.jdn_timestamp import JDNTimestamp
        from universal_history.models import Event, Workspace

        ws = Workspace()
        for uid, year in (("e1990", 1990), ("e2010", 2010), ("e2030", 2030)):
            ws.add(Event(
                uuid=uid,
                source="s",
                since=JDNTimestamp.from_year(year),
                until=JDNTimestamp.from_year(year),
                focus_label="event",
                labels={"time": [str(year)]},
            ))

        after_2000 = ws.select(time_range=(JDNTimestamp.from_year(2000), None))
        self.assertEqual({e.uuid for e in after_2000}, {"e2010", "e2030"})

        before_2020 = ws.select(time_range=(None, JDNTimestamp.from_year(2020)))
        self.assertEqual({e.uuid for e in before_2020}, {"e1990", "e2010"})


if __name__ == "__main__":
    unittest.main()
