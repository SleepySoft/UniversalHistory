"""
Event editor UI for UniversalHistory.

A fresh implementation based on the new Event model and JDNTimestamp, using
PyQt6. It is intentionally simpler than the old HistoryRecordEditor while
preserving the essential workflow.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QDateTime, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QRadioButton, QTextEdit, QVBoxLayout, QWidget, QFileDialog,
    QDateTimeEdit, QTabWidget,
)

from universal_history.adapters import HisFileAdapter
from universal_history.chrono import parse_time_text, format_jdn, jdn_to_qdatetime, qdatetime_to_jdn
from universal_history.models import Event, Workspace


class DateTimePickerDialog(QDialog):
    """Minimal date/time picker for in-range timestamps."""

    def __init__(self, initial: Optional[QDateTime] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pick Date & Time")
        self.resize(400, 120)

        self.picker = QDateTimeEdit()
        if initial is not None:
            self.picker.setDateTime(initial)
        self.picker.setCalendarPopup(True)
        self.picker.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.picker)
        layout.addWidget(buttons)

    def selected(self):
        return self.picker.dateTime()


class EventEditor(QWidget):
    """
    Widget for editing a single Event within a Workspace source.
    """

    event_saved = pyqtSignal(Event)
    event_deleted = pyqtSignal(str)  # uuid

    def __init__(
        self,
        workspace: Workspace,
        source: str = "",
        edit_uuid: str = "",
        parent=None,
    ):
        super().__init__(parent)

        self._workspace = workspace
        self._source = source
        self._current_event: Optional[Event] = None
        self._adapter = HisFileAdapter()

        # ------------------------------------------------------------------
        # Widgets
        # ------------------------------------------------------------------
        self._label_source = QLabel("No source")
        self._btn_open_file = QPushButton("Open File")
        self._btn_new_file = QPushButton("New File")

        self._combo_records = QComboBox()
        self._btn_new = QPushButton("New")
        self._btn_delete = QPushButton("Delete")

        self._label_uuid = QLabel()
        self._line_time = QLineEdit()
        self._btn_calendar = QPushButton("Calendar")
        self._check_lock_time = QCheckBox("Lock")

        self._radio_time = QRadioButton("Time")
        self._radio_location = QRadioButton("Location")
        self._radio_people = QRadioButton("People")
        self._radio_organization = QRadioButton("Organization")
        self._radio_event = QRadioButton("Event")
        self._radio_event.setChecked(True)

        self._line_location = QLineEdit()
        self._check_lock_location = QCheckBox("Lock")
        self._line_people = QLineEdit()
        self._check_lock_people = QCheckBox("Lock")
        self._line_organization = QLineEdit()
        self._check_lock_organization = QCheckBox("Lock")
        self._line_tags = QLineEdit()
        self._check_lock_tags = QCheckBox("Lock")

        self._line_title = QLineEdit()
        self._text_brief = QTextEdit()
        self._text_event = QTextEdit()

        self._btn_apply = QPushButton("Apply")
        self._btn_cancel = QPushButton("Cancel")

        # ------------------------------------------------------------------
        # Layout
        # ------------------------------------------------------------------
        root = QVBoxLayout(self)

        source_line = QHBoxLayout()
        source_line.addWidget(self._label_source, 1)
        source_line.addWidget(self._btn_open_file)
        source_line.addWidget(self._btn_new_file)
        root.addLayout(source_line)

        record_line = QHBoxLayout()
        record_line.addWidget(self._combo_records, 1)
        record_line.addWidget(self._btn_new)
        record_line.addWidget(self._btn_delete)
        root.addLayout(record_line)

        form = QFormLayout()
        form.addRow("UUID", self._label_uuid)

        time_layout = QHBoxLayout()
        time_layout.addWidget(self._radio_time)
        time_layout.addWidget(self._line_time, 1)
        time_layout.addWidget(self._btn_calendar)
        time_layout.addWidget(self._check_lock_time)
        form.addRow("Time", time_layout)

        loc_layout = QHBoxLayout()
        loc_layout.addWidget(self._radio_location)
        loc_layout.addWidget(self._line_location, 1)
        loc_layout.addWidget(self._check_lock_location)
        form.addRow("Location", loc_layout)

        ppl_layout = QHBoxLayout()
        ppl_layout.addWidget(self._radio_people)
        ppl_layout.addWidget(self._line_people, 1)
        ppl_layout.addWidget(self._check_lock_people)
        form.addRow("People", ppl_layout)

        org_layout = QHBoxLayout()
        org_layout.addWidget(self._radio_organization)
        org_layout.addWidget(self._line_organization, 1)
        org_layout.addWidget(self._check_lock_organization)
        form.addRow("Organization", org_layout)

        focus_layout = QHBoxLayout()
        focus_layout.addWidget(self._radio_event)
        focus_layout.addWidget(QLabel("Focus label"))
        form.addRow("Focus", focus_layout)

        tags_layout = QHBoxLayout()
        tags_layout.addWidget(self._line_tags, 1)
        tags_layout.addWidget(self._check_lock_tags)
        form.addRow("Tags", tags_layout)

        form.addRow("Title", self._line_title)
        form.addRow("Brief", self._text_brief)
        form.addRow("Event", self._text_event)

        root.addLayout(form)

        btn_line = QHBoxLayout()
        btn_line.addStretch()
        btn_line.addWidget(self._btn_apply)
        btn_line.addWidget(self._btn_cancel)
        root.addLayout(btn_line)

        # ------------------------------------------------------------------
        # Connections
        # ------------------------------------------------------------------
        self._btn_open_file.clicked.connect(self._on_open_file)
        self._btn_new_file.clicked.connect(self._on_new_file)
        self._combo_records.currentIndexChanged.connect(self._on_record_selected)
        self._btn_new.clicked.connect(self._on_new_record)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_apply.clicked.connect(self._on_apply)
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._btn_calendar.clicked.connect(self._on_pick_date)
        self._line_time.textChanged.connect(self._on_time_changed)

        # ------------------------------------------------------------------
        # Load initial state
        # ------------------------------------------------------------------
        self._refresh_record_list()
        if edit_uuid:
            self._load_event(edit_uuid)
        else:
            self._new_record()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_source(self, source: str) -> None:
        self._source = source
        self._refresh_record_list()
        self._new_record()

    def source(self) -> str:
        return self._source

    # ------------------------------------------------------------------
    # UI Event handlers
    # ------------------------------------------------------------------

    def _on_open_file(self):
        adapter = HisFileAdapter()
        root = adapter.depot_root
        path, _ = QFileDialog.getOpenFileName(
            self, "Open History File", str(root), "History Files (*.his)"
        )
        if path:
            events = self._adapter.load_file(path)
            self._workspace.load_events(events)
            self.set_source(events[0].source if events else path)

    def _on_new_file(self):
        adapter = HisFileAdapter()
        root = adapter.depot_root
        path, _ = QFileDialog.getSaveFileName(
            self, "New History File", str(root), "History Files (*.his)"
        )
        if path:
            Path(path).write_text("", encoding="utf-8")
            self.set_source(path)

    def _on_record_selected(self):
        if self._combo_records.count() == 0:
            return
        data = self._combo_records.currentData()
        if data is None:
            return
        if self._current_event and data == self._current_event.uuid:
            return
        self._load_event(data)

    def _on_new_record(self):
        self._new_record()

    def _on_delete(self):
        if self._current_event is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete event '{self._current_event.abstract(40)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            uuid = self._current_event.uuid
            self._workspace.remove(uuid)
            self._save_source()
            self.event_deleted.emit(uuid)
            self._refresh_record_list()
            self._new_record()

    def _on_apply(self):
        if not self._source:
            QMessageBox.information(
                self, "Source Required", "Please select or create a file first."
            )
            return

        event = self._ui_to_event()
        if event is None:
            return

        self._workspace.upsert(event)
        self._save_source()
        self.event_saved.emit(event)
        self._current_event = event
        self._refresh_record_list()
        self._select_uuid(event.uuid)

    def _on_cancel(self):
        self.window().close()

    def _on_pick_date(self):
        since, _, _ = parse_time_text(self._line_time.text())
        if since is None:
            QMessageBox.information(
                self, "No Time", "Enter a valid time first, then use the calendar."
            )
            return

        qdt = jdn_to_qdatetime(since)
        if qdt is None:
            QMessageBox.information(
                self, "Out of Range", "Calendar picker only supports years 1-9999."
            )
            return

        dlg = DateTimePickerDialog(qdt, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_jdn = qdatetime_to_jdn(dlg.selected())
            self._line_time.setText(format_jdn(new_jdn))

    def _on_time_changed(self):
        since, until, displays = parse_time_text(self._line_time.text())
        if since is not None:
            self._line_time.setToolTip("Parsed: " + "; ".join(displays))
        else:
            self._line_time.setToolTip("Cannot parse time")

    # ------------------------------------------------------------------
    # Data <-> UI
    # ------------------------------------------------------------------

    def _load_event(self, event_uuid: str):
        event = self._workspace.get_by_uuid(event_uuid)
        if event is None:
            return
        self._current_event = event
        self._event_to_ui(event)

    def _new_record(self):
        locked = self._locked_values()
        new_event = Event(
            uuid=str(uuid.uuid4()),
            source=self._source,
            since=None,
            until=None,
            focus_label="event",
            labels={},
        )
        for key, value in locked.items():
            if value:
                new_event.labels[key] = value if isinstance(value, list) else [value]
        self._current_event = new_event
        self._event_to_ui(new_event)

    def _locked_values(self) -> dict:
        return {
            "time": self._line_time.text() if self._check_lock_time.isChecked() else "",
            "location": self._line_location.text() if self._check_lock_location.isChecked() else "",
            "people": self._line_people.text() if self._check_lock_people.isChecked() else "",
            "organization": self._line_organization.text() if self._check_lock_organization.isChecked() else "",
            "tags": self._line_tags.text() if self._check_lock_tags.isChecked() else "",
        }

    def _event_to_ui(self, event: Event):
        self._label_uuid.setText(event.uuid)
        self._label_source.setText(self._source or "No source")

        self._line_time.setText(event.time_text())
        self._line_location.setText(", ".join(event.labels.get("location", [])))
        self._line_people.setText(", ".join(event.labels.get("people", [])))
        self._line_organization.setText(", ".join(event.labels.get("organization", [])))
        self._line_tags.setText(", ".join(event.labels.get("tags", [])))
        self._line_title.setText(event.title())
        self._text_brief.setPlainText(event.brief())
        self._text_event.setPlainText(event.event_text())

        radio_map = {
            "time": self._radio_time,
            "location": self._radio_location,
            "people": self._radio_people,
            "organization": self._radio_organization,
            "event": self._radio_event,
        }
        radio = radio_map.get(event.focus_label, self._radio_event)
        radio.setChecked(True)

    def _ui_to_event(self) -> Optional[Event]:
        since, until, _ = parse_time_text(self._line_time.text())
        if since is None or until is None:
            QMessageBox.information(self, "Input Check", "Time field is required and must be parseable.")
            return None

        focus = self._selected_focus_label()
        labels = {
            "time": [self._line_time.text().strip()],
            "location": [t.strip() for t in self._line_location.text().split(",") if t.strip()],
            "people": [t.strip() for t in self._line_people.text().split(",") if t.strip()],
            "organization": [t.strip() for t in self._line_organization.text().split(",") if t.strip()],
            "tags": [t.strip() for t in self._line_tags.text().split(",") if t.strip()],
            "title": [self._line_title.text().strip()] if self._line_title.text().strip() else [],
            "brief": [self._text_brief.toPlainText().strip()] if self._text_brief.toPlainText().strip() else [],
            "event": [self._text_event.toPlainText().strip()] if self._text_event.toPlainText().strip() else [],
        }

        # Validate focus requirement.
        if focus == "location" and not labels["location"]:
            QMessageBox.information(self, "Input Check", "Focus is Location but location is empty.")
            return None
        if focus == "people" and not labels["people"]:
            QMessageBox.information(self, "Input Check", "Focus is People but people is empty.")
            return None
        if focus == "organization" and not labels["organization"]:
            QMessageBox.information(self, "Input Check", "Focus is Organization but organization is empty.")
            return None
        if focus == "event" and not (labels["title"] or labels["brief"] or labels["event"]):
            QMessageBox.information(self, "Input Check", "Focus is Event but title/brief/event are all empty.")
            return None

        return Event(
            uuid=self._current_event.uuid if self._current_event else str(uuid.uuid4()),
            source=self._source,
            since=since,
            until=until,
            focus_label=focus,
            labels=labels,
        )

    def _selected_focus_label(self) -> str:
        if self._radio_time.isChecked():
            return "time"
        if self._radio_location.isChecked():
            return "location"
        if self._radio_people.isChecked():
            return "people"
        if self._radio_organization.isChecked():
            return "organization"
        return "event"

    # ------------------------------------------------------------------
    # Record list
    # ------------------------------------------------------------------

    def _refresh_record_list(self):
        self._combo_records.blockSignals(True)
        self._combo_records.clear()

        records = self._workspace.events(self._source)
        records = sorted(records, key=lambda e: e.since.value if e.since else 0)

        current_uuid = self._current_event.uuid if self._current_event else ""
        selected_index = -1
        for i, record in enumerate(records):
            time_str = format_jdn(record.since) if record.since else "?"
            text = f"[{time_str}] {record.abstract(30)}"
            self._combo_records.addItem(text, record.uuid)
            if record.uuid == current_uuid:
                selected_index = i

        if selected_index >= 0:
            self._combo_records.setCurrentIndex(selected_index)

        self._combo_records.blockSignals(False)

    def _select_uuid(self, uuid: str):
        for i in range(self._combo_records.count()):
            if self._combo_records.itemData(i) == uuid:
                self._combo_records.setCurrentIndex(i)
                return

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_source(self):
        if not self._source:
            return
        events = self._workspace.events(self._source)
        try:
            self._adapter.save_file(self._source, events)
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", str(e))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._on_apply()
        else:
            super().keyPressEvent(event)


class EventEditorDialog(QDialog):
    """Dialog wrapper around EventEditor."""

    def __init__(
        self,
        workspace: Workspace,
        source: str = "",
        edit_uuid: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Event Editor")
        self.resize(900, 700)

        self.editor = EventEditor(workspace, source, edit_uuid, self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)
