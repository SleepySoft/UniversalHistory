"""
Main application window for UniversalHistory.

Integrates the timeline viewer, workspace, event editor, and filter dialog
into a single PyQt6 desktop application.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

# Support running this file directly from inside the package (e.g. PyCharm's
# "Run <file>" configuration). In that case the project root is not on sys.path,
# so add it before importing the rest of the package.
if __name__ == "__main__":
    _project_root = Path(__file__).resolve().parents[1]
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QAction, QColor, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDockWidget, QFileDialog, QInputDialog, QMainWindow,
    QMenu, QMessageBox, QTextBrowser, QVBoxLayout, QWidget,
)

from universal_history.adapters import HisFileAdapter, SaveConflictError
from universal_history.chrono.time_utils import format_jdn
from universal_history.i18n import install_translator
from universal_history.models import Workspace
from universal_history.render import TimelineView
from universal_history.ui import (
    AddThreadDialog,
    BindSourceDialog,
    EventEditor,
    FilterDialog,
    ThreadManagerDialog,
)


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
        self._view.itemClicked.connect(self._on_item_clicked)
        self._view.contextMenuRequested.connect(self._on_timeline_context_menu)

        self.setCentralWidget(self._view)

        # T5-5 / §8.6: single-click a timeline item to show its full content
        # in a side panel, instead of opening the editor just to read it.
        self._details_view = QTextBrowser(self)
        self._details_dock = QDockWidget(self.tr("Event Details"), self)
        self._details_dock.setObjectName("eventDetailsDock")
        self._details_dock.setWidget(self._details_view)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,
                           self._details_dock)
        self._details_dock.hide()

        # T5-3: non-modal side editor — the timeline stays visible and
        # interactive while editing. Replaces the former modal dialog.
        self._editor = EventEditor(self._workspace, parent=self)
        self._editor.event_saved.connect(self._on_editor_event_saved)
        self._editor_dock = QDockWidget(self.tr("Event Editor"), self)
        self._editor_dock.setObjectName("eventEditorDock")
        self._editor_dock.setWidget(self._editor)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,
                           self._editor_dock)
        self._editor_dock.hide()

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

        file_menu = menubar.addMenu(self.tr("File"))
        open_action = QAction(self.tr("Open File..."), self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        exit_action = QAction(self.tr("Exit"), self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu(self.tr("View"))
        editor_action = QAction(self.tr("Event Editor"), self)
        editor_action.setShortcut("Ctrl+E")
        editor_action.triggered.connect(self._on_open_editor)
        view_menu.addAction(editor_action)

        filter_action = QAction(self.tr("Filter..."), self)
        filter_action.setShortcut("Ctrl+L")
        filter_action.triggered.connect(self._on_open_filter)
        view_menu.addAction(filter_action)

        fit_action = QAction(self.tr("Fit to View"), self)
        fit_action.setShortcut("Ctrl+0")
        fit_action.triggered.connect(self._view.fit_to_sources)
        view_menu.addAction(fit_action)

        toggle_action = QAction(self.tr("Toggle Orientation"), self)
        toggle_action.setShortcut("Ctrl+T")
        toggle_action.triggered.connect(self._view.toggle_orientation)
        view_menu.addAction(toggle_action)

        thread_mgr_action = QAction(self.tr("Thread Manager..."), self)
        thread_mgr_action.setShortcut("Ctrl+M")
        thread_mgr_action.triggered.connect(self._on_open_thread_manager)
        view_menu.addAction(thread_mgr_action)

        help_menu = menubar.addMenu(self.tr("Help"))
        help_action = QAction(self.tr("Help Contents"), self)
        help_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        help_action.triggered.connect(self._on_help)
        help_menu.addAction(help_action)

        about_action = QAction(self.tr("About UniversalHistory"), self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------
    # Help / About (legacy defects #16 — were empty stubs)
    # ------------------------------------------------------------------

    _HELP_TEXT = (
        "UniversalHistory — infinite timeline viewer\n"
        "\n"
        "Navigation:\n"
        "  - Drag with the left mouse button to pan.\n"
        "  - Mouse wheel pans; Ctrl + wheel zooms around the cursor.\n"
        "  - Arrow keys scroll smoothly (Up/Down: small steps, Left/Right: pages).\n"
        "  - Ctrl+0 fits all loaded data; Ctrl+T toggles horizontal/vertical.\n"
        "\n"
        "Events:\n"
        "  - Double-click an event to edit it.\n"
        "  - Right-click for the context menu (add thread, new event, delete).\n"
        "  - Ctrl+E opens the event editor; Ctrl+L opens the filter dialog.\n"
        "\n"
        "Time text accepts natural language such as \"300 BC\", \"公元前200年\",\n"
        "\"2030-05-01\" or ranges like \"公元前300年 - 公元前200年\"."
    )

    _ABOUT_TEXT = (
        "UniversalHistory\n"
        "\n"
        "An infinite historical timeline built on a single proleptic-Gregorian\n"
        "JDN timestamp model (astronomical year numbering, year 0 = 1 BC).\n"
        "\n"
        "A PyQt6 re-implementation of the legacy History project."
    )

    def _on_help(self):
        QMessageBox.information(self, self.tr("Help"), self.tr(self._HELP_TEXT))

    def _on_about(self):
        QMessageBox.about(self, self.tr("About UniversalHistory"),
                          self.tr(self._ABOUT_TEXT))

    def closeEvent(self, event: QCloseEvent):
        """Exit confirmation (restored legacy behaviour, i18n text)."""
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Exit"),
            self.tr("Quit UniversalHistory?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()

    def _load_file(self, path: str):
        try:
            events = self._adapter.load_file(path)
            self._workspace.load_events(events)
            source = events[0].source if events else path
            self._view.load_source(source, align="right")
            self._view.show_events_at_default_scale([source])
        except Exception as e:
            QMessageBox.critical(self, self.tr("Load Failed"), str(e))

    def _on_add_thread(self, align: str = "right"):
        dlg = AddThreadDialog(self._adapter, side=align, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        source, events = dlg.get_result()
        if events:
            self._workspace.load_events(events)
        indexes = [e.to_index() for e in events]
        thread = self._view.add_thread(indexes, align=align, source=source)
        # If we created a new empty source, immediately open the editor so the
        # user can add the first record seamlessly.
        if not indexes and source:
            self._open_editor(source)

    def _on_new_event_for_thread(self, thread, preset_time_text: str = ""):
        """Open the editor for a thread, binding a source first if needed."""
        if thread.source:
            self._open_editor(thread.source, preset_time_text=preset_time_text)
            return
        dlg = BindSourceDialog(self._adapter, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        source, events = dlg.get_result()
        if events:
            self._workspace.load_events(events)
        thread.source = source
        self._view.set_thread_events(thread, [e.to_index() for e in events])
        self._open_editor(source, preset_time_text=preset_time_text)

    def _on_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open History File"),
            str(self._adapter.depot_root),
            self.tr("History Files (*.his)"),
        )
        if path:
            self._load_file(path)

    def _on_open_editor(self):
        # Use the first loaded source if none currently selected.
        source = self._workspace.sources()[0] if self._workspace.sources() else ""
        if not source:
            # No file loaded: guide the user to open/create one instead of
            # showing an editor that cannot save (spec #33 / T4).
            box = QMessageBox(self)
            box.setWindowTitle(self.tr("No Source"))
            box.setText(self.tr("Open or create a history file before editing events."))
            open_btn = box.addButton(
                self.tr("Open File..."), QMessageBox.ButtonRole.AcceptRole
            )
            new_btn = box.addButton(
                self.tr("New File..."), QMessageBox.ButtonRole.ActionRole
            )
            box.addButton(QMessageBox.StandardButton.Cancel)
            box.exec()
            clicked = box.clickedButton()
            if clicked is open_btn:
                path, _ = QFileDialog.getOpenFileName(
                    self,
                    self.tr("Open History File"),
                    str(self._adapter.depot_root),
                    self.tr("History Files (*.his)"),
                )
                if not path:
                    return
                self._load_file(path)
                source = self._workspace.sources()[0] if self._workspace.sources() else ""
            elif clicked is new_btn:
                path, _ = QFileDialog.getSaveFileName(
                    self,
                    self.tr("New History File"),
                    str(self._adapter.depot_root),
                    self.tr("History Files (*.his)"),
                )
                if not path:
                    return
                Path(path).write_text("", encoding="utf-8")
                source = path
            else:
                return
        self._open_editor(source)

    def _open_editor(self, source: str, edit_uuid: str = "",
                     preset_time_text: str = ""):
        """T5-3: open the non-modal side editor dock (timeline stays usable).

        Unsaved content in the panel is confirmed before switching context;
        hiding the dock keeps the unsaved content intact."""
        if self._editor.is_dirty() and not self._editor.confirm_discard_or_save():
            return
        if self._editor.source() != source:
            self._editor.set_source(source)
        if edit_uuid:
            if not self._editor.edit_event(edit_uuid):
                return
        else:
            if not self._editor.start_new_record(preset_time_text):
                return
        self._editor_dock.show()
        self._editor_dock.raise_()

    def _on_editor_event_saved(self, event):
        # T5-2: after a save, reveal the event on the timeline (no-op when it
        # is already visible, e.g. position-aware creation at the clicked spot).
        if event.since is not None:
            self._view.reveal_time(event.since)

    def _on_item_double_clicked(self, index):
        self._open_editor(index.source, edit_uuid=index.uuid)

    def _on_item_clicked(self, index):
        """T5-5: show the full event content in the side details panel."""
        event = self._workspace.get_by_uuid(index.uuid)
        if event is None:
            return
        self.show_event_details(event)

    def show_event_details(self, event):
        """Populate and reveal the side details panel for `event`."""
        if event.since is not None:
            time_text = format_jdn(event.since)
            if event.until is not None and event.until != event.since:
                time_text += " ~ " + format_jdn(event.until)
        else:
            time_text = self.tr("No Time")

        parts = []
        title = event.title()
        if title:
            parts.append(f"<h3>{html.escape(title)}</h3>")
        parts.append(
            f"<p><i>{html.escape(time_text)}</i><br>"
            f"<small>{self.tr('Source')}: {html.escape(event.source)}</small></p>"
        )
        brief = event.brief()
        if brief:
            parts.append(f"<p>{html.escape(brief)}</p>")
        body = event.event_text()
        if body:
            parts.append(f"<p>{html.escape(body).replace(chr(10), '<br>')}</p>")
        self._details_view.setHtml("".join(parts))
        self._details_dock.show()

    def _on_timeline_context_menu(self, global_pos, index):
        menu = QMenu(self)

        local_pos = self._view.mapFromGlobal(global_pos)
        local_f = QPointF(local_pos)
        thread = self._view.thread_at_screen(local_f)
        side = thread.align if thread is not None else self._view.side_at_screen(local_f)

        # Context-aware add / load: use the side where the cursor is.
        add_action = QAction(self.tr("Add thread"), self)
        add_action.triggered.connect(lambda: self._on_add_thread(side))
        menu.addAction(add_action)

        load_action = QAction(self.tr("Load file"), self)
        if thread is not None:
            load_action.triggered.connect(lambda: self._load_file_into_thread(thread))
        else:
            load_action.triggered.connect(lambda: self._on_add_thread(side))
        menu.addAction(load_action)

        if thread is not None:
            # T5-1: position-aware creation — prefill the clicked axis time.
            click_time_text = format_jdn(self._view.time_at_screen(local_f))
            new_event_action = QAction(self.tr("New event"), self)
            new_event_action.triggered.connect(
                lambda: self._on_new_event_for_thread(
                    thread, preset_time_text=click_time_text
                )
            )
            menu.addAction(new_event_action)

        if thread is not None:
            menu.addSeparator()

            share_action = QAction(self.tr("Set thread share..."), self)
            share_action.triggered.connect(lambda: self._on_set_thread_share(thread))
            menu.addAction(share_action)

            switch_action = QAction(self.tr("Switch side"), self)
            switch_action.triggered.connect(lambda: self._view.switch_thread_side(thread))
            menu.addAction(switch_action)

            remove_action = QAction(self.tr("Remove this thread"), self)
            remove_action.triggered.connect(lambda: self._confirm_remove_thread(thread))
            menu.addAction(remove_action)

        menu.addSeparator()

        fit_action = QAction(self.tr("Fit to view"), self)
        fit_action.triggered.connect(self._view.fit_to_sources)
        menu.addAction(fit_action)

        toggle_action = QAction(self.tr("Toggle orientation"), self)
        toggle_action.triggered.connect(self._view.toggle_orientation)
        menu.addAction(toggle_action)

        if index is not None:
            menu.addSeparator()
            edit_action = QAction(self.tr("Edit event"), self)
            edit_action.triggered.connect(
                lambda: self._open_editor(index.source, edit_uuid=index.uuid)
            )
            menu.addAction(edit_action)

            delete_action = QAction(self.tr("Delete event"), self)
            delete_action.triggered.connect(lambda: self._delete_event(index))
            menu.addAction(delete_action)

        menu.exec(global_pos)

    def _confirm_remove_thread(self, thread):
        """Removing a thread only unbinds it from the view (no data change),
        so a plain close confirmation is enough."""
        reply = QMessageBox.question(
            self,
            self.tr("Remove Thread"),
            self.tr("Remove this thread from the view? The events stay saved."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._view.remove_thread(thread)

    def _delete_event(self, index):
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr("Delete '%1'?").replace("%1", index.abstract[:40]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._workspace.remove(index.uuid)
            try:
                self._adapter.save_file(
                    index.source, self._workspace.events(index.source)
                )
            except SaveConflictError:
                reply2 = QMessageBox.question(
                    self,
                    self.tr("Save Conflict"),
                    self.tr("The file changed on disk since it was loaded.\n"
                            "Overwrite it anyway?"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply2 == QMessageBox.StandardButton.Yes:
                    try:
                        self._adapter.save_file(
                            index.source,
                            self._workspace.events(index.source),
                            force=True,
                        )
                    except Exception as e2:
                        QMessageBox.critical(self, self.tr("Save Failed"), str(e2))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Save Failed"), str(e))

    def _on_open_thread_manager(self):
        dlg = ThreadManagerDialog(self._view, adapter=self._adapter, parent=self)
        dlg.exec()

    def _on_set_thread_share(self, thread):
        share, ok = QInputDialog.getDouble(
            self,
            self.tr("Thread Share"),
            self.tr("Share of this side (0.0 ~ 1.0):"),
            thread.share,
            0.01,
            0.99,
            2,
        )
        if ok:
            self._view.set_thread_share(thread, share)

    def _load_file_into_thread(self, thread):
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
            self._workspace.load_events(events)
            source = events[0].source if events else path
            indexes = [e.to_index() for e in events]
            thread.source = source
            self._view.set_thread_events(thread, indexes)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Load Failed"), str(e))

    def _on_open_filter(self):
        dlg = FilterDialog(self._workspace, self)
        dlg.filter_applied.connect(self._on_filter_applied)
        dlg.exec()

    def _on_filter_applied(self, indexes):
        # Reuse an existing filter thread instead of stacking new ones.
        for thread in self._view.left_threads() + self._view.right_threads():
            if thread.source == "__filter__":
                self._view.set_thread_events(thread, indexes)
                return

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
    args = list(sys.argv[1:] if argv is None else argv)
    language = None
    if "--lang" in args:
        i = args.index("--lang")
        if i + 1 < len(args):
            language = args[i + 1]
    app = QApplication([sys.argv[0]])
    install_translator(app, language)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
