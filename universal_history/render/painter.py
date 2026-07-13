"""
Painting helpers for the timeline viewer.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.chrono.tick_stepper import TickLevel, TickStepper
from universal_history.render.geometry import CoordinateSystem
from universal_history.render.layout import ItemLayout, ThreadLayout


AXIS_LINE_WIDTH = 2
TICK_LENGTH = 6
LABEL_OFFSET = 12


def _format_tick_label(tick: JDNTimestamp, level: TickLevel) -> str:
    y, m, d, h, mn, s, _ = tick.to_gregorian()

    era_suffix = ""
    display_year = y
    if y <= 0:
        display_year = -(y - 1)
        era_suffix = " BC"

    if level.unit == "Year":
        if level.step_count >= 1000:
            return f"{display_year}{era_suffix}"
        return f"{display_year}{era_suffix}"

    if level.unit == "Month":
        if m == 1:
            return f"{display_year}{era_suffix}"
        months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return months[m]

    if level.unit == "Day":
        if d == 1:
            return f"{m:02d}/{display_year}"
        return f"{d}"

    return str(tick)


def _visible_ticks(
    coord: CoordinateSystem, target_px: float = 120.0
) -> Tuple[TickLevel, list]:
    """Choose a tick level and generate ticks for the visible range."""
    start, end = coord.visible_time_range()
    if end <= start:
        return TickStepper.LEVELS[-1], []

    # target spacing in microseconds
    target_us = target_px / coord.scale

    level = TickStepper.LEVELS[-1]
    for candidate in TickStepper.LEVELS:
        if candidate.avg_duration_us >= target_us:
            level = candidate
            break

    ticks = []
    current = TickStepper.snap_to_grid(start, level)
    safety = 0
    while current < end and safety < 200:
        if current >= start:
            ticks.append(current)
        current = TickStepper.get_next_tick(current, level)
        safety += 1
        if current <= start and safety > 1:
            break

    return level, ticks


def paint_axis(
    qp: QPainter,
    coord: CoordinateSystem,
    axis_color: QColor,
    tick_color: QColor,
    text_color: QColor,
    font: QFont,
) -> None:
    """Paint the central axis line and tick labels."""
    vp = coord.viewport()
    half_len = vp.length / 2

    # Apply the unified logical coordinate transform for geometry.
    qp.setPen(QPen(axis_color, AXIS_LINE_WIDTH))
    qp.drawLine(QPointF(-half_len, 0), QPointF(half_len, 0))

    level, ticks = _visible_ticks(coord)

    qp.setPen(QPen(tick_color, 1))
    for tick in ticks:
        x = coord.time_to_logical_x(tick)
        qp.drawLine(QPointF(x, -TICK_LENGTH), QPointF(x, TICK_LENGTH))

    # Labels are drawn in screen coordinates so they stay upright.
    qp.resetTransform()
    qp.setFont(font)
    qp.setPen(text_color)
    fm = QFontMetrics(font)

    for tick in ticks:
        x = coord.time_to_logical_x(tick)
        # Place labels on the side of the axis that is not covered by threads
        # (above in horizontal mode, to the right in vertical mode).
        screen_pos = coord.logical_to_screen(QPointF(x, -LABEL_OFFSET))
        text = _format_tick_label(tick, level)

        if coord.is_vertical:
            # In vertical mode the label sits to the right of the tick.
            draw_x = screen_pos.x() + 4
            draw_y = screen_pos.y() + fm.ascent() / 2
        else:
            text_width = fm.horizontalAdvance(text)
            draw_x = screen_pos.x() - text_width / 2
            draw_y = screen_pos.y() + fm.ascent()

        qp.drawText(QPointF(draw_x, draw_y), text)


def paint_thread_background(
    qp: QPainter, coord: CoordinateSystem, thread: ThreadLayout
) -> None:
    """Paint the background area of a thread."""
    vp = coord.viewport()
    half_len = vp.length / 2
    rect = QRectF(-half_len, thread.y0, vp.length, thread.y1 - thread.y0)
    qp.fillRect(rect, thread.track_color)


def paint_item(
    qp: QPainter,
    coord: CoordinateSystem,
    item: ItemLayout,
    color: QColor,
    text_color: QColor,
    font: QFont,
) -> None:
    """Paint a single event item: rectangle in logical coords, text in screen."""
    rect = item.rect()

    # When a point event is zoomed far out, its fixed 120 px card would span
    # centuries and look like a period bar. In that case draw a thin marker.
    if item.is_point:
        one_year_us = int(365.2425 * 24 * 3600 * 1_000_000)
        point_span_us = rect.width() / coord.scale if coord.scale else 0
        if point_span_us > 2 * one_year_us:
            center_x = (rect.left() + rect.right()) / 2
            qp.setPen(QPen(color, 2))
            qp.drawLine(
                QPointF(center_x, rect.top()), QPointF(center_x, rect.bottom())
            )
            qp.setTransform(coord.transform())
            return

    # Draw the geometry with the logical transform active.
    radius = 4.0
    qp.setBrush(color)
    qp.setPen(QPen(color.darker(120), 1))
    qp.drawRoundedRect(rect, radius, radius)

    if item.is_point:
        # Mark the exact instant with a vertical pin line so point events are
        # visually distinguishable from period bars.
        center_x = (rect.left() + rect.right()) / 2
        qp.setPen(QPen(text_color, 1))
        qp.drawLine(
            QPointF(center_x, rect.top()), QPointF(center_x, rect.bottom())
        )

    # Draw text in screen coordinates so it is never rotated.
    qp.resetTransform()
    qp.setFont(font)
    qp.setPen(text_color)
    fm = QFontMetrics(font)

    screen_rect = item.screen_rect(coord)
    # Keep a small padding.
    pad = 4
    text_rect = screen_rect.adjusted(pad, pad, -pad, -pad)
    if text_rect.width() <= 0 or text_rect.height() <= 0:
        return

    text = item.event.abstract or ""
    # Truncate to available width.
    elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, int(text_rect.width()))
    qp.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)

    # Restore the logical transform for subsequent geometry.
    qp.setTransform(coord.transform())
