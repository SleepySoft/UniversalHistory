import unittest

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import EventIndex
from universal_history.render.geometry import CoordinateSystem
from universal_history.render.layout import ThreadLayout


def _index(since: tuple, until: tuple = None, abstract: str = "") -> EventIndex:
    s = JDNTimestamp.from_ymd_hms(*since)
    u = JDNTimestamp.from_ymd_hms(*until) if until else s
    return EventIndex(
        uuid="test",
        source="test",
        since=s,
        until=u,
        abstract=abstract,
    )


class TestThreadLayout(unittest.TestCase):

    def test_point_event_has_fixed_screen_width(self):
        coord = CoordinateSystem()
        coord.set_widget_size(800, 600)

        thread = ThreadLayout(align="right")
        thread.set_events([_index((2000, 1, 1), abstract="A")])
        thread.arrange(coord, (20, 300))

        self.assertEqual(len(thread.items), 1)
        item = thread.items[0]
        self.assertTrue(item.is_point)
        # x0/x1 are in logical pixels, so the width is the fixed pixel width.
        self.assertAlmostEqual(item.x1 - item.x0, 120.0, delta=1.0)

    def test_overlapping_period_events_go_to_different_tracks(self):
        coord = CoordinateSystem()
        coord.set_widget_size(800, 600)

        events = [
            _index((2000, 1, 1), (2000, 6, 1), "A"),
            _index((2000, 3, 1), (2000, 9, 1), "B"),
            _index((2001, 1, 1), (2001, 6, 1), "C"),
        ]

        thread = ThreadLayout(align="right")
        thread.set_events(events)
        thread.arrange(coord, (20, 300))

        # A and B overlap in time -> should be on different tracks.
        a = next(i for i in thread.items if i.event.abstract == "A")
        b = next(i for i in thread.items if i.event.abstract == "B")
        c = next(i for i in thread.items if i.event.abstract == "C")

        self.assertNotEqual(a.y0, b.y0)
        # C does not overlap A or B, can reuse B's track.
        self.assertEqual(c.y0, b.y0)

    def test_point_events_can_use_any_track(self):
        coord = CoordinateSystem()
        coord.set_widget_size(800, 600)

        events = [
            _index((2000, 1, 1), abstract="P1"),
            _index((2000, 6, 1), abstract="P2"),
            _index((2001, 1, 1), abstract="P3"),
        ]

        thread = ThreadLayout(align="right")
        thread.set_events(events)
        thread.arrange(coord, (20, 300))

        # Point events at distant times should not all be forced to track 0.
        tracks = {item.y0 for item in thread.items}
        self.assertGreaterEqual(len(tracks), 2)

    def test_min_track_width_affects_track_count(self):
        coord = CoordinateSystem()
        coord.set_widget_size(800, 600)

        # Three overlapping period events that need separate tracks.
        events = [
            _index((2000, 1, 1), (2000, 6, 1), "A"),
            _index((2000, 3, 1), (2000, 9, 1), "B"),
            _index((2000, 5, 1), (2000, 12, 1), "C"),
        ]

        narrow = ThreadLayout(align="right", min_track_width=20)
        narrow.set_events(events)
        narrow.arrange(coord, (20, 300))

        wide = ThreadLayout(align="right", min_track_width=200)
        wide.set_events(events)
        wide.arrange(coord, (20, 300))

        self.assertGreater(len(narrow.tracks), len(wide.tracks))

    def test_set_min_track_width_updates_value(self):
        thread = ThreadLayout(align="right", min_track_width=50)
        thread.set_min_track_width(120)
        self.assertEqual(thread.min_track_width, 120)
        thread.set_min_track_width(-10)
        self.assertEqual(thread.min_track_width, 1.0)


if __name__ == "__main__":
    unittest.main()
