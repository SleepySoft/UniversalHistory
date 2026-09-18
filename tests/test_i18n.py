import unittest

from PyQt6.QtWidgets import QApplication

from universal_history.i18n import (
    JsonTranslator,
    available_languages,
    install_translator,
    load_translator,
    resolve_language,
)


class TestJsonTranslator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance() or QApplication([])

    def test_lookup_hit_and_miss(self):
        translator = JsonTranslator({"File": "文件"})
        self.assertEqual(translator.translate("MainWindow", "File"), "文件")
        self.assertFalse(translator.translate("MainWindow", "Missing"))

    def test_english_never_installs(self):
        self.assertIsNone(load_translator("en"))
        self.assertIsNone(load_translator("en_US"))
        self.assertEqual(install_translator(self._app, "en"), [])

    def test_unknown_language_returns_none(self):
        self.assertIsNone(load_translator("xx_YY"))

    def test_zh_cn_translation_active(self):
        installed = install_translator(self._app, "zh_CN")
        self.assertTrue(installed)
        self.assertEqual(self._app.translate("MainWindow", "File"), "文件")
        for translator in installed:
            self._app.removeTranslator(translator)

    def test_language_prefix_fallback(self):
        # zh_TW has no file; prefix 'zh' has none either -> None.
        self.assertIsNone(load_translator("zh_TW"))
        # zh_CN exists directly.
        self.assertIsNotNone(load_translator("zh_CN"))

    def test_resolve_language_prefers_explicit(self):
        self.assertEqual(resolve_language("zh_CN"), "zh_CN")

    def test_available_languages(self):
        langs = available_languages()
        self.assertIn("en", langs)
        self.assertIn("zh_CN", langs)


if __name__ == "__main__":
    unittest.main()
