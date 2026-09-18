"""
Tests for JsonFileAdapter (non-.his persistence) and the shared
FileFingerprints conflict detection.
"""

import json
import tempfile
import unittest
from pathlib import Path

from universal_history.adapters import (
    FORMAT_ID, JsonFileAdapter, SaveConflictError, event_from_dict,
    event_to_dict,
)
from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import Event


def _event(uuid="u1", year=2000):
    return Event(
        uuid=uuid,
        source="s",
        since=JDNTimestamp.from_ymd(year, 1, 1),
        until=JDNTimestamp.from_ymd(year, 1, 1),
        focus_label="event",
        labels={"title": ["Hello"], "time": [f"{year}"]},
    )


class TestJsonAdapter(unittest.TestCase):

    def test_roundtrip_exact(self):
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "events.uh.json")
            adapter = JsonFileAdapter()
            events = [_event("a", 2000), _event("b", -2999)]
            adapter.save_file(path, events)

            doc = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(doc["format"], FORMAT_ID)
            self.assertIsInstance(doc["events"][0]["since"], int)

            loaded = adapter.load_file(path)
            self.assertEqual(len(loaded), 2)
            for orig, back in zip(events, loaded):
                self.assertEqual(orig.uuid, back.uuid)
                self.assertEqual(orig.since.value, back.since.value)
                self.assertEqual(orig.labels, back.labels)

    def test_none_time_roundtrip(self):
        ev = Event(uuid="t", source="s", since=None, until=None,
                   focus_label="event", labels={})
        back = event_from_dict(event_to_dict(ev))
        self.assertIsNone(back.since)
        self.assertIsNone(back.until)

    def test_empty_file_loads_empty(self):
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "empty.uh.json")
            Path(path).write_text("", encoding="utf-8")
            self.assertEqual(JsonFileAdapter().load_file(path), [])

    def test_missing_file_raises(self):
        with self.assertRaises(OSError):
            JsonFileAdapter().load_file("no/such/file.json")

    def test_conflict_detection_and_force(self):
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "events.uh.json")
            adapter = JsonFileAdapter()
            adapter.save_file(path, [_event("a")])
            # External modification.
            Path(path).write_text("{}", encoding="utf-8")
            with self.assertRaises(SaveConflictError):
                adapter.save_file(path, [_event("b")])
            adapter.save_file(path, [_event("b")], force=True)
            self.assertEqual(adapter.load_file(path)[0].uuid, "b")


if __name__ == "__main__":
    unittest.main()
