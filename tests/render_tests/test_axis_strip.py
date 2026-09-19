"""Regression tests for the 2026-09-19 axis/track fixes:

1. Tracks are assigned axis-outward on BOTH sides (negative-side threads
   used to fill from the far edge — horizontal/vertical inconsistency).
2. Vertical-mode axis labels are painted on top of the threads with a
   background chip (they share the left side with left threads and were
   occluded by the cards).
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QApplication

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render.geometry import CoordinateSystem
from universal_history.render.layout import ThreadLayout
from universal_history.render.timeline_view import TimelineView

app = QApplication.instance() or QApplication([])


def _index(since: tuple, until: tuple = None, abstract: str = "") -> EventIndex:
    s = JDNTimestamp.from_ymd_hms(*since)
    u = JDNTimestamp.from_ymd_hms(*until) if until else s
    return EventIndex(uuid=abstract or "t", source="t", since=s, until=u,
                      abstract=abstract)


class TestAxisOutwardTracks(unittest.TestCase):

    def test_negative_side_track0_hugs_axis(self):
        coord = CoordinateSystem()
        coord.set_widget_size(800, 600)
        events = [
            _index((2000, 1, 1), (2000, 6, 1), "A"),
            _index((2000, 3, 1), (2000, 9, 1), "B"),  # longer -> placed first
        ]
        thread = ThreadLayout(align="left")
        thread.set_events(events)
        thread.arrange(coord, (-300, -20))

        # Track 0 must hug the axis (the y1 edge is nearest to 0 here).
        self.assertAlmostEqual(thread.tracks[0].y1, -20.0)
        self.assertAlmostEqual(thread.tracks[-1].y0, -300.0)
        b = next(i for i in thread.items if i.event.abstract == "B")
        self.assertAlmostEqual(b.y1, -20.0)  # first-placed sits nearest axis

    def test_positive_side_track0_hugs_axis(self):
        coord = CoordinateSystem()
        coord.set_widget_size(800, 600)
        thread = ThreadLayout(align="right")
        thread.set_events([_index((2000, 1, 1), (2000, 6, 1), "A")])
        thread.arrange(coord, (20, 300))
        self.assertAlmostEqual(thread.tracks[0].y0, 20.0)
        self.assertAlmostEqual(thread.tracks[-1].y1, 300.0)


class TestVerticalLabelsOnTop(unittest.TestCase):

    def test_vertical_label_chip_covers_thread_card(self):
        view = TimelineView()
        view.resize(800, 600)
        span = _index((1995, 1, 1), (2005, 1, 1), "span")
        thread = view.add_thread([span], align="left")
        view.coord.is_vertical = True
        view.coord.center_time = JDNTimestamp.from_ymd_hms(2000, 1, 1)
        view._arrange_threads()
        view.show()

        img = QImage(800, 600, QImage.Format.Format_ARGB32)
        img.fill(0)
        p = QPainter(img)
        view.render(p)
        p.end()

        # A major tick sits at the view centre (2000-01-01). Its label is
        # right-aligned ending at axis_center - LABEL_TOP - 4 and extends
        # leftwards over the left thread band. With the chip, most pixels in
        # that zone are light (chip fill), not the card colour.
        axis_c = view.coord.axis_screen_center()
        y = 300  # screen y of the centre tick
        card = thread.item_color
        light = 0
        total = 0
        for x in range(int(axis_c - 75), int(axis_c - 30), 3):
            c = QColor(img.pixel(x, y))
            total += 1
            if abs(c.red() - card.red()) < 20 and \
                    abs(c.green() - card.green()) < 20 and \
                    abs(c.blue() - card.blue()) < 20:
                pass  # raw card colour — chip missing here
            if c.red() > 220 and c.green() > 220 and c.blue() > 220:
                light += 1
        self.assertGreater(light, total // 2,
                           "vertical axis label area should be chip-backed, "
                           "not raw thread card pixels")


if __name__ == "__main__":
    unittest.main()
