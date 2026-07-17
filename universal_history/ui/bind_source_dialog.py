"""Dialog to bind a source file to a thread that currently has no source."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from universal_history.adapters import HisFileAdapter
from universal_history.models import Event


class BindSourceDialog(QDialog):
    """
    Choose a source file for an empty thread before adding records.
    """

    def __init__(self, adapter: HisFileAdapter, parent=None):
        super().__init__(parent)
        self._adapter = adapter
        self.setWindowTitle("Bind Source to Thread")
        self.resize(450, 140)

        self._source: Optional[str] = None
        self._events: List[Event] = []

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("This thread has no source file yet. Choose one to add records.")
        )

        btn_layout = QHBoxLayout()

        load_btn = QPushButton("Load existing file...")
        load_btn.clicked.connect(self._on_load_existing)
        btn_layout.addWidget(load_btn)

        new_btn = QPushButton("Create new source file...")
        new_btn.clicked.connect(self._on_create_new)
        btn_layout.addWidget(new_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _on_load_existing(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open History File",
            str(self._adapter.depot_root),
            "History Files (*.his)",
        )
        if not path:
            return
        try:
            self._events = self._adapter.load_file(path)
            self._source = self._events[0].source if self._events else path
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Load Failed", str(e))

    def _on_create_new(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New History Source File",
            str(self._adapter.depot_root),
            "History Files (*.his)",
        )
        if not path:
            return
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text("", encoding="utf-8")
            self._source = path
            self._events = []
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Create Failed", str(e))

    def get_result(self):
        """Return (source, events) chosen by the user.

        NOTE: do not override QDialog.result() because QDialog.exec() relies on
        the integer Accepted/Rejected code returned by that method.
        """
        return self._source or "", list(self._events)
