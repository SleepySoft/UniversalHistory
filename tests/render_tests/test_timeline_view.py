import unittest

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render import TimelineView


class TestTimelineView(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def test_can_instantiate_and_add_thread(self):
        view = TimelineView()
        view.resize(800, 600)

        events = [
            EventIndex("a", "test", JDNTimestamp.from_ymd(2000, 1, 1),
                       JDNTimestamp.from_ymd(2000, 1, 1), "Point event"),
            EventIndex("b", "test", JDNTimestamp.from_ymd(2000, 3, 1),
                       JDNTimestamp.from_ymd(2000, 9, 1), "Period event"),
        ]
        thread = view.add_thread(events, align="right")
        self.assertIsNotNone(thread)
        self.assertEqual(len(thread.items), 2)

        # Toggle orientation should not crash.
        view.toggle_orientation()
        self.assertTrue(view.coord.is_vertical)

        # Cleanup to avoid leaking widgets in batch tests.
        view.deleteLater()


if __name__ == "__main__":
    unittest.main()
