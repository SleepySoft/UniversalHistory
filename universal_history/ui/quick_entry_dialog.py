"""
Quick entry dialog (T5-4): create an event in one step from the timeline —
title + time (prefilled from the double-clicked axis position). Full field
editing stays in the EventEditor.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout,
)

from universal_history.chrono.time_utils import parse_time_text


class QuickEntryDialog(QDialog):
    """Minimal inline creation: Title + Time."""

    def __init__(self, preset_time_text: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Quick Entry"))
        self.setMinimumWidth(420)

        self._line_title = QLineEdit()
        self._line_title.setPlaceholderText(self.tr("Title"))
        self._line_time = QLineEdit(preset_time_text)
        self._error = QLabel("")
        self._error.setStyleSheet("color: #b91c1c;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow(self.tr("Title"), self._line_title)
        form.addRow(self.tr("Time"), self._line_time)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._error)
        layout.addWidget(buttons)

        self._line_title.setFocus()

    def _on_accept(self):
        title = self._line_title.text().strip()
        if not title:
            self._error.setText(self.tr("Title is required."))
            return
        since, until, _ = parse_time_text(self._line_time.text())
        if since is None or until is None:
            self._error.setText(
                self.tr("Time field is required and must be parseable.")
            )
            return
        self.accept()

    def get_result(self) -> Tuple[str, str]:
        """(title, time_text) — valid only after Accepted."""
        return self._line_title.text().strip(), self._line_time.text().strip()
