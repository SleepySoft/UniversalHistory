"""Thread management dialog for the timeline viewer."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from universal_history.adapters import HisFileAdapter
from universal_history.render.layout import ThreadLayout
from universal_history.render.timeline_view import TimelineView
from universal_history.ui.add_thread_dialog import AddThreadDialog


class ThreadManagerDialog(QDialog):
    """
    Manage the threads displayed on the timeline: axis offset, order, side,
    and per-thread minimum track width.
    """

    def __init__(self, view: TimelineView, adapter: HisFileAdapter, parent=None):
        super().__init__(parent)
        self._view = view
        self._adapter = adapter
        self.setWindowTitle(self.tr("Thread Manager"))
        self.resize(750, 500)

        self._updating = False

        self._build_ui()
        self._refresh_lists()
        self._sync_controls()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Add thread
        add_box = QGroupBox(self.tr("Add Thread"))
        add_layout = QHBoxLayout(add_box)
        self._add_left_btn = QPushButton(self.tr("Add Left"))
        self._add_left_btn.clicked.connect(lambda: self._on_add_thread("left"))
        add_layout.addWidget(self._add_left_btn)
        self._add_right_btn = QPushButton(self.tr("Add Right"))
        self._add_right_btn.clicked.connect(lambda: self._on_add_thread("right"))
        add_layout.addWidget(self._add_right_btn)
        layout.addWidget(add_box)

        # Axis offset
        offset_box = QGroupBox(self.tr("Axis Offset"))
        offset_layout = QHBoxLayout(offset_box)
        self._offset_slider = QSlider(Qt.Orientation.Horizontal)
        self._offset_slider.setRange(0, 100)
        self._offset_slider.setValue(int(self._view.coord.axis_offset * 100))
        self._offset_label = QLabel(str(int(self._view.coord.axis_offset * 100)))
        self._offset_slider.valueChanged.connect(self._on_offset_changed)
        offset_layout.addWidget(self._offset_slider)
        offset_layout.addWidget(self._offset_label)
        layout.addWidget(offset_box)

        # Thread lists
        lists_layout = QHBoxLayout()

        self._left_list = QListWidget()
        self._left_list.currentItemChanged.connect(self._on_selection_changed)
        lists_layout.addWidget(self._group_with_label(self.tr("Left Threads"), self._left_list))

        self._right_list = QListWidget()
        self._right_list.currentItemChanged.connect(self._on_selection_changed)
        lists_layout.addWidget(self._group_with_label(self.tr("Right Threads"), self._right_list))

        # Controls for selected thread
        controls_layout = QVBoxLayout()
        controls_layout.addStretch()

        self._share_spin = QDoubleSpinBox()
        self._share_spin.setRange(0.01, 0.99)
        self._share_spin.setDecimals(2)
        self._share_spin.setSingleStep(0.05)
        self._share_spin.valueChanged.connect(self._on_share_changed)
        controls_layout.addWidget(QLabel(self.tr("Thread Share")))
        controls_layout.addWidget(self._share_spin)

        self._remove_btn = QPushButton(self.tr("Remove"))
        self._remove_btn.clicked.connect(self._on_remove)
        controls_layout.addWidget(self._remove_btn)

        self._up_btn = QPushButton(self.tr("Move Up"))
        self._up_btn.clicked.connect(lambda: self._on_move(-1))
        controls_layout.addWidget(self._up_btn)

        self._down_btn = QPushButton(self.tr("Move Down"))
        self._down_btn.clicked.connect(lambda: self._on_move(1))
        controls_layout.addWidget(self._down_btn)

        self._switch_btn = QPushButton(self.tr("Switch Side"))
        self._switch_btn.clicked.connect(self._on_switch_side)
        controls_layout.addWidget(self._switch_btn)

        controls_layout.addStretch()
        lists_layout.addLayout(controls_layout)

        layout.addLayout(lists_layout)

        # Close button
        close_btn = QPushButton(self.tr("Close"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    @staticmethod
    def _group_with_label(text: str, widget) -> QWidget:
        group = QGroupBox(text)
        vbox = QVBoxLayout(group)
        vbox.addWidget(widget)
        return group

    # ------------------------------------------------------------------
    # Data sync
    # ------------------------------------------------------------------

    def _refresh_lists(self) -> None:
        self._left_list.clear()
        self._right_list.clear()
        for thread in self._view.left_threads():
            self._left_list.addItem(self._make_item(thread))
        for thread in self._view.right_threads():
            self._right_list.addItem(self._make_item(thread))

    def _make_item(self, thread: ThreadLayout) -> QListWidgetItem:
        source = thread.source or self.tr("(custom)")
        text = f"{source}\nshare={thread.share:.0%}"
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, id(thread))
        if thread.track_color:
            item.setBackground(thread.track_color)
        return item

    def _selected_thread(self) -> Optional[ThreadLayout]:
        for lst in (self._left_list, self._right_list):
            item = lst.currentItem()
            if item is None:
                continue
            thread_id = item.data(Qt.ItemDataRole.UserRole)
            for thread in self._view.left_threads() + self._view.right_threads():
                if id(thread) == thread_id:
                    return thread
        return None

    def _sync_controls(self) -> None:
        thread = self._selected_thread()
        enabled = thread is not None
        can_share = enabled and len(self._view.left_threads() if thread.align == "left" else self._view.right_threads()) > 1
        self._share_spin.setEnabled(can_share)
        self._remove_btn.setEnabled(enabled)
        self._up_btn.setEnabled(enabled)
        self._down_btn.setEnabled(enabled)
        self._switch_btn.setEnabled(enabled)

        if thread is not None and not self._updating:
            self._updating = True
            self._share_spin.setValue(thread.share)
            self._updating = False

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_offset_changed(self, value: int) -> None:
        self._offset_label.setText(str(value))
        self._view.coord.axis_offset = value / 100.0
        self._view.relayout()

    def _on_selection_changed(self) -> None:
        # Clear selection in the other list.
        sender = self.sender()
        if sender is self._left_list:
            self._right_list.setCurrentRow(-1)
        elif sender is self._right_list:
            self._left_list.setCurrentRow(-1)
        self._sync_controls()

    def _on_share_changed(self, value: float) -> None:
        if self._updating:
            return
        thread = self._selected_thread()
        if thread is None:
            return
        self._view.set_thread_share(thread, value)
        self._refresh_selected_item_text()

    def _on_remove(self) -> None:
        thread = self._selected_thread()
        if thread is None:
            return
        # Removing a thread only unbinds it from the view (no data change),
        # so a plain close confirmation is enough (decision 2026-09-18).
        reply = QMessageBox.question(
            self,
            self.tr("Remove Thread"),
            self.tr("Remove this thread from the view? The events stay saved."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._view.remove_thread(thread)
        self._refresh_lists()
        self._sync_controls()

    def _on_move(self, delta: int) -> None:
        thread = self._selected_thread()
        if thread is None:
            return
        if self._view.move_thread(thread, delta):
            self._refresh_lists()
            self._select_thread(thread)
            self._sync_controls()

    def _on_switch_side(self) -> None:
        thread = self._selected_thread()
        if thread is None:
            return
        if self._view.switch_thread_side(thread):
            self._refresh_lists()
            self._select_thread(thread)
            self._sync_controls()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _select_thread(self, thread: ThreadLayout) -> None:
        target_id = id(thread)
        for lst in (self._left_list, self._right_list):
            for i in range(lst.count()):
                if lst.item(i).data(Qt.ItemDataRole.UserRole) == target_id:
                    lst.setCurrentRow(i)
                    return

    def _refresh_selected_item_text(self) -> None:
        thread = self._selected_thread()
        if thread is None:
            return
        target_id = id(thread)
        for lst in (self._left_list, self._right_list):
            for i in range(lst.count()):
                item = lst.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == target_id:
                    item.setText(self._make_item(thread).text())
                    return

    def _on_add_thread(self, align: str) -> None:
        dlg = AddThreadDialog(self._adapter, side=align, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        source, events = dlg.get_result()
        self._view.add_thread(
            [e.to_index() for e in events], align=align, source=source
        )
        self._refresh_lists()
