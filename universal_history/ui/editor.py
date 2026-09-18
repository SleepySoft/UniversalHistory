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
from PyQt6.QtGui import QCloseEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QRadioButton, QTextEdit, QVBoxLayout, QWidget, QFileDialog,
    QDateTimeEdit, QTabWidget, QTableWidget, QTableWidgetItem,
)

from universal_history.adapters import HisFileAdapter, SaveConflictError
from universal_history.chrono import parse_time_text, format_jdn, jdn_to_qdatetime, qdatetime_to_jdn
from universal_history.models import Event, Workspace


class DateTimePickerDialog(QDialog):
    """Minimal date/time picker for in-range timestamps."""

    def __init__(self, initial: Optional[QDateTime] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Pick Date & Time"))
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

    Tracks a dirty flag for unsaved edits: switching records, starting a new
    record, or closing with unsaved changes prompts to save / discard /
    cancel (decision 2026-09-18, see spec/how/98-known-issues.md #28).
    """

    event_saved = pyqtSignal(Event)
    event_deleted = pyqtSignal(str)  # uuid

    def __init__(
        self,
        workspace: Workspace,
        source: str = "",
        edit_uuid: str = "",
        parent=None,
        preset_time_text: str = "",
    ):
        super().__init__(parent)

        self._workspace = workspace
        self._source = source
        self._current_event: Optional[Event] = None
        self._adapter = HisFileAdapter()
        self._dirty = False
        self._loading = False

        # ------------------------------------------------------------------
        # Widgets
        # ------------------------------------------------------------------
        self._label_source = QLabel(self.tr("No source"))
        self._btn_open_file = QPushButton(self.tr("Open File"))
        self._btn_new_file = QPushButton(self.tr("New File"))

        self._combo_records = QComboBox()
        self._btn_new = QPushButton(self.tr("New"))
        self._btn_delete = QPushButton(self.tr("Delete"))

        self._label_uuid = QLabel()
        self._line_time = QLineEdit()
        self._btn_calendar = QPushButton(self.tr("Calendar"))
        self._check_lock_time = QCheckBox(self.tr("Lock"))

        self._radio_time = QRadioButton(self.tr("Time"))
        self._radio_location = QRadioButton(self.tr("Location"))
        self._radio_people = QRadioButton(self.tr("People"))
        self._radio_organization = QRadioButton(self.tr("Organization"))
        self._radio_event = QRadioButton(self.tr("Event"))
        self._radio_event.setChecked(True)

        self._line_location = QLineEdit()
        self._check_lock_location = QCheckBox(self.tr("Lock"))
        self._line_people = QLineEdit()
        self._check_lock_people = QCheckBox(self.tr("Lock"))
        self._line_organization = QLineEdit()
        self._check_lock_organization = QCheckBox(self.tr("Lock"))
        self._line_tags = QLineEdit()
        self._check_lock_tags = QCheckBox(self.tr("Lock"))

        self._line_title = QLineEdit()
        self._text_brief = QTextEdit()
        self._text_event = QTextEdit()

        self._btn_apply = QPushButton(self.tr("Apply"))
        self._btn_cancel = QPushButton(self.tr("Cancel"))

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
        form.addRow(self.tr("UUID"), self._label_uuid)

        time_layout = QHBoxLayout()
        time_layout.addWidget(self._radio_time)
        time_layout.addWidget(self._line_time, 1)
        time_layout.addWidget(self._btn_calendar)
        time_layout.addWidget(self._check_lock_time)
        form.addRow(self.tr("Time"), time_layout)

        loc_layout = QHBoxLayout()
        loc_layout.addWidget(self._radio_location)
        loc_layout.addWidget(self._line_location, 1)
        loc_layout.addWidget(self._check_lock_location)
        form.addRow(self.tr("Location"), loc_layout)

        ppl_layout = QHBoxLayout()
        ppl_layout.addWidget(self._radio_people)
        ppl_layout.addWidget(self._line_people, 1)
        ppl_layout.addWidget(self._check_lock_people)
        form.addRow(self.tr("People"), ppl_layout)

        org_layout = QHBoxLayout()
        org_layout.addWidget(self._radio_organization)
        org_layout.addWidget(self._line_organization, 1)
        org_layout.addWidget(self._check_lock_organization)
        form.addRow(self.tr("Organization"), org_layout)

        focus_layout = QHBoxLayout()
        focus_layout.addWidget(self._radio_event)
        focus_layout.addWidget(QLabel(self.tr("Focus label")))
        form.addRow(self.tr("Focus"), focus_layout)

        tags_layout = QHBoxLayout()
        tags_layout.addWidget(self._line_tags, 1)
        tags_layout.addWidget(self._check_lock_tags)
        form.addRow(self.tr("Tags"), tags_layout)

        form.addRow(self.tr("Title"), self._line_title)
        form.addRow(self.tr("Brief"), self._text_brief)
        form.addRow(self.tr("Event"), self._text_event)

        # Tab 1: the guided form; Tab 2: the generic Label Tag Editor
        # (implements the legacy editor's empty placeholder tab — legacy
        # defect #39). Both views edit the same label set; the table is
        # authoritative at Apply time.
        form_widget = QWidget()
        form_widget.setLayout(form)

        self._label_table = QTableWidget(0, 2)
        self._label_table.setHorizontalHeaderLabels(
            [self.tr("Label"), self.tr("Tags (comma separated)")]
        )
        self._label_table.horizontalHeader().setStretchLastSection(True)
        self._btn_add_label = QPushButton(self.tr("Add Label"))
        self._btn_remove_label = QPushButton(self.tr("Remove Label"))

        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        table_layout.addWidget(self._label_table, 1)
        table_btn_line = QHBoxLayout()
        table_btn_line.addWidget(self._btn_add_label)
        table_btn_line.addWidget(self._btn_remove_label)
        table_btn_line.addStretch()
        table_layout.addLayout(table_btn_line)

        self._tabs = QTabWidget()
        self._tabs.addTab(form_widget, self.tr("Form"))
        self._tabs.addTab(table_panel, self.tr("Label Tags"))
        root.addWidget(self._tabs, 1)

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
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._btn_add_label.clicked.connect(self._on_add_label_row)
        self._btn_remove_label.clicked.connect(self._on_remove_label_row)
        self._label_table.itemChanged.connect(self._mark_dirty)

        # Dirty tracking: any user edit marks the form dirty.
        for line in (
            self._line_time,
            self._line_location,
            self._line_people,
            self._line_organization,
            self._line_tags,
            self._line_title,
        ):
            line.textChanged.connect(self._mark_dirty)
        self._text_brief.textChanged.connect(self._mark_dirty)
        self._text_event.textChanged.connect(self._mark_dirty)
        for radio in (
            self._radio_time,
            self._radio_location,
            self._radio_people,
            self._radio_organization,
            self._radio_event,
        ):
            radio.toggled.connect(self._mark_dirty)

        # ------------------------------------------------------------------
        # Load initial state
        # ------------------------------------------------------------------
        self._refresh_record_list()
        if edit_uuid:
            self._load_event(edit_uuid)
        else:
            self._new_record()
            if preset_time_text:
                # T5-1: position-aware creation — the clicked axis time is
                # prefilled as the (user-visible, dirty) initial Time value.
                self._line_time.setText(preset_time_text)
                self._mark_dirty()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_source(self, source: str) -> None:
        self._source = source
        self._refresh_record_list()
        self._new_record()

    def source(self) -> str:
        return self._source

    def edit_event(self, event_uuid: str) -> bool:
        """Load an existing record for editing (T5-3 non-modal reuse).

        Prompts to save/discard pending changes first; returns False when the
        user cancelled."""
        if not self.confirm_discard_or_save():
            return False
        self._load_event(event_uuid)
        return True

    def start_new_record(self, preset_time_text: str = "") -> bool:
        """Start a fresh record, optionally with a prefilled Time field
        (T5-1/T5-3). Prompts for pending changes; False when cancelled."""
        if not self.confirm_discard_or_save():
            return False
        self._new_record()
        if preset_time_text:
            self._line_time.setText(preset_time_text)
            self._mark_dirty()
        return True

    def is_dirty(self) -> bool:
        return self._dirty

    def confirm_discard_or_save(self) -> bool:
        """Prompt when there are unsaved changes.

        Returns True when it is OK to proceed (nothing to save, changes were
        saved, or the user chose Discard); False when the user cancelled.
        """
        if not self._dirty:
            return True
        reply = QMessageBox.question(
            self,
            self.tr("Unsaved Changes"),
            self.tr("The current event has unsaved changes."),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if reply == QMessageBox.StandardButton.Save:
            return self._on_apply()
        return reply == QMessageBox.StandardButton.Discard

    # ------------------------------------------------------------------
    # UI Event handlers
    # ------------------------------------------------------------------

    def _mark_dirty(self):
        if not self._loading:
            self._dirty = True

    def _on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Open History File"),
            str(self._adapter.depot_root), self.tr("History Files (*.his)"),
        )
        if path:
            try:
                events = self._adapter.load_file(path)
            except Exception as e:
                QMessageBox.critical(self, self.tr("Load Failed"), str(e))
                return
            self._workspace.load_events(events)
            self.set_source(events[0].source if events else path)

    def _on_new_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("New History File"),
            str(self._adapter.depot_root), self.tr("History Files (*.his)"),
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
        if not self.confirm_discard_or_save():
            # Revert the combo selection to the record still being edited.
            if self._current_event is not None:
                self._combo_records.blockSignals(True)
                self._select_uuid(self._current_event.uuid)
                self._combo_records.blockSignals(False)
            return
        self._load_event(data)

    def _on_new_record(self):
        if self.confirm_discard_or_save():
            self._new_record()

    def _on_delete(self):
        if self._current_event is None:
            return
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr("Delete event '%1'?").replace(
                "%1", self._current_event.abstract(40)
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            uuid = self._current_event.uuid
            self._workspace.remove(uuid)
            self._save_source()
            self.event_deleted.emit(uuid)
            self._refresh_record_list()
            self._new_record()

    def _on_apply(self) -> bool:
        if not self._source:
            QMessageBox.information(
                self, self.tr("Source Required"),
                self.tr("Please select or create a file first."),
            )
            return False

        event = self._ui_to_event()
        if event is None:
            return False

        self._workspace.upsert(event)
        self._save_source()
        self.event_saved.emit(event)
        self._current_event = event
        self._dirty = False
        self._refresh_record_list()
        self._select_uuid(event.uuid)
        return True

    def _on_cancel(self):
        self.window().close()

    def _on_pick_date(self):
        since, _, _ = parse_time_text(self._line_time.text())
        if since is None:
            QMessageBox.information(
                self, self.tr("No Time"),
                self.tr("Enter a valid time first, then use the calendar."),
            )
            return

        qdt = jdn_to_qdatetime(since)
        if qdt is None:
            QMessageBox.information(
                self, self.tr("Out of Range"),
                self.tr("Calendar picker only supports years 1-9999."),
            )
            return

        dlg = DateTimePickerDialog(qdt, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_jdn = qdatetime_to_jdn(dlg.selected())
            self._line_time.setText(format_jdn(new_jdn))

    def _on_time_changed(self):
        since, until, displays = parse_time_text(self._line_time.text())
        if since is not None:
            tooltip = self.tr("Parsed: %1").replace("%1", "; ".join(displays))
            self._line_time.setToolTip(tooltip)
        else:
            self._line_time.setToolTip(self.tr("Cannot parse time"))

    # ------------------------------------------------------------------
    # Label Tag Editor tab (generic label/tag table)
    # ------------------------------------------------------------------

    _FORM_LABEL_KEYS = (
        "time", "location", "people", "organization", "tags",
        "title", "brief", "event",
    )

    def _on_tab_changed(self, index: int):
        if self._loading:
            return
        if index == 1:
            # Entering the table: fold current form edits into it.
            self._sync_table_from_form()
        else:
            # Back to the form: reflect table edits in the form fields.
            self._sync_form_from_table()

    def _on_add_label_row(self):
        self._label_table.insertRow(self._label_table.rowCount())
        self._mark_dirty()

    def _on_remove_label_row(self):
        row = self._label_table.currentRow()
        if row >= 0:
            self._label_table.removeRow(row)
            self._mark_dirty()

    def _form_labels(self) -> dict:
        """Current values of the form-exposed labels (empty = removed)."""
        return {
            "time": [self._line_time.text().strip()] if self._line_time.text().strip() else [],
            "location": [t.strip() for t in self._line_location.text().split(",") if t.strip()],
            "people": [t.strip() for t in self._line_people.text().split(",") if t.strip()],
            "organization": [t.strip() for t in self._line_organization.text().split(",") if t.strip()],
            "tags": [t.strip() for t in self._line_tags.text().split(",") if t.strip()],
            "title": [self._line_title.text().strip()] if self._line_title.text().strip() else [],
            "brief": [self._text_brief.toPlainText().strip()] if self._text_brief.toPlainText().strip() else [],
            "event": [self._text_event.toPlainText().strip()] if self._text_event.toPlainText().strip() else [],
        }

    def _table_labels(self) -> dict:
        """Read the label table into a labels dict (empty labels dropped)."""
        labels: dict = {}
        for row in range(self._label_table.rowCount()):
            label_item = self._label_table.item(row, 0)
            tags_item = self._label_table.item(row, 1)
            label = label_item.text().strip() if label_item else ""
            if not label:
                continue
            tags_text = tags_item.text() if tags_item else ""
            tags = [t.strip() for t in tags_text.split(",") if t.strip()]
            if tags:
                labels.setdefault(label, []).extend(tags)
        return labels

    def _sync_table_from_labels(self, labels: dict):
        self._loading = True
        try:
            self._label_table.setRowCount(0)
            for label, tags in labels.items():
                if not tags:
                    continue
                row = self._label_table.rowCount()
                self._label_table.insertRow(row)
                self._label_table.setItem(row, 0, QTableWidgetItem(label))
                self._label_table.setItem(row, 1, QTableWidgetItem(", ".join(tags)))
        finally:
            self._loading = False

    def _sync_table_from_form(self):
        labels = self._table_labels()
        for key, values in self._form_labels().items():
            if values:
                labels[key] = values
            else:
                labels.pop(key, None)
        self._sync_table_from_labels(labels)

    def _sync_form_from_table(self):
        labels = self._table_labels()
        self._loading = True
        try:
            self._line_time.setText(", ".join(labels.get("time", [])))
            self._line_location.setText(", ".join(labels.get("location", [])))
            self._line_people.setText(", ".join(labels.get("people", [])))
            self._line_organization.setText(", ".join(labels.get("organization", [])))
            self._line_tags.setText(", ".join(labels.get("tags", [])))
            self._line_title.setText(labels.get("title", [""])[0])
            self._text_brief.setPlainText(labels.get("brief", [""])[0])
            self._text_event.setPlainText(labels.get("event", [""])[0])
        finally:
            self._loading = False

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
        self._loading = True
        try:
            self._label_uuid.setText(event.uuid)
            self._label_source.setText(self._source or self.tr("No source"))

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

            # Populate the generic label/tag table from the full label set.
            self._sync_table_from_labels(event.labels)
        finally:
            self._loading = False
            self._dirty = False

    def _ui_to_event(self) -> Optional[Event]:
        since, until, _ = parse_time_text(self._line_time.text())
        if since is None or until is None:
            QMessageBox.information(
                self, self.tr("Input Check"),
                self.tr("Time field is required and must be parseable."),
            )
            return None

        focus = self._selected_focus_label()

        # The label table is the authoritative label set at Apply time: it
        # was populated from the event's full labels (so UI-unexposed labels
        # survive) and is kept in sync with the form both ways.
        if self._tabs.currentIndex() == 0:
            self._sync_table_from_form()
        labels = self._table_labels()

        # Validate focus requirement (labels may lack cleared keys).
        if focus == "location" and not labels.get("location"):
            QMessageBox.information(
                self, self.tr("Input Check"),
                self.tr("Focus is Location but location is empty."),
            )
            return None
        if focus == "people" and not labels.get("people"):
            QMessageBox.information(
                self, self.tr("Input Check"),
                self.tr("Focus is People but people is empty."),
            )
            return None
        if focus == "organization" and not labels.get("organization"):
            QMessageBox.information(
                self, self.tr("Input Check"),
                self.tr("Focus is Organization but organization is empty."),
            )
            return None
        if focus == "event" and not (
            labels.get("title") or labels.get("brief") or labels.get("event")
        ):
            QMessageBox.information(
                self, self.tr("Input Check"),
                self.tr("Focus is Event but title/brief/event are all empty."),
            )
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
        except SaveConflictError as e:
            reply = QMessageBox.question(
                self,
                self.tr("Save Conflict"),
                self.tr("The file changed on disk since it was loaded.\n"
                        "Overwrite it anyway?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self._adapter.save_file(self._source, events, force=True)
                except Exception as e2:
                    QMessageBox.critical(self, self.tr("Save Failed"), str(e2))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Save Failed"), str(e))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._on_apply()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent):
        if self.confirm_discard_or_save():
            super().closeEvent(event)
        else:
            event.ignore()


class EventEditorDialog(QDialog):
    """Dialog wrapper around EventEditor."""

    def __init__(
        self,
        workspace: Workspace,
        source: str = "",
        edit_uuid: str = "",
        parent=None,
        preset_time_text: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Event Editor"))
        self.resize(900, 700)

        self.editor = EventEditor(
            workspace, source, edit_uuid, self, preset_time_text=preset_time_text
        )
        layout = QVBoxLayout(self)
        layout.addWidget(self.editor)

    def closeEvent(self, event: QCloseEvent):
        if self.editor.confirm_discard_or_save():
            super().closeEvent(event)
        else:
            event.ignore()
