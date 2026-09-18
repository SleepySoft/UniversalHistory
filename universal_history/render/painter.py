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

# LOD fade thresholds (docs/zoom_design.md §3): a tick level fades in between
# TICK_FADE_MIN_PX and TICK_FADE_FULL_PX of on-screen spacing, is the major
# scale between FULL and DEMOTE, and demotes to a faint background scale
# beyond TICK_DEMOTE_PX.
TICK_FADE_MIN_PX = 50.0
TICK_FADE_FULL_PX = 100.0
TICK_DEMOTE_PX = 300.0

# Three-tier display degradation (core_design.md §5.2): ticks deeper than
# DEEP_TIME_YEAR (astronomical -10000, i.e. earlier than 10001 BC) are labeled
# in BP (Before Present, reference epoch 1950 AD) magnitudes.
DEEP_TIME_YEAR = -10_000
BP_REFERENCE_YEAR = 1950

# Light chip for point events; period bars use the thread's item color.
POINT_EVENT_FILL = QColor(243, 244, 246)


def _format_bp(y: int) -> str:
    """BP (Before Present, 1950 AD) magnitude label for deep-time ticks."""
    bp = BP_REFERENCE_YEAR - y
    if bp >= 1_000_000_000:
        return f"{bp / 1_000_000_000:g} Ga BP"
    if bp >= 1_000_000:
        return f"{bp / 1_000_000:g} Ma BP"
    if bp >= 1_000:
        return f"{bp / 1_000:g} ka BP"
    return f"{bp} BP"


def _format_tick_label(tick: JDNTimestamp, level: TickLevel) -> str:
    y, m, d, h, mn, s, _ = tick.to_gregorian()

    era_suffix = ""
    display_year = y
    if y <= 0:
        display_year = -(y - 1)
        era_suffix = " BC"

    # Tier 3 (core_design §5.2): anything deeper than 10001 BC is Deep Time —
    # label in BP magnitudes regardless of the tick level.
    if y < DEEP_TIME_YEAR:
        return _format_bp(y)

    if level.unit == "Year":
        # Deep Time magnitudes for coarse levels near the boundary (a major
        # level of 10k+ years can straddle the BP threshold).
        if level.step_count >= 1_000_000_000:
            return f"{y / 1_000_000_000:g} Ga"
        if level.step_count >= 1_000_000:
            return f"{y / 1_000_000:g} Ma"
        if level.step_count >= 10_000:
            return f"{y / 1_000:g} ka"
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

    if level.unit == "Second":
        # Sub-day levels: show the clock time; give the date at day start.
        if h == 0 and mn == 0 and s == 0:
            return f"{display_year}{era_suffix}-{m:02d}-{d:02d}"
        if level.step_count >= 3600:
            return f"{h:02d}:00"
        if level.step_count >= 60:
            return f"{h:02d}:{mn:02d}"
        return f"{h:02d}:{mn:02d}:{s:02d}"

    return str(tick)


def _tick_opacity(px_width: float) -> float:
    """Density-driven fade (zoom_design.md §3): 0 below MIN, linear ramp to
    FULL, 1.0 above."""
    if px_width < TICK_FADE_MIN_PX:
        return 0.0
    if px_width < TICK_FADE_FULL_PX:
        return (px_width - TICK_FADE_MIN_PX) / (TICK_FADE_FULL_PX - TICK_FADE_MIN_PX)
    return 1.0


def _tick_role(px_width: float) -> str:
    """minor = fading-in sub-scale; major = main scale; demoted = background."""
    if px_width < TICK_FADE_FULL_PX:
        return "minor"
    if px_width > TICK_DEMOTE_PX:
        return "demoted"
    return "major"


def _generate_ticks(coord: CoordinateSystem, level: TickLevel, start, end) -> list:
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
    return ticks


def _tick_layers(coord: CoordinateSystem) -> list:
    """
    Compute all visible tick layers for the current zoom (known-issues #16:
    dual-layer ticks with density-driven fade, replacing the previous
    single-layer hard switch).

    Returns a list of ``(level, ticks, alpha, role)`` ordered fine -> coarse.
    """
    start, end = coord.visible_time_range()
    if end <= start:
        return []

    # Respect each level's registered visibility range (Day/Week/Month are
    # limited to documented history, ±10000 years).
    center_year = (start.year + end.year) // 2
    candidates = [lv for lv in TickStepper.LEVELS if lv.is_visible(center_year)]
    if not candidates:
        candidates = TickStepper.LEVELS

    layers = []
    for level in candidates:
        px = level.avg_duration_us * coord.scale
        alpha = _tick_opacity(px)
        if alpha <= 0:
            continue
        ticks = _generate_ticks(coord, level, start, end)
        if not ticks:
            continue
        layers.append((level, ticks, alpha, _tick_role(px)))
        # Coarse levels only get wider; once one is demoted, stop (anything
        # coarser is redundant background).
        if px > TICK_DEMOTE_PX:
            break
    return layers


def _visible_ticks(
    coord: CoordinateSystem, target_px: float = 120.0
) -> Tuple[TickLevel, list]:
    """Choose a tick level and generate ticks for the visible range.

    Kept as the single-layer compatibility view: returns the major layer of
    `_tick_layers` (the finest fully-visible level).
    """
    layers = _tick_layers(coord)
    if not layers:
        return TickStepper.LEVELS[-1], []
    for level, ticks, alpha, role in layers:
        if role == "major":
            return level, ticks
        if role == "demoted":
            return level, ticks
    # Only fading-in minors: fall back to the finest available.
    level, ticks, _, _ = layers[0]
    return level, ticks


def paint_axis(
    qp: QPainter,
    coord: CoordinateSystem,
    axis_color: QColor,
    tick_color: QColor,
    text_color: QColor,
    font: QFont,
) -> None:
    """Paint the central axis line and tick labels.

    Renders all visible tick layers (zoom_design.md): coarse layers first as
    background, then finer layers on top. Minor (fading-in) layers draw short
    ticks without labels; major layers draw full ticks and labels; demoted
    layers stay as faint background scales.
    """
    vp = coord.viewport()
    half_len = vp.length / 2
    # The axis line must span the *current* viewport, not the layout anchor:
    # while panning, logical X 0 stays at the anchor time, so centre the line
    # on the view centre's logical position.
    cx = coord.center_logical_x()

    # Apply the unified logical coordinate transform for geometry.
    qp.setPen(QPen(axis_color, AXIS_LINE_WIDTH))
    qp.drawLine(QPointF(cx - half_len, 0), QPointF(cx + half_len, 0))

    layers = _tick_layers(coord)

    def _faded(color: QColor, alpha: float) -> QColor:
        c = QColor(color)
        c.setAlphaF(max(0.0, min(1.0, alpha)))
        return c

    # 1. Tick marks, coarse (background) -> fine (foreground).
    for level, ticks, alpha, role in reversed(layers):
        if role == "minor":
            length = TICK_LENGTH / 2
            layer_alpha = alpha
        elif role == "demoted":
            length = TICK_LENGTH * 1.5
            layer_alpha = 0.3  # strategy A: faded background reference
        else:
            length = TICK_LENGTH
            layer_alpha = alpha
        qp.setPen(QPen(_faded(tick_color, layer_alpha), 1))
        for tick in ticks:
            x = coord.time_to_logical_x(tick)
            qp.drawLine(QPointF(x, -length), QPointF(x, length))

    # 2. Labels in screen coordinates so they stay upright; only major and
    # demoted (watermark) layers get labels.
    qp.save()
    qp.resetTransform()
    qp.setFont(font)
    fm = QFontMetrics(font)

    for level, ticks, alpha, role in reversed(layers):
        if role == "minor":
            continue
        label_alpha = alpha if role == "major" else 0.3
        qp.setPen(_faded(text_color, label_alpha))
        for tick in ticks:
            x = coord.time_to_logical_x(tick)
            # Place labels on the side of the axis that is not covered by
            # threads (above in horizontal mode, to the right in vertical).
            screen_pos = coord.logical_to_screen(QPointF(x, -LABEL_OFFSET))
            text = _format_tick_label(tick, level)

            if coord.is_vertical:
                draw_x = screen_pos.x() + 4
                draw_y = screen_pos.y() + fm.ascent() / 2
            else:
                text_width = fm.horizontalAdvance(text)
                draw_x = screen_pos.x() - text_width / 2
                draw_y = screen_pos.y() + fm.ascent()

            qp.drawText(QPointF(draw_x, draw_y), text)

    # Restore the logical transform explicitly (no implicit contract).
    qp.restore()


def item_in_time_range(item: ItemLayout, start, end, margin_us: int = 0) -> bool:
    """
    Visibility culling predicate (known-issues #19).

    Only painting/hit-testing should cull — layout deliberately processes all
    events so track assignment stays stable while panning. ``margin_us``
    expands the range so point-event cards centered just outside the viewport
    are still drawn.
    """
    ev = item.event
    if ev.since is None or ev.until is None:
        return True
    if margin_us:
        start = JDNTimestamp(start.value - margin_us)
        end = JDNTimestamp(end.value + margin_us)
    return not (ev.until < start or ev.since > end)


def paint_thread_background(
    qp: QPainter, coord: CoordinateSystem, thread: ThreadLayout
) -> None:
    """Paint the background area of a thread."""
    height = thread.y1 - thread.y0
    if height <= 0:
        return
    vp = coord.viewport()
    half_len = vp.length / 2
    # Span the current viewport along the time axis (see paint_axis).
    cx = coord.center_logical_x()
    rect = QRectF(cx - half_len, thread.y0, vp.length, height)
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

    fill_color = POINT_EVENT_FILL if item.is_point else color

    # When a point event is zoomed far out, its fixed 120 px card would span
    # centuries and look like a period bar. In that case draw a thin marker.
    if item.is_point:
        one_year_us = int(365.2425 * 24 * 3600 * 1_000_000)
        point_span_us = rect.width() / coord.scale if coord.scale else 0
        if point_span_us > 2 * one_year_us:
            center_x = (rect.left() + rect.right()) / 2
            qp.setPen(QPen(fill_color, 2))
            qp.drawLine(
                QPointF(center_x, rect.top()), QPointF(center_x, rect.bottom())
            )
            qp.setTransform(coord.transform())
            return

    # Draw the geometry with the logical transform active.
    radius = 4.0
    qp.setBrush(fill_color)
    qp.setPen(QPen(fill_color.darker(120), 1))
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
