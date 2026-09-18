"""
Minimal i18n support for UniversalHistory.

User-visible strings are written in English (the source language) and wrapped
in ``QObject.tr()`` / ``QApplication.translate()``. Translations live as JSON
files under ``universal_history/translations/<lang>.json``, mapping the
English source text to the translated text (see ``zh_CN.json``).

A custom QTranslator subclass is used instead of Qt Linguist ``.qm`` files so
the project does not depend on the lupdate/lrelease toolchain. Standard Qt
button texts (Save/Discard/Cancel/...) are translated by loading Qt's own
``qtbase_<lang>.qm`` catalog when available.

Language resolution order: explicit argument > ``UH_LANGUAGE`` environment
variable > system locale. English (the source language) never installs a
translator.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import QLibraryInfo, QLocale, QTranslator

_TRANSLATIONS_DIR = Path(__file__).resolve().parent / "translations"
SOURCE_LANGUAGE = "en"


class JsonTranslator(QTranslator):
    """QTranslator backed by a flat ``{sourceText: translation}`` dict."""

    def __init__(self, translations: Dict[str, str], parent=None):
        super().__init__(parent)
        self._translations = translations

    def translate(self, context, sourceText, disambiguation=None, n=-1):
        return self._translations.get(sourceText) or None


def available_languages() -> List[str]:
    """Languages with a translation file (always includes the source 'en')."""
    langs = [SOURCE_LANGUAGE]
    if _TRANSLATIONS_DIR.is_dir():
        langs += sorted(p.stem for p in _TRANSLATIONS_DIR.glob("*.json"))
    return langs


def resolve_language(requested: Optional[str] = None) -> str:
    """Pick the effective language code."""
    if requested:
        return requested
    env = os.environ.get("UH_LANGUAGE", "").strip()
    if env:
        return env
    return QLocale.system().name()


def load_translator(language: str, parent=None) -> Optional[JsonTranslator]:
    """Build a translator for `language`; None for source/unknown languages."""
    if not language or language.startswith(SOURCE_LANGUAGE):
        return None
    candidates = [language]
    if "_" in language:
        candidates.append(language.split("_", 1)[0])
    for name in candidates:
        path = _TRANSLATIONS_DIR / f"{name}.json"
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return JsonTranslator(data, parent)
    return None


def _load_qt_base_translator(language: str, parent=None) -> Optional[QTranslator]:
    """Load Qt's own catalog (translates standard dialog buttons etc.)."""
    qt_translator = QTranslator(parent)
    for name in (language, language.split("_", 1)[0]):
        if qt_translator.load(
            f"qtbase_{name}",
            QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath),
        ):
            return qt_translator
    return None


def install_translator(app, language: Optional[str] = None) -> List[QTranslator]:
    """Resolve the language and install translators on `app`.

    Returns the list of installed translators (kept alive by their `app`
    parent). Empty list means the source language is in effect.
    """
    lang = resolve_language(language)
    installed: List[QTranslator] = []
    if not lang.startswith(SOURCE_LANGUAGE):
        qt_base = _load_qt_base_translator(lang, parent=app)
        if qt_base is not None:
            app.installTranslator(qt_base)
            installed.append(qt_base)
    app_translator = load_translator(lang, parent=app)
    if app_translator is not None:
        app.installTranslator(app_translator)
        installed.append(app_translator)
    return installed
