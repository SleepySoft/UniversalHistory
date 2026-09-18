"""
Filter dialog for UniversalHistory.

Provides a simple UI to query the Workspace by source, focus label, tag
include/exclude, and time range.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QVBoxLayout, QPushButton, QLabel, QMessageBox,
)

from universal_history.chrono import parse_time_text
from universal_history.models import Event, EventIndex, Workspace
from universal_history.parsing import HistoryRecordLoader, LabelTagParser


class FilterDialog(QDialog):
    """
    Dialog to build a filter and emit the resulting EventIndex list.
    """

    filter_applied = pyqtSignal(list)  # List[EventIndex]

    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Filter Events"))
        self.resize(500, 300)

        self._workspace = workspace

        self._line_source = QLineEdit()
        self._combo_focus = QComboBox()
        self._combo_focus.setEditable(True)
        self._combo_focus.addItems(["", "time", "location", "people", "organization", "event"])

        self._line_include = QLineEdit()
        self._line_include.setPlaceholderText(self.tr("tags: tag5; author: Sleepy"))
        self._line_exclude = QLineEdit()
        self._line_exclude.setPlaceholderText(self.tr("tags: draft"))

        self._line_time_from = QLineEdit()
        self._line_time_from.setPlaceholderText(self.tr("e.g. 2000"))
        self._line_time_to = QLineEdit()
        self._line_time_to.setPlaceholderText(self.tr("e.g. 2020"))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_apply)
        buttons.rejected.connect(self.reject)

        # Filter presets (.hisfilter), restored from the legacy filter editor
        # (legacy defects #42/#45: utf-8 encoding + UI feedback).
        preset_line = QHBoxLayout()
        self._btn_save_preset = QPushButton(self.tr("Save Preset..."))
        self._btn_load_preset = QPushButton(self.tr("Load Preset..."))
        self._btn_save_preset.clicked.connect(self._on_save_preset)
        self._btn_load_preset.clicked.connect(self._on_load_preset)
        preset_line.addWidget(self._btn_save_preset)
        preset_line.addWidget(self._btn_load_preset)
        preset_line.addStretch()

        form = QFormLayout()
        form.addRow(self.tr("Source"), self._line_source)
        form.addRow(self.tr("Focus Label"), self._combo_focus)
        form.addRow(self.tr("Include Labels"), self._line_include)
        form.addRow(self.tr("Exclude Labels"), self._line_exclude)
        form.addRow(self.tr("Time From"), self._line_time_from)
        form.addRow(self.tr("Time To"), self._line_time_to)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(preset_line)
        layout.addWidget(buttons)

    def _on_apply(self):
        sources = None
        source_text = self._line_source.text().strip()
        if source_text:
            sources = [source_text]

        focus = self._combo_focus.currentText().strip() or None

        include_labels = self._parse_label_text(self._line_include.text())
        exclude_labels = self._parse_label_text(self._line_exclude.text())

        try:
            time_range = self._parse_time_range()
        except ValueError as e:
            QMessageBox.information(self, self.tr("Parse Error"), str(e))
            return

        results = self._workspace.select(
            sources=sources,
            focus_label=focus,
            include_labels=include_labels or None,
            exclude_labels=exclude_labels or None,
            time_range=time_range,
        )

        self.filter_applied.emit([e.to_index() for e in results])
        self.accept()

    def _parse_label_text(self, text: str) -> Optional[Dict[str, List[str]]]:
        text = text.strip()
        if not text:
            return None
        result: Dict[str, List[str]] = {}
        parts = [p.strip() for p in text.split(";") if p.strip()]
        for part in parts:
            if ":" not in part:
                continue
            label, tags_text = part.split(":", 1)
            tags = [t.strip() for t in tags_text.split(",") if t.strip()]
            if tags:
                result[label.strip()] = tags
        return result or None

    def _parse_time_range(self):
        """Return None (no time filter) or ``(since, until)`` where either end
        may be None for an open-ended range. Raises ValueError on bad input.
        """
        from_text = self._line_time_from.text().strip()
        to_text = self._line_time_to.text().strip()

        since = None
        until = None
        if from_text:
            since, _, _ = parse_time_text(from_text)
            if since is None:
                raise ValueError(f"Cannot parse time: {from_text}")
        if to_text:
            until, _, _ = parse_time_text(to_text)
            if until is None:
                raise ValueError(f"Cannot parse time: {to_text}")

        if since is None and until is None:
            return None
        return (since, until)

    # ------------------------------------------------------------------
    # Filter presets (.hisfilter)
    # ------------------------------------------------------------------

    _PRESET_FILTER = "History Filter Files (*.hisfilter)"

    def _on_save_preset(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Filter Preset"),
            str(HistoryRecordLoader.get_local_depot_root()),
            self._PRESET_FILTER,
        )
        if not path:
            return

        # LabelTag format, compatible with the legacy .hisfilter layout
        # (sources / focus_label / include_tags / exclude_tags), plus the
        # new time range fields. Always utf-8 (legacy defect #42).
        def line(label: str, tags: List[str]) -> str:
            text = LabelTagParser.tags_to_text(tags, persistence=True)
            return f"{label}: {text}\n" if text else ""

        source = self._line_source.text().strip()
        include = [p.strip() for p in self._line_include.text().split(";") if p.strip()]
        exclude = [p.strip() for p in self._line_exclude.text().split(";") if p.strip()]

        text = ""
        text += line("sources", [source] if source else [])
        text += line("focus_label", [self._combo_focus.currentText().strip()])
        text += line("include_tags", include)
        text += line("exclude_tags", exclude)
        text += line("time_from", [self._line_time_from.text().strip()])
        text += line("time_to", [self._line_time_to.text().strip()])

        try:
            Path(path).write_text(text, encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(self, self.tr("Save Failed"), str(e))

    def _on_load_preset(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Load Filter Preset"),
            str(HistoryRecordLoader.get_local_depot_root()),
            self._PRESET_FILTER,
        )
        if not path:
            return

        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(self, self.tr("Load Failed"), str(e))
            return

        parser = LabelTagParser()
        if not parser.parse(text):
            QMessageBox.warning(
                self, self.tr("Load Failed"),
                self.tr("Invalid filter preset file: %1").replace("%1", path),
            )
            return

        data = LabelTagParser.label_tags_list_to_dict(parser.get_label_tags())

        def first(label: str) -> str:
            tags = data.get(label, [])
            return tags[0] if tags else ""

        self._line_source.setText(first("sources"))
        self._combo_focus.setCurrentText(first("focus_label"))
        self._line_include.setText("; ".join(data.get("include_tags", [])))
        self._line_exclude.setText("; ".join(data.get("exclude_tags", [])))
        self._line_time_from.setText(first("time_from"))
        self._line_time_to.setText(first("time_to"))
