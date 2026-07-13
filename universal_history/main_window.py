"""
Main application window for UniversalHistory.

Integrates the timeline viewer, workspace, event editor, and filter dialog
into a single PyQt6 desktop application.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Support running this file directly from inside the package (e.g. PyCharm's
# "Run <file>" configuration). In that case the project root is not on sys.path,
# so add it before importing the rest of the package.
if __name__ == "__main__":
    _project_root = Path(__file__).resolve().parents[1]
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QMainWindow, QMenu, QMessageBox, QVBoxLayout,
    QWidget,
)

from universal_history.adapters import HisFileAdapter
from universal_history.models import Workspace
from universal_history.render import TimelineView
from universal_history.ui import EventEditorDialog, FilterDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UniversalHistory")
        self.resize(1400, 900)

        self._workspace = Workspace()
        self._adapter = HisFileAdapter()

        self._view = TimelineView()
        self._view.set_workspace(self._workspace)
        self._view.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._view.contextMenuRequested.connect(self._on_timeline_context_menu)

        self.setCentralWidget(self._view)
        self._init_menu()

        # Load example data by default.
        example = (
            Path(__file__).resolve().parents[2]
            / "History"
            / "depot"
            / "example"
            / "example.his"
        )
        if example.exists():
            self._load_file(str(example))

    def _init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        open_action = QAction("Open File...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("View")
        editor_action = QAction("Event Editor", self)
        editor_action.setShortcut("Ctrl+E")
        editor_action.triggered.connect(self._on_open_editor)
        view_menu.addAction(editor_action)

        filter_action = QAction("Filter...", self)
        filter_action.setShortcut("Ctrl+L")
        filter_action.triggered.connect(self._on_open_filter)
        view_menu.addAction(filter_action)

        fit_action = QAction("Fit to View", self)
        fit_action.setShortcut("Ctrl+0")
        fit_action.triggered.connect(self._view.fit_to_sources)
        view_menu.addAction(fit_action)

        toggle_action = QAction("Toggle Orientation", self)
        toggle_action.setShortcut("Ctrl+T")
        toggle_action.triggered.connect(self._view.toggle_orientation)
        view_menu.addAction(toggle_action)

    def _load_file(self, path: str):
        try:
            events = self._adapter.load_file(path)
            self._workspace.load_events(events)
            source = events[0].source if events else path
            self._view.load_source(
                source,
                align="right",
                track_color=QColor(230, 230, 230),
                item_color=QColor(185, 227, 217),
            )
            self._view.show_events_at_default_scale([source])
        except Exception as e:
            QMessageBox.critical(self, "Load Failed", str(e))

    def _add_file_as_thread(self, align: str = "left"):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open History File",
            str(self._adapter.depot_root),
            "History Files (*.his)",
        )
        if not path:
            return
        try:
            events = self._adapter.load_file(path)
            self._workspace.load_events(events)
            source = events[0].source if events else path
            if align == "left":
                track_color = QColor(220, 230, 240)
                item_color = QColor(200, 210, 240)
            else:
                track_color = QColor(230, 230, 230)
                item_color = QColor(185, 227, 217)
            self._view.load_source(
                source,
                align=align,
                track_color=track_color,
                item_color=item_color,
            )
        except Exception as e:
            QMessageBox.critical(self, "Load Failed", str(e))

    def _on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open History File",
            str(self._adapter.depot_root),
            "History Files (*.his)",
        )
        if path:
            self._load_file(path)

    def _on_open_editor(self):
        # Use the first loaded source if none currently selected.
        source = self._workspace.sources()[0] if self._workspace.sources() else ""
        self._open_editor(source)

    def _open_editor(self, source: str, edit_uuid: str = ""):
        dlg = EventEditorDialog(
            self._workspace, source=source, edit_uuid=edit_uuid, parent=self
        )
        dlg.exec()

    def _on_item_double_clicked(self, index):
        self._open_editor(index.source, edit_uuid=index.uuid)

    def _on_timeline_context_menu(self, global_pos, index):
        menu = QMenu(self)

        load_left_action = QAction("Load file into left thread", self)
        load_left_action.triggered.connect(lambda: self._add_file_as_thread("left"))
        menu.addAction(load_left_action)

        load_right_action = QAction("Load file into right thread", self)
        load_right_action.triggered.connect(lambda: self._add_file_as_thread("right"))
        menu.addAction(load_right_action)

        menu.addSeparator()

        fit_action = QAction("Fit to view", self)
        fit_action.triggered.connect(self._view.fit_to_sources)
        menu.addAction(fit_action)

        toggle_action = QAction("Toggle orientation", self)
        toggle_action.triggered.connect(self._view.toggle_orientation)
        menu.addAction(toggle_action)

        if index is not None:
            menu.addSeparator()
            edit_action = QAction("Edit event", self)
            edit_action.triggered.connect(
                lambda: self._open_editor(index.source, edit_uuid=index.uuid)
            )
            menu.addAction(edit_action)

            delete_action = QAction("Delete event", self)
            delete_action.triggered.connect(lambda: self._delete_event(index))
            menu.addAction(delete_action)

        menu.exec(global_pos)

    def _delete_event(self, index):
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete '{index.abstract[:40]}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._workspace.remove(index.uuid)
            try:
                self._adapter.save_file(
                    index.source, self._workspace.events(index.source)
                )
            except Exception as e:
                QMessageBox.critical(self, "Save Failed", str(e))

    def _on_open_filter(self):
        dlg = FilterDialog(self._workspace, self)
        dlg.filter_applied.connect(self._on_filter_applied)
        dlg.exec()

    def _on_filter_applied(self, indexes):
        self._view.add_thread(
            indexes,
            align="left",
            track_color=QColor(220, 230, 240),
            item_color=QColor(200, 210, 240),
            source="__filter__",
        )


def main(argv: list[str] | None = None) -> int:
    # Only pass the executable name to QApplication so that debugger/IDE
    # arguments (e.g. PyCharm's --file, --multiprocess) are not interpreted
    # by Qt and do not break startup.
    app = QApplication([sys.argv[0]])
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
