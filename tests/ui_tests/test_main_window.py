import unittest

from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.main_window import MainWindow


class TestMainWindowFilterDedup(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def test_filter_thread_is_reused(self):
        window = MainWindow()
        view = window._view

        indexes = [
            EventIndex("f1", "__filter__", JDNTimestamp.from_ymd(2000, 1, 1),
                       JDNTimestamp.from_ymd(2000, 1, 1), "Filter A"),
        ]

        window._on_filter_applied(indexes)
        filter_threads = [t for t in view.left_threads() + view.right_threads()
                          if t.source == "__filter__"]
        self.assertEqual(len(filter_threads), 1)
        first_thread = filter_threads[0]

        indexes2 = [
            EventIndex("f2", "__filter__", JDNTimestamp.from_ymd(2001, 1, 1),
                       JDNTimestamp.from_ymd(2001, 1, 1), "Filter B"),
        ]
        window._on_filter_applied(indexes2)
        filter_threads = [t for t in view.left_threads() + view.right_threads()
                          if t.source == "__filter__"]
        self.assertEqual(len(filter_threads), 1)
        self.assertIs(filter_threads[0], first_thread)
        self.assertEqual(len(filter_threads[0].events), 1)
        self.assertEqual(filter_threads[0].events[0].uuid, "f2")

        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
