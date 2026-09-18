"""Dialog for adding a new timeline thread."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from universal_history.adapters import HisFileAdapter
from universal_history.models import Event, EventIndex


class AddThreadDialog(QDialog):
    """
    Choose how to populate a new timeline thread:
    - load an existing .his file
    - create a new empty .his source file
    - create an empty thread with no source (records added later via editor)
    """

    def __init__(
        self,
        adapter: HisFileAdapter,
        side: str = "right",
        parent=None,
    ):
        super().__init__(parent)
        self._adapter = adapter
        self._side = side
        self.setWindowTitle(self.tr("Add Thread"))
        self.resize(550, 180)

        self._source: Optional[str] = None
        self._events: List[Event] = []

        self._build_ui()
        # Default to an empty thread so the user can just click Add.
        self._on_empty_thread()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(self.tr("New thread will be added on the %1 side.").replace("%1", self._side)))

        # Source path display
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel(self.tr("Source:")))
        self._source_edit = QLineEdit()
        self._source_edit.setReadOnly(True)
        self._source_edit.setPlaceholderText(self.tr("No source selected"))
        source_layout.addWidget(self._source_edit)
        layout.addLayout(source_layout)

        # Buttons
        btn_layout = QHBoxLayout()

        load_btn = QPushButton(self.tr("Load existing file..."))
        load_btn.setAutoDefault(False)
        load_btn.clicked.connect(self._on_load_existing)
        btn_layout.addWidget(load_btn)

        new_btn = QPushButton(self.tr("Create new source file..."))
        new_btn.setAutoDefault(False)
        new_btn.clicked.connect(self._on_create_new)
        btn_layout.addWidget(new_btn)

        empty_btn = QPushButton(self.tr("Empty thread"))
        empty_btn.setAutoDefault(False)
        empty_btn.clicked.connect(self._on_empty_thread)
        btn_layout.addWidget(empty_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        # Dialog buttons
        dialog_btn_layout = QHBoxLayout()
        self._add_btn = QPushButton(self.tr("Add"))
        self._add_btn.setDefault(True)
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        dialog_btn_layout.addStretch()
        dialog_btn_layout.addWidget(self._add_btn)
        dialog_btn_layout.addWidget(cancel_btn)
        layout.addLayout(dialog_btn_layout)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_load_existing(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open History File"),
            str(self._adapter.depot_root),
            self.tr("History Files (*.his)"),
        )
        if not path:
            return
        try:
            events = self._adapter.load_file(path)
            self._source = events[0].source if events else path
            self._events = events
            self._source_edit.setText(self._source)
            self._add_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Load Failed"), str(e))

    def _on_create_new(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Create New History Source File"),
            str(self._adapter.depot_root),
            self.tr("History Files (*.his)"),
        )
        if not path:
            return
        try:
            # Ensure the file exists and is a valid empty .his file.
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text("", encoding="utf-8")
            self._source = path
            self._events = []
            self._source_edit.setText(self._source)
            self._add_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Create Failed"), str(e))

    def _on_empty_thread(self) -> None:
        self._source = ""
        self._events = []
        self._source_edit.setText(self.tr("(empty thread)"))
        self._add_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def get_result(self) -> Tuple[str, List[Event]]:
        """Return (source, events) for the new thread.

        NOTE: do not override QDialog.result() because QDialog.exec() relies on
        the integer Accepted/Rejected code returned by that method.
        """
        return self._source or "", list(self._events)
