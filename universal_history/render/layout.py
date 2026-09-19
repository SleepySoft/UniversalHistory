"""
Thread / Track layout engine for the timeline viewer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor

from universal_history.models import EventIndex
from universal_history.render.geometry import CoordinateSystem


# Visual design constants
POINT_EVENT_PIXEL_WIDTH = 120.0  # fixed on-screen width for a point-event chip
POINT_EVENT_PIXEL_HEIGHT = 24.0
EVENT_MARGIN_PIXELS = 6.0
MIN_TRACK_WIDTH = 50.0


@dataclass
class ItemLayout:
    """Layout information for a single event inside a thread."""

    event: EventIndex
    x0: float  # logical start along time axis
    x1: float  # logical end along time axis
    y0: float  # logical transverse start
    y1: float  # logical transverse end
    is_point: bool

    def rect(self) -> QRectF:
        return QRectF(self.x0, self.y0, self.x1 - self.x0, self.y1 - self.y0)

    def screen_rect(self, coord: CoordinateSystem) -> QRectF:
        """Bounding rect in screen coordinates."""
        rect = self.rect()
        pts = [
            coord.logical_to_screen(QPointF(rect.left(), rect.top())),
            coord.logical_to_screen(QPointF(rect.right(), rect.top())),
            coord.logical_to_screen(QPointF(rect.right(), rect.bottom())),
            coord.logical_to_screen(QPointF(rect.left(), rect.bottom())),
        ]
        xs = [p.x() for p in pts]
        ys = [p.y() for p in pts]
        return QRectF(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


@dataclass
class Track:
    """A single track (lane) inside a thread."""

    index: int
    y0: float
    y1: float
    occupied: List[Tuple[float, float]] = field(default_factory=list)

    def has_space(self, x0: float, x1: float) -> bool:
        """Check whether [x0, x1] does not overlap any existing item."""
        for a, b in self.occupied:
            if not (x1 <= a or x0 >= b):
                return False
        return True

    def take(self, x0: float, x1: float) -> None:
        self.occupied.append((x0, x1))


class ThreadLayout:
    """
    Layout for one thread (left or right side of the axis).

    Given a list of EventIndex items, it distributes them across tracks so that
    overlapping items in time are placed on different lanes.
    """

    def __init__(
        self,
        align: str = "right",
        min_track_width: float = MIN_TRACK_WIDTH,
        share: float = 1.0,
        track_color: QColor = None,
        item_color: QColor = None,
        source: str = "",
    ):
        if align not in ("left", "right"):
            raise ValueError("align must be 'left' or 'right'")
        self.align = align
        self.source = source
        self.min_track_width = min_track_width
        self.share = max(0.0, min(1.0, float(share)))
        self.track_color = track_color or QColor(240, 240, 240)
        self.item_color = item_color or QColor(185, 227, 217)
        self.events: List[EventIndex] = []
        self.items: List[ItemLayout] = []
        self.tracks: List[Track] = []
        self.y0 = 0.0
        self.y1 = 0.0

    def set_events(self, events: List[EventIndex]) -> None:
        self.events = list(events)
        self.items.clear()

    def set_min_track_width(self, width: float) -> None:
        """Set the minimum track width for this thread."""
        self.min_track_width = max(1.0, float(width))

    def set_share(self, share: float) -> None:
        """Set this thread's share (0.0~1.0) of its side's total space."""
        self.share = max(0.0, min(1.0, float(share)))

    def arrange(
        self,
        coord: CoordinateSystem,
        transverse_range: Tuple[float, float],
    ) -> None:
        """
        Compute the layout within the given transverse range.

        transverse_range: (y0, y1) in logical coordinates, perpendicular to the
        time axis. For a right-side thread y0 >= 0; for left-side y1 <= 0.
        """
        self.y0, self.y1 = transverse_range
        thread_width = abs(self.y1 - self.y0)
        track_count = max(1, int(thread_width / self.min_track_width + 0.5))
        track_height = thread_width / track_count

        self.tracks = []
        # Track 0 is always the axis-adjacent lane: for negative-side ranges
        # the axis is at the y1 (high) edge, for positive ranges at y0.
        # Without this, above-axis threads filled from the far edge and
        # stacked inconsistently with vertical mode (user report 2026-09-19).
        axis_at_high_edge = self.y1 <= 0
        for i in range(track_count):
            if axis_at_high_edge:
                base = self.y1 - (i + 1) * track_height
            else:
                base = self.y0 + i * track_height
            self.tracks.append(Track(i, base, base + track_height))

        # Sort by duration (longer first) for stable layout.
        sorted_events = sorted(
            self.events,
            key=lambda e: (
                -(e.until.value - e.since.value) if e.until and e.since else 0,
                e.since.value if e.since else 0,
            ),
        )

        # x0/x1 are in logical pixels (screen pixels before the final
        # orientation transform). Margins are therefore constant pixels.
        margin_logical = EVENT_MARGIN_PIXELS

        self.items.clear()
        for event in sorted_events:
            if event.since is None or event.until is None:
                continue

            is_point = event.is_point_event()
            time_x = coord.time_to_logical_x(event.since)

            if is_point:
                # Lollipop anchor (2026-09-19 redesign): the card's left edge
                # IS the event instant — the stem/axis-dot drawn by the
                # painter connects the card to that exact point on the axis.
                x0 = time_x
                x1 = time_x + POINT_EVENT_PIXEL_WIDTH
            else:
                x0 = coord.time_to_logical_x(event.since)
                x1 = coord.time_to_logical_x(event.until)

            if x1 < x0:
                x0, x1 = x1, x0

            # Add margin for visual separation.
            x0 -= margin_logical
            x1 += margin_logical

            placed = False
            for track in self.tracks:
                if track.has_space(x0, x1):
                    track.take(x0, x1)
                    self.items.append(
                        ItemLayout(
                            event=event,
                            x0=x0 + margin_logical,  # store without margin for drawing
                            x1=x1 - margin_logical,
                            y0=track.y0,
                            y1=track.y1,
                            is_point=is_point,
                        )
                    )
                    placed = True
                    break

            if not placed:
                # Fallback: place in the last track (overlap allowed).
                track = self.tracks[-1]
                track.take(x0, x1)
                self.items.append(
                    ItemLayout(
                        event=event,
                        x0=x0 + margin_logical,
                        x1=x1 - margin_logical,
                        y0=track.y0,
                        y1=track.y1,
                        is_point=is_point,
                    )
                )

    def item_at_logical(self, pos: QPointF) -> ItemLayout:
        """Return the topmost item containing the logical point, or None."""
        for item in reversed(self.items):
            if item.rect().contains(pos):
                return item
        return None
