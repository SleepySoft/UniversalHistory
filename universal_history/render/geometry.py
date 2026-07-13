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

    def time_to_logical_x(self, ts: JDNTimestamp) -> float:
        """Return logical X coordinate for a JDNTimestamp."""
        return (ts.value - self.center_time.value) * self.scale

    def logical_x_to_time_value(self, x: float) -> int:
        """Return the raw microsecond value corresponding to logical X."""
        return int(self.center_time.value + x / self.scale)

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

    def transform(self) -> QTransform:
        size = self.widget_size()
        t = QTransform()
        # Center the logical origin on the widget, then rotate for vertical mode.
        t.translate(size.width() / 2, size.height() / 2)
        if self.is_vertical:
            # Rotate so the time axis runs vertically (top = past, bottom = future).
            t.rotate(90)
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
