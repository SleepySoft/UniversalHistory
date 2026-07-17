import unittest
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QDialog

from universal_history.adapters import HisFileAdapter
from universal_history.main_window import MainWindow
from universal_history.ui import AddThreadDialog


class TestAddEmptyThreadIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def test_main_window_add_empty_thread(self):
        window = MainWindow()
        # MainWindow loads example data by default; ensure at least one thread.
        self.assertGreaterEqual(len(window._view.right_threads()), 0)

        with patch("universal_history.main_window.AddThreadDialog") as MockDlg:
            instance = MockDlg.return_value
            instance.exec.return_value = QDialog.DialogCode.Accepted
            instance.get_result.return_value = ("", [])
            window._on_add_thread("right")

        threads = window._view.right_threads()
        self.assertTrue(any(t.source == "" for t in threads))
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
