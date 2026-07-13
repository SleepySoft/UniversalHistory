"""
TimelineView: the main timeline widget.

Combines the central time axis with left/right threads and handles pan/zoom
and item hover/selection.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QContextMenuEvent, QFont, QMouseEvent, QWheelEvent
from PyQt6.QtCore import QPoint
from universal_history.chrono.jdn_timestamp import JDNTimestamp
from PyQt6.QtWidgets import QApplication, QWidget

from universal_history.models import Event, EventIndex, Workspace
from universal_history.render.geometry import CoordinateSystem
from universal_history.render.layout import ThreadLayout
from universal_history.render.painter import paint_axis, paint_item, paint_thread_background


AXIS_BREADTH = 30  # pixels reserved for the central axis strip


class TimelineView(QWidget):
    """
    QWidget that displays a JDNTimestamp-based timeline with multiple threads.
    """

    itemClicked = pyqtSignal(EventIndex)
    itemDoubleClicked = pyqtSignal(EventIndex)
    contextMenuRequested = pyqtSignal(QPoint, object)  # global pos, optional EventIndex

    def __init__(self, parent=None):
        super().__init__(parent)

        self.coord = CoordinateSystem(self)

        self.bg_color = QColor(25, 25, 30)
        self.axis_color = QColor(100, 100, 100)
        self.tick_color = QColor(180, 180, 180)
        self.text_color = QColor(220, 220, 220)
        self.item_text_color = QColor(20, 20, 20)
        self.tick_font = QFont("Segoe UI", 9)
        self.item_font = QFont("微软雅黑", 8)

        self._left_threads: List[ThreadLayout] = []
        self._right_threads: List[ThreadLayout] = []
        self._workspace: Optional[Workspace] = None

        self._drag_last_pos: Optional[QPointF] = None
        self._hover_item: Optional[EventIndex] = None

        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Thread management
    # ------------------------------------------------------------------

    def set_workspace(self, workspace: Workspace, source: Optional[str] = None) -> None:
        """Bind the view to a Workspace so it updates automatically."""
        if self._workspace is workspace:
            return
        if self._workspace is not None:
            try:
                self._workspace.event_added.disconnect(self._on_event_added)
                self._workspace.event_updated.disconnect(self._on_event_updated)
                self._workspace.event_removed.disconnect(self._on_event_removed)
                self._workspace.source_loaded.disconnect(self._on_source_loaded)
            except Exception:
                pass
        self._workspace = workspace
        workspace.event_added.connect(self._on_event_added)
        workspace.event_updated.connect(self._on_event_updated)
        workspace.event_removed.connect(self._on_event_removed)
        workspace.source_loaded.connect(self._on_source_loaded)
        if source is not None:
            self.load_source(source)

    def load_source(
        self,
        source: str,
        align: str = "right",
        track_color: QColor = None,
        item_color: QColor = None,
    ) -> ThreadLayout:
        """Add a thread displaying all events from a workspace source."""
        if self._workspace is None:
            raise RuntimeError("Call set_workspace() before load_source()")
        events = [e.to_index() for e in self._workspace.events(source)]
        return self.add_thread(
            events, align=align, source=source, track_color=track_color, item_color=item_color
        )

    def add_thread(
        self,
        events: List[EventIndex],
        align: str = "right",
        track_color: QColor = None,
        item_color: QColor = None,
        source: str = "",
    ) -> ThreadLayout:
        thread = ThreadLayout(
            align=align, track_color=track_color, item_color=item_color, source=source
        )
        thread.set_events(events)
        if align == "left":
            self._left_threads.append(thread)
        else:
            self._right_threads.append(thread)
        self._arrange_threads()
        self.update()
        return thread

    def refresh_source(self, source: str) -> None:
        """Reload all threads bound to a given source."""
        if self._workspace is None:
            return
        indexes = [e.to_index() for e in self._workspace.events(source)]
        changed = False
        for thread in self._left_threads + self._right_threads:
            if thread.source == source:
                thread.set_events(indexes)
                changed = True
        if changed:
            self._arrange_threads()
            self.update()

    def clear_threads(self) -> None:
        self._left_threads.clear()
        self._right_threads.clear()
        self.update()

    def set_thread_events(self, thread: ThreadLayout, events: List[EventIndex]) -> None:
        thread.set_events(events)
        self._arrange_threads()
        self.update()

    def toggle_orientation(self) -> None:
        self.coord.is_vertical = not self.coord.is_vertical
        self._arrange_threads()
        self.update()

    def fit_to_sources(
        self, sources: Optional[List[str]] = None, padding: float = 0.05
    ) -> None:
        """Zoom and pan so that events from the given sources fit the view."""
        items: List[EventIndex] = []
        for thread in self._left_threads + self._right_threads:
            if sources is None or thread.source in sources:
                items.extend(thread.events)

        if not items:
            return

        min_time = min(item.since.value for item in items if item.since is not None)
        max_time = max(item.until.value for item in items if item.until is not None)
        if min_time >= max_time:
            return

        vp = self.coord.viewport()
        if vp.length <= 0:
            return

        self.coord.center_time = JDNTimestamp((min_time + max_time) // 2)
        range_us = max_time - min_time
        # Ensure at least a sensible minimum range for point-only data.
        one_year_us = int(365.2425 * 24 * 3600 * 1_000_000)
        range_us = max(range_us, one_year_us)
        target_px = vp.length * (1 - 2 * padding)
        self.coord.scale = max(1e-15, target_px / range_us)
        self._arrange_threads()
        self.update()

    def show_events_at_default_scale(
        self,
        sources: Optional[List[str]] = None,
    ) -> None:
        """
        Show the densest cluster of events at a comfortable scale.

        This avoids the "everything squeezed" look when the dataset spans
        thousands of years with only a few events.
        """
        items: List[EventIndex] = []
        for thread in self._left_threads + self._right_threads:
            if sources is None or thread.source in sources:
                items.extend(thread.events)

        if not items:
            return

        times = sorted(
            item.since.value for item in items if item.since is not None
        )
        if len(times) < 2:
            self.coord.center_time = JDNTimestamp(times[0])
            one_year_us = int(365.2425 * 24 * 3600 * 1_000_000)
            self.coord.scale = max(1e-15, 100.0 / one_year_us)
            self._arrange_threads()
            self.update()
            return

        # Find the closest pair of events and center on it.
        gaps = [(times[i + 1] - times[i], times[i], times[i + 1])
                for i in range(len(times) - 1)]
        smallest_gap, t0, t1 = min(gaps, key=lambda x: x[0])

        # Show a window around that cluster (at least ~20 years, at most
        # a modest multiple of the gap).
        one_year_us = int(365.2425 * 24 * 3600 * 1_000_000)
        min_window_us = 20 * one_year_us
        window_us = max(min_window_us, smallest_gap * 20)

        vp = self.coord.viewport()
        if vp.length <= 0:
            return

        self.coord.center_time = JDNTimestamp((t0 + t1) // 2)
        self.coord.scale = max(1e-15, vp.length / window_us)
        self._arrange_threads()
        self.update()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _arrange_threads(self) -> None:
        """Recompute transverse ranges and track layouts for all threads."""
        vp = self.coord.viewport()
        available = max(0, vp.breadth / 2 - AXIS_BREADTH / 2)
        half_len = vp.length / 2

        def arrange_side(threads: List[ThreadLayout], positive: bool):
            count = len(threads)
            if count == 0:
                return
            width = available / count
            for i, thread in enumerate(threads):
                if positive:
                    y0 = AXIS_BREADTH / 2 + i * width
                    y1 = y0 + width
                else:
                    y1 = -(AXIS_BREADTH / 2 + i * width)
                    y0 = y1 - width
                thread.arrange(self.coord, (y0, y1))

        arrange_side(self._right_threads, positive=True)
        arrange_side(self._left_threads, positive=False)

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter

        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        qp.fillRect(self.rect(), self.bg_color)

        # 1. Axis geometry + labels.
        qp.setTransform(self.coord.transform())
        paint_axis(
            qp, self.coord, self.axis_color, self.tick_color, self.text_color, self.tick_font
        )

        # 2. Thread backgrounds and items.
        qp.setTransform(self.coord.transform())
        for thread in self._left_threads + self._right_threads:
            paint_thread_background(qp, self.coord, thread)
            for item in thread.items:
                paint_item(
                    qp,
                    self.coord,
                    item,
                    thread.item_color,
                    self.item_text_color,
                    self.item_font,
                )

        qp.end()

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_last_pos = QPointF(event.pos())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = QPointF(event.pos())

        if self._drag_last_pos is not None:
            # Pan along the time axis: horizontal in horizontal mode, vertical
            # in vertical mode.
            if self.coord.is_vertical:
                delta_screen = pos.y() - self._drag_last_pos.y()
            else:
                delta_screen = pos.x() - self._drag_last_pos.x()
            delta_us = int(delta_screen / self.coord.scale)
            self.coord.center_time = JDNTimestamp(
                self.coord.center_time.value - delta_us
            )
            self._drag_last_pos = pos
            self._arrange_threads()
            self.update()
        else:
            self._update_hover(pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_last_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        item = self._item_at_screen(QPointF(event.pos()))
        if item is not None:
            self.itemDoubleClicked.emit(item.event)

    def contextMenuEvent(self, event: QContextMenuEvent):
        pos = event.pos()
        item = self._item_at_screen(QPointF(pos))
        self.contextMenuRequested.emit(event.globalPos(), item.event if item else None)

    def wheelEvent(self, event: QWheelEvent):
        angle = event.angleDelta().y()
        pos = QPointF(event.position())

        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            # Zoom centered on mouse.
            old_scale = self.coord.scale
            factor = 1.2 if angle > 0 else 1 / 1.2
            new_scale = max(1e-15, min(self.coord.scale * factor, 1e-3))

            logical_mouse = self.coord.screen_to_logical(pos)
            mouse_time = self.coord.logical_x_to_time(logical_mouse.x())

            self.coord.scale = new_scale
            # Preserve: logical_mouse.x = (mouse_time - new_center) * new_scale
            new_center_value = mouse_time.value - logical_mouse.x() / new_scale
            self.coord.center_time = JDNTimestamp(int(new_center_value))
        else:
            scroll_px = angle
            delta_us = int(scroll_px / self.coord.scale)
            self.coord.center_time = JDNTimestamp(
                self.coord.center_time.value - delta_us
            )

        self._arrange_threads()
        self.update()

    def resizeEvent(self, event):
        self._arrange_threads()
        super().resizeEvent(event)

    # ------------------------------------------------------------------
    # Hover / hit testing
    # ------------------------------------------------------------------

    def _update_hover(self, screen_pos: QPointF):
        item = self._item_at_screen(screen_pos)
        if item is not None:
            if self._hover_item != item.event:
                self._hover_item = item.event
                self.setToolTip(self._tooltip_text(item.event))
                self.update()
        else:
            if self._hover_item is not None:
                self._hover_item = None
                self.setToolTip("")
                self.update()

    def _item_at_screen(self, screen_pos: QPointF):
        logical_pos = self.coord.screen_to_logical(screen_pos)
        for thread in self._left_threads + self._right_threads:
            item = thread.item_at_logical(logical_pos)
            if item is not None:
                return item
        return None

    @staticmethod
    def _tooltip_text(event: EventIndex) -> str:
        y, m, d, *_ = event.since.to_gregorian()
        era = "BC" if y <= 0 else "AD"
        display_year = -(y - 1) if y <= 0 else y
        time_text = f"{display_year} {era}-{m:02d}-{d:02d}"
        if event.is_point_event():
            return f"{time_text}\n{event.abstract}"
        ye, me, de, *_ = event.until.to_gregorian()
        era_e = "BC" if ye <= 0 else "AD"
        display_year_e = -(ye - 1) if ye <= 0 else ye
        return f"{time_text} ~ {display_year_e} {era_e}-{me:02d}-{de:02d}\n{event.abstract}"

    # ------------------------------------------------------------------
    # Workspace slots
    # ------------------------------------------------------------------

    def _on_event_added(self, event: Event):
        self.refresh_source(event.source)

    def _on_event_updated(self, event: Event):
        self.refresh_source(event.source)

    def _on_event_removed(self, uuid: str):
        # We don't know the source from the uuid alone; refresh all bound sources.
        sources = {t.source for t in self._left_threads + self._right_threads if t.source}
        for source in sources:
            self.refresh_source(source)

    def _on_source_loaded(self, source: str):
        self.refresh_source(source)
