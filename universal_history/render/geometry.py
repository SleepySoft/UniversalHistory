"""
Geometry / coordinate system for the timeline viewer.

Keeps the same unified-coordinate idea as UniversalTimeAxis:
- logical X is always the time axis,
- logical Y is perpendicular to the time axis,
- a QTransform maps logical coordinates to screen coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from PyQt6.QtCore import QPointF, QSize
from PyQt6.QtGui import QTransform
from universal_history.chrono.jdn_timestamp import JDNTimestamp


# Pixels reserved for the central axis strip.  This constant is used by both
# the coordinate system (to compute left/right space budgets) and the timeline
# view (to lay out threads).
AXIS_BREADTH = 30


@dataclass
class Viewport:
    """Logical viewport dimensions."""

    length: float  # along the time axis
    breadth: float  # perpendicular to the time axis


class CoordinateSystem:
    """
    Manages the mapping between JDNTimestamp, logical coordinates and screen
    pixels for both horizontal and vertical layouts.
    """

    def __init__(self, parent_widget=None):
        self._widget = parent_widget
        self._size: QSize = QSize(800, 600)
        self.is_vertical = False
        self.center_time = JDNTimestamp.from_ymd_hms(2000, 1, 1, 12, 0, 0)
        # Default scale: 200 px per year
        one_year_us = 365.2425 * 24 * 3600 * 1_000_000
        self.scale = 200.0 / one_year_us  # px / us

        # Layout anchor: logical X coordinates cached by ThreadLayout are
        # relative to this time, NOT to center_time.  Panning only changes
        # center_time; the resulting drift is applied inside transform() so
        # cached item geometry moves with the axis without re-layout.  The
        # anchor is re-synced to center_time on every arrange (zoom, resize,
        # data change, or large-drift re-anchor in the view).
        self._anchor_time = self.center_time

        # Axis offset within the available transverse space.
        # 0.0 -> axis at the near edge (left/top side gets 0 space).
        # 0.5 -> axis centered (default).
        # 1.0 -> axis at the far edge (right/bottom side gets 0 space).
        self.axis_offset = 0.5

    # ------------------------------------------------------------------
    # Viewport
    # ------------------------------------------------------------------

    def widget_size(self) -> QSize:
        if self._widget is not None:
            return self._widget.size()
        return self._size

    def set_widget_size(self, width: int, height: int) -> None:
        """Set the virtual widget size (useful for unit tests)."""
        self._size = QSize(width, height)

    def viewport(self) -> Viewport:
        size = self.widget_size()
        if self.is_vertical:
            return Viewport(length=size.height(), breadth=size.width())
        return Viewport(length=size.width(), breadth=size.height())

    def half_length(self) -> float:
        return self.viewport().length / 2

    def half_breadth(self) -> float:
        return self.viewport().breadth / 2

    # ------------------------------------------------------------------
    # Time <-> logical coordinate
    # ------------------------------------------------------------------

    @property
    def anchor_time(self) -> JDNTimestamp:
        """Time the cached layout coordinates are relative to."""
        return self._anchor_time

    def set_anchor(self, ts: JDNTimestamp) -> None:
        """Re-sync the layout anchor (call whenever the layout is recomputed)."""
        self._anchor_time = ts

    def center_logical_x(self) -> float:
        """Logical X of the current view centre (0 right after an arrange)."""
        return (self.center_time.value - self._anchor_time.value) * self.scale

    def time_to_logical_x(self, ts: JDNTimestamp) -> float:
        """Return logical X coordinate for a JDNTimestamp (anchor-relative)."""
        return (ts.value - self._anchor_time.value) * self.scale

    def logical_x_to_time_value(self, x: float) -> int:
        """Return the raw microsecond value corresponding to logical X."""
        return int(self._anchor_time.value + x / self.scale)

    def logical_x_to_time(self, x: float) -> JDNTimestamp:
        return JDNTimestamp(self.logical_x_to_time_value(x))

    def visible_time_range(self) -> Tuple[JDNTimestamp, JDNTimestamp]:
        half = self.half_length()
        start_val = self.center_time.value - int(half / self.scale)
        end_val = self.center_time.value + int(half / self.scale)
        return JDNTimestamp(start_val), JDNTimestamp(end_val)

    # ------------------------------------------------------------------
    # Screen <-> logical coordinate transform
    # ------------------------------------------------------------------

    def axis_screen_center(self) -> float:
        """Return the screen pixel coordinate of the axis centre line."""
        vp = self.viewport()
        return AXIS_BREADTH / 2 + self.axis_offset * (vp.breadth - AXIS_BREADTH)

    def thread_budgets(self) -> Tuple[float, float]:
        """Return the available transverse pixels on each side of the axis.

        Returns (left_budget, right_budget) in screen/logical units.  Either
        value may be zero if the axis is pushed to one edge.
        """
        center = self.axis_screen_center()
        breadth = self.viewport().breadth
        left = max(0.0, center - AXIS_BREADTH / 2)
        right = max(0.0, breadth - center - AXIS_BREADTH / 2)
        return left, right

    def transform(self) -> QTransform:
        size = self.widget_size()
        t = QTransform()
        axis_center = self.axis_screen_center()
        # Pan drift: cached layout coordinates are anchor-relative, so the
        # transform must shift logical X by (anchor - center) * scale to make
        # items follow the axis while panning without re-layout.
        dx = (self._anchor_time.value - self.center_time.value) * self.scale
        if self.is_vertical:
            # Time axis runs vertically; the transverse axis is horizontal.
            t.translate(axis_center, size.height() / 2)
            t.rotate(90)
            # Applied before the rotation: shifts along the logical time axis.
            t.translate(dx, 0)
        else:
            # Time axis runs horizontally; the transverse axis is vertical.
            t.translate(size.width() / 2 + dx, axis_center)
        return t

    def logical_to_screen(self, p: QPointF) -> QPointF:
        return self.transform().map(p)

    def screen_to_logical(self, p: QPointF) -> QPointF:
        inv, ok = self.transform().inverted()
        if not ok:
            return QPointF(0, 0)
        return inv.map(p)

    # ------------------------------------------------------------------
    # helpers for layout
    # ------------------------------------------------------------------

    def pixel_to_logical_distance(self, px: float) -> float:
        """Convert a screen pixel distance to logical distance along X."""
        return px / self.scale

    def logical_to_pixel_distance(self, dist: float) -> float:
        return dist * self.scale
