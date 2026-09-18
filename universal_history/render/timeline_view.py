"""
TimelineView: the main timeline widget.

Combines the central time axis with left/right threads and handles pan/zoom
and item hover/selection.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import QCoreApplication, QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QContextMenuEvent, QFont, QKeyEvent, QMouseEvent, QWheelEvent
from PyQt6.QtCore import QPoint
from universal_history.chrono.jdn_timestamp import JDNTimestamp
from PyQt6.QtWidgets import QApplication, QWidget

from universal_history.models import Event, EventIndex, Workspace
from universal_history.render.geometry import AXIS_BREADTH, CoordinateSystem
from universal_history.render.layout import MIN_TRACK_WIDTH, ThreadLayout


# Color palette borrowed from the reference History project.
# Thread backgrounds are warm/muted lanes; item colors are used for period bars.
THREAD_BACKGROUNDS = [
    QColor(182, 194, 154),
    QColor(138, 151, 123),
    QColor(244, 208, 0),
    QColor(229, 87, 18),
    QColor(178, 200, 187),
    QColor(69, 137, 148),
    QColor(117, 121, 74),
    QColor(114, 83, 52),
    QColor(130, 57, 53),
    QColor(137, 190, 178),
    QColor(201, 211, 140),
    QColor(222, 156, 83),
    QColor(160, 90, 124),
    QColor(101, 147, 74),
    QColor(64, 116, 52),
    QColor(222, 125, 44),
]

ITEM_COLORS = [
    QColor(185, 227, 217),
    QColor(252, 157, 154),
    QColor(249, 205, 173),
    QColor(200, 200, 169),
    QColor(131, 175, 155),
    QColor(255, 245, 247),
]
from universal_history.render.painter import (
    item_in_time_range, paint_axis, paint_item, paint_thread_background,
)




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

        self.bg_color = QColor(255, 245, 247)
        self.axis_color = QColor(120, 120, 120)
        self.tick_color = QColor(100, 100, 100)
        self.text_color = QColor(50, 50, 50)
        self.item_text_color = QColor(30, 30, 30)
        self.tick_font = QFont("Segoe UI", 9)
        self.item_font = QFont("微软雅黑", 8)

        self._left_threads: List[ThreadLayout] = []
        self._right_threads: List[ThreadLayout] = []
        self._workspace: Optional[Workspace] = None

        self._drag_last_pos: Optional[QPointF] = None
        self._hover_item: Optional[EventIndex] = None
        # Year under the cursor for the period-progress tooltip ("Year N of M");
        # tracked so the tooltip refreshes as the cursor moves within one item.
        self._hover_year: Optional[int] = None

        # Arrow-key smooth scrolling (restored from legacy History main.py,
        # whose implementation was broken — legacy defect #12).
        self._scroll_keys: set = set()
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(50)
        self._scroll_timer.timeout.connect(self._on_scroll_timer)

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

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
                self._workspace.source_removed.disconnect(self._on_source_removed)
            except Exception:
                pass
        self._workspace = workspace
        workspace.event_added.connect(self._on_event_added)
        workspace.event_updated.connect(self._on_event_updated)
        workspace.event_removed.connect(self._on_event_removed)
        workspace.source_loaded.connect(self._on_source_loaded)
        workspace.source_removed.connect(self._on_source_removed)
        if source is not None:
            self.load_source(source)

    def load_source(
        self,
        source: str,
        align: str = "right",
        track_color: QColor = None,
        item_color: QColor = None,
        min_track_width: float = MIN_TRACK_WIDTH,
    ) -> ThreadLayout:
        """Add a thread displaying all events from a workspace source."""
        if self._workspace is None:
            raise RuntimeError("Call set_workspace() before load_source()")
        events = [e.to_index() for e in self._workspace.events(source)]
        return self.add_thread(
            events,
            align=align,
            source=source,
            track_color=track_color,
            item_color=item_color,
            min_track_width=min_track_width,
        )

    def _next_palette_index(self) -> int:
        return len(self._left_threads) + len(self._right_threads)

    def _pick_thread_colors(self) -> (QColor, QColor):
        idx = self._next_palette_index()
        return (
            THREAD_BACKGROUNDS[idx % len(THREAD_BACKGROUNDS)],
            ITEM_COLORS[idx % len(ITEM_COLORS)],
        )

    def _side_threads(self, align: str) -> List[ThreadLayout]:
        return self._left_threads if align == "left" else self._right_threads

    @staticmethod
    def _normalize_shares(threads: List[ThreadLayout]) -> None:
        """Scale thread shares so they sum to 1.0."""
        total = sum(t.share for t in threads)
        if total <= 0:
            for t in threads:
                t.share = 1.0 / max(1, len(threads))
            return
        for t in threads:
            t.share = t.share / total

    def _insert_thread_with_equal_share(
        self, thread: ThreadLayout, align: str
    ) -> None:
        """Append a thread and give every thread on that side an equal share."""
        side = self._side_threads(align)
        side.append(thread)
        share = 1.0 / len(side)
        for t in side:
            t.share = share

    def add_thread(
        self,
        events: List[EventIndex],
        align: str = "right",
        track_color: QColor = None,
        item_color: QColor = None,
        source: str = "",
        min_track_width: float = MIN_TRACK_WIDTH,
    ) -> ThreadLayout:
        if track_color is None or item_color is None:
            default_track, default_item = self._pick_thread_colors()
            track_color = track_color or default_track
            item_color = item_color or default_item
        thread = ThreadLayout(
            align=align,
            track_color=track_color,
            item_color=item_color,
            source=source,
            min_track_width=min_track_width,
        )
        thread.set_events(events)
        self._insert_thread_with_equal_share(thread, align)
        self._arrange_threads()
        self.update()
        return thread

    def refresh_source(self, source: str) -> None:
        """Reload all threads bound to a given source."""
        if self._workspace is None or not source:
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

    def left_threads(self) -> List[ThreadLayout]:
        return list(self._left_threads)

    def right_threads(self) -> List[ThreadLayout]:
        return list(self._right_threads)

    def set_thread_share(self, thread: ThreadLayout, share: float) -> bool:
        """Set a thread's share and renormalize the rest of its side to sum 1."""
        side = self._side_threads(thread.align)
        if thread not in side:
            return False
        if len(side) <= 1:
            thread.share = 1.0
            self._arrange_threads()
            self.update()
            return True
        thread.set_share(share)
        others = [t for t in side if t is not thread]
        remaining = 1.0 - thread.share
        other_total = sum(t.share for t in others)
        if other_total <= 0:
            for t in others:
                t.share = remaining / len(others)
        else:
            scale = remaining / other_total
            for t in others:
                t.share = max(0.001, t.share * scale)
        # Final normalization to fix any rounding/clamping drift.
        self._normalize_shares(side)
        self._arrange_threads()
        self.update()
        return True

    def remove_thread(self, thread: ThreadLayout) -> bool:
        """Remove a thread from either side and renormalize shares."""
        if thread in self._left_threads:
            self._left_threads.remove(thread)
            self._normalize_shares(self._left_threads)
        elif thread in self._right_threads:
            self._right_threads.remove(thread)
            self._normalize_shares(self._right_threads)
        else:
            return False
        self._arrange_threads()
        self.update()
        return True

    def move_thread(self, thread: ThreadLayout, delta: int) -> bool:
        """Move a thread up/down within its side list."""
        lst = self._left_threads if thread in self._left_threads else self._right_threads
        if thread not in lst:
            return False
        idx = lst.index(thread)
        new_idx = idx + delta
        if 0 <= new_idx < len(lst):
            lst[idx], lst[new_idx] = lst[new_idx], lst[idx]
            self._arrange_threads()
            self.update()
            return True
        return False

    def switch_thread_side(self, thread: ThreadLayout) -> bool:
        """Move a thread from left to right or vice versa, renormalizing shares."""
        if thread in self._left_threads:
            self._left_threads.remove(thread)
            self._normalize_shares(self._left_threads)
            thread.align = "right"
            self._insert_thread_with_equal_share(thread, "right")
        elif thread in self._right_threads:
            self._right_threads.remove(thread)
            self._normalize_shares(self._right_threads)
            thread.align = "left"
            self._insert_thread_with_equal_share(thread, "left")
        else:
            return False
        self._arrange_threads()
        self.update()
        return True

    def set_thread_events(self, thread: ThreadLayout, events: List[EventIndex]) -> None:
        thread.set_events(events)
        self._arrange_threads()
        self.update()

    def toggle_orientation(self) -> None:
        self.coord.is_vertical = not self.coord.is_vertical
        self._arrange_threads()
        self.update()

    def relayout(self) -> None:
        """Public relayout hook: recompute thread geometry and repaint.

        External dialogs (e.g. ThreadManagerDialog) must call this instead of
        the private `_arrange_threads()`.
        """
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

        since_values = [item.since.value for item in items if item.since is not None]
        until_values = [item.until.value for item in items if item.until is not None]
        if not since_values or not until_values:
            # No timed events at all: nothing meaningful to fit to.
            return

        min_time = min(since_values)
        max_time = max(until_values)

        vp = self.coord.viewport()
        if vp.length <= 0:
            return

        self.coord.center_time = JDNTimestamp((min_time + max_time) // 2)
        range_us = max_time - min_time
        # Ensure at least a sensible minimum range for point-only data
        # (including datasets where every event sits at the same instant).
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
        left_budget, right_budget = self.coord.thread_budgets()
        half_len = vp.length / 2

        def arrange_side(threads: List[ThreadLayout], positive: bool, budget: float):
            count = len(threads)
            if count == 0 or budget <= 0:
                return
            cursor = AXIS_BREADTH / 2
            for thread in threads:
                width = budget * thread.share
                if width <= 0:
                    continue
                if positive:
                    y0 = cursor
                    y1 = cursor + width
                else:
                    y1 = -cursor
                    y0 = y1 - width
                thread.arrange(self.coord, (y0, y1))
                cursor += width

        # In horizontal mode, right threads use logical +Y (screen bottom/right
        # depending on orientation).  In vertical mode the 90° rotation flips the
        # screen mapping, so we swap the logical side to keep "right" visually on
        # the right and "left" on the left.
        if self.coord.is_vertical:
            arrange_side(self._right_threads, positive=False, budget=right_budget)
            arrange_side(self._left_threads, positive=True, budget=left_budget)
        else:
            arrange_side(self._right_threads, positive=True, budget=right_budget)
            arrange_side(self._left_threads, positive=False, budget=left_budget)

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

        # 2. Thread backgrounds and items (paint only what is visible —
        # layout stays uncullable for track stability, known-issues #19).
        start, end = self.coord.visible_time_range()
        margin_us = int(120 / self.coord.scale) if self.coord.scale else 0
        qp.setTransform(self.coord.transform())
        for thread in self._left_threads + self._right_threads:
            paint_thread_background(qp, self.coord, thread)
            for item in thread.items:
                if not item_in_time_range(item, start, end, margin_us):
                    continue
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
            # Pure panning does not change track assignment (layout is
            # translation-invariant), so skip re-layout and just repaint.
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
            # Pan by a fraction of the visible span per wheel notch, so the
            # scroll speed adapts to the current zoom level instead of being
            # a raw pixel delta.
            steps = angle / 120.0
            vp = self.coord.viewport()
            if vp.length > 0:
                visible_us = vp.length / self.coord.scale
                delta_us = int(steps * visible_us * 0.1)
                self.coord.center_time = JDNTimestamp(
                    self.coord.center_time.value - delta_us
                )

        self._arrange_threads()
        self.update()

    def resizeEvent(self, event):
        self._arrange_threads()
        super().resizeEvent(event)

    # ------------------------------------------------------------------
    # Keyboard smooth scrolling
    # ------------------------------------------------------------------

    _SCROLL_KEYS = (
        Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right,
    )

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in self._SCROLL_KEYS:
            if not event.isAutoRepeat():
                self._scroll_keys.add(event.key())
                if not self._scroll_timer.isActive():
                    self._scroll_timer.start()
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() in self._SCROLL_KEYS:
            if not event.isAutoRepeat():
                self._scroll_keys.discard(event.key())
                if not self._scroll_keys:
                    self._scroll_timer.stop()
            event.accept()
            return
        super().keyReleaseEvent(event)

    def _on_scroll_timer(self):
        """
        Pan while arrow keys are held. Up/Down move a small step (5% of the
        visible span per tick), Left/Right move a full page — matching the
        legacy intent (small step vs page step) but speed adapts to zoom.
        """
        vp = self.coord.viewport()
        if vp.length <= 0:
            return
        visible_us = vp.length / self.coord.scale
        delta_us = 0
        if Qt.Key.Key_Up in self._scroll_keys:
            delta_us -= visible_us * 0.05
        if Qt.Key.Key_Down in self._scroll_keys:
            delta_us += visible_us * 0.05
        if Qt.Key.Key_Left in self._scroll_keys:
            delta_us -= visible_us
        if Qt.Key.Key_Right in self._scroll_keys:
            delta_us += visible_us
        if delta_us:
            self.coord.center_time = JDNTimestamp(
                int(self.coord.center_time.value + delta_us)
            )
            self.update()

    # ------------------------------------------------------------------
    # Hover / hit testing
    # ------------------------------------------------------------------

    def _update_hover(self, screen_pos: QPointF):
        item = self._item_at_screen(screen_pos)
        if item is None:
            if self._hover_item is not None:
                self._hover_item = None
                self._hover_year = None
                self.setToolTip("")
                self.update()
            return

        hover_year = None
        if not item.event.is_point_event():
            logical_pos = self.coord.screen_to_logical(screen_pos)
            hover_time = self.coord.logical_x_to_time(logical_pos.x())
            hover_year = hover_time.to_gregorian()[0]

        if self._hover_item != item.event or hover_year != self._hover_year:
            self._hover_item = item.event
            self._hover_year = hover_year
            self.setToolTip(self._tooltip_text(item.event, hover_year))
            self.update()

    @classmethod
    def _period_progress(cls, event: EventIndex, hover_year: int) -> str:
        """Legacy-style period progress at the cursor: 'Year N of M'
        (legacy showed 「第N年/共M年」). Year math uses astronomical years;
        the cursor position is clamped into the event's range."""
        since_year = event.since.to_gregorian()[0]
        until_year = event.until.to_gregorian()[0]
        total = until_year - since_year + 1
        current = min(max(hover_year, since_year), until_year) - since_year + 1
        return QCoreApplication.translate("TimelineView", "Year %1 of %2") \
            .replace("%1", str(current)).replace("%2", str(total))

    def thread_at_screen(self, screen_pos: QPointF) -> Optional[ThreadLayout]:
        """Return the thread whose item is under the screen point, or None."""
        logical_pos = self.coord.screen_to_logical(screen_pos)
        for thread in self._left_threads + self._right_threads:
            if thread.item_at_logical(logical_pos) is not None:
                return thread
        return None

    def side_at_screen(self, screen_pos: QPointF) -> str:
        """Return 'left' or 'right' for the side under the screen point."""
        center = self.coord.axis_screen_center()
        if self.coord.is_vertical:
            return "left" if screen_pos.x() < center else "right"
        return "left" if screen_pos.y() < center else "right"

    def _item_at_screen(self, screen_pos: QPointF):
        logical_pos = self.coord.screen_to_logical(screen_pos)
        # Cull threads' items outside the visible range before hit-testing
        # (known-issues #19); item_at_logical still does the precise check.
        start, end = self.coord.visible_time_range()
        margin_us = int(120 / self.coord.scale) if self.coord.scale else 0
        for thread in self._left_threads + self._right_threads:
            for item in thread.items:
                if not item_in_time_range(item, start, end, margin_us):
                    continue
                if item.rect().contains(logical_pos):
                    return item
        return None

    @classmethod
    def _tooltip_text(cls, event: EventIndex, hover_year: Optional[int] = None) -> str:
        y, m, d, *_ = event.since.to_gregorian()
        era = "BC" if y <= 0 else "AD"
        display_year = -(y - 1) if y <= 0 else y
        time_text = f"{display_year} {era}-{m:02d}-{d:02d}"
        if event.is_point_event():
            return f"{time_text}\n{event.abstract}"
        ye, me, de, *_ = event.until.to_gregorian()
        era_e = "BC" if ye <= 0 else "AD"
        display_year_e = -(ye - 1) if ye <= 0 else ye
        text = f"{time_text} ~ {display_year_e} {era_e}-{me:02d}-{de:02d}\n{event.abstract}"
        if hover_year is not None:
            text += f"\n{cls._period_progress(event, hover_year)}"
        return text

    # ------------------------------------------------------------------
    # Workspace slots
    # ------------------------------------------------------------------

    def _on_event_added(self, event: Event):
        self.refresh_source(event.source)

    def _on_event_updated(self, event: Event):
        self.refresh_source(event.source)

    def _on_event_removed(self, uuid: str):
        # The removal signal carries only the uuid; locate the affected
        # thread(s) via their (still stale) event lists and refresh just
        # those sources instead of everything.
        for thread in self._left_threads + self._right_threads:
            if thread.source and any(e.uuid == uuid for e in thread.events):
                self.refresh_source(thread.source)

    def _on_source_loaded(self, source: str):
        self.refresh_source(source)

    def _on_source_removed(self, source: str):
        # The source is gone from the workspace; refreshing clears any
        # thread still bound to it.
        self.refresh_source(source)
