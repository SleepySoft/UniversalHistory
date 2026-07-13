"""
Filter dialog for UniversalHistory.

Provides a simple UI to query the Workspace by source, focus label, tag
include/exclude, and time range.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QVBoxLayout,
    QPushButton, QLabel, QMessageBox,
)

from universal_history.chrono import parse_time_text
from universal_history.models import Event, EventIndex, Workspace


class FilterDialog(QDialog):
    """
    Dialog to build a filter and emit the resulting EventIndex list.
    """

    filter_applied = pyqtSignal(list)  # List[EventIndex]

    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filter Events")
        self.resize(500, 300)

        self._workspace = workspace

        self._line_source = QLineEdit()
        self._combo_focus = QComboBox()
        self._combo_focus.setEditable(True)
        self._combo_focus.addItems(["", "time", "location", "people", "organization", "event"])

        self._line_include = QLineEdit()
        self._line_include.setPlaceholderText("tags: tag5; author: Sleepy")
        self._line_exclude = QLineEdit()
        self._line_exclude.setPlaceholderText("tags: draft")

        self._line_time_from = QLineEdit()
        self._line_time_from.setPlaceholderText("e.g. 2000")
        self._line_time_to = QLineEdit()
        self._line_time_to.setPlaceholderText("e.g. 2020")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_apply)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("Source", self._line_source)
        form.addRow("Focus Label", self._combo_focus)
        form.addRow("Include Labels", self._line_include)
        form.addRow("Exclude Labels", self._line_exclude)
        form.addRow("Time From", self._line_time_from)
        form.addRow("Time To", self._line_time_to)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _on_apply(self):
        sources = None
        source_text = self._line_source.text().strip()
        if source_text:
            sources = [source_text]

        focus = self._combo_focus.currentText().strip() or None

        include_labels = self._parse_label_text(self._line_include.text())
        exclude_labels = self._parse_label_text(self._line_exclude.text())

        time_range = self._parse_time_range()
        if time_range is False:
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
        from_text = self._line_time_from.text().strip()
        to_text = self._line_time_to.text().strip()

        since = None
        until = None
        if from_text:
            since, _, _ = parse_time_text(from_text)
            if since is None:
                QMessageBox.information(self, "Parse Error", f"Cannot parse time: {from_text}")
                return False
        if to_text:
            until, _, _ = parse_time_text(to_text)
            if until is None:
                QMessageBox.information(self, "Parse Error", f"Cannot parse time: {to_text}")
                return False

        if since is None and until is None:
            return None
        if since is None:
            since = until
        if until is None:
            until = since
        return (since, until)
