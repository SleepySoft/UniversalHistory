"""
Boundary tests for Workspace and HisFileAdapter (PROJECT_STATUS 待办 2).

Covers known-issues #1-#4 (model layer) and #6 (save conflict detection).
"""

import tempfile
import unittest
from pathlib import Path

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import Event, Workspace
from universal_history.adapters import HisFileAdapter, SaveConflictError


def _event(uuid: str, source: str = "s1", year: int = 2000) -> Event:
    ts = JDNTimestamp.from_ymd(year, 1, 1)
    return Event(uuid, source, ts, ts, "event")


class TestWorkspaceBoundaries(unittest.TestCase):

    def test_add_empty_source_raises(self):
        ws = Workspace()
        with self.assertRaises(ValueError):
            ws.add(_event("u1", source=""))

    def test_add_duplicate_uuid_raises(self):
        """known-issues #3: add() must reject duplicate uuids."""
        ws = Workspace()
        ws.add(_event("u1"))
        with self.assertRaises(ValueError):
            ws.add(_event("u1", year=2001))
        self.assertEqual(len(ws.events()), 1)

    def test_load_skips_duplicate_uuid(self):
        """Bulk load stays tolerant but never stores a uuid twice."""
        ws = Workspace()
        ws.load({"s1": [_event("u1"), _event("u1", year=2001)]})
        self.assertEqual(len(ws.events()), 1)

    def test_upsert_emits_single_signal(self):
        """known-issues #2: replacing via upsert emits only event_updated."""
        ws = Workspace()
        ws.add(_event("u1"))
        captured = []
        ws.event_removed.connect(lambda uid: captured.append(("removed", uid)))
        ws.event_updated.connect(lambda e: captured.append(("updated", e.uuid)))
        ws.event_added.connect(lambda e: captured.append(("added", e.uuid)))
        ws.upsert(_event("u1", year=2001))
        self.assertEqual(captured, [("updated", "u1")])

    def test_clear_emits_source_removed(self):
        """known-issues #1: clear() signals removal, not loading."""
        ws = Workspace()
        ws.load({"s1": [_event("u1")], "s2": [_event("u2", source="s2")]})
        removed, loaded = [], []
        ws.source_removed.connect(removed.append)
        ws.source_loaded.connect(loaded.append)
        ws.clear()
        self.assertEqual(sorted(removed), ["s1", "s2"])
        self.assertEqual(loaded, [])
        self.assertEqual(ws.sources(), [])

    def test_remove_source_emits_source_removed(self):
        ws = Workspace()
        ws.load({"s1": [_event("u1")]})
        removed = []
        ws.source_removed.connect(removed.append)
        ws.remove_source("s1")
        self.assertEqual(removed, ["s1"])

    def test_remove_source_unknown_is_noop(self):
        ws = Workspace()
        removed = []
        ws.source_removed.connect(removed.append)
        ws.remove_source("nope")
        self.assertEqual(removed, [])


class TestEventIndexHelpers(unittest.TestCase):

    def test_has_time_and_period(self):
        """known-issues #4: EventIndex exposes is_period_event/has_time."""
        point = _event("u1").to_index()
        self.assertTrue(point.has_time())
        self.assertTrue(point.is_point_event())
        self.assertFalse(point.is_period_event())

        e = Event("u2", "s1", JDNTimestamp.from_ymd(2000, 1, 1),
                  JDNTimestamp.from_ymd(2001, 1, 1), "event")
        idx = e.to_index()
        self.assertTrue(idx.has_time())
        self.assertTrue(idx.is_period_event())
        self.assertFalse(idx.is_point_event())

        timeless = Event("u3", "s1", None, None, "event").to_index()
        self.assertFalse(timeless.has_time())
        self.assertFalse(timeless.is_point_event())
        self.assertFalse(timeless.is_period_event())


class TestSaveConflict(unittest.TestCase):
    """known-issues #6: overwriting a file changed on disk must be detected."""

    def setUp(self):
        self.adapter = HisFileAdapter()
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".his", delete=False, encoding="utf-8"
        )
        self.tmp.write("[START]: event\ntime: 2000年\nevent: hello\n")
        self.tmp.close()
        self.path = self.tmp.name

    def tearDown(self):
        Path(self.path).unlink(missing_ok=True)

    def test_normal_save_after_load(self):
        events = self.adapter.load_file(self.path)
        self.adapter.save_file(self.path, events)  # no conflict

    def test_conflict_detected(self):
        events = self.adapter.load_file(self.path)
        # Simulate external modification.
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("\n# external change\n")
        with self.assertRaises(SaveConflictError):
            self.adapter.save_file(self.path, events)

    def test_force_overwrites(self):
        events = self.adapter.load_file(self.path)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("\n# external change\n")
        self.adapter.save_file(self.path, events, force=True)
        reloaded = self.adapter.load_file(self.path)
        self.assertEqual(len(reloaded), len(events))

    def test_save_new_file_no_conflict(self):
        new_path = self.path + ".new"
        try:
            self.adapter.save_file(new_path, [])
            self.assertTrue(Path(new_path).exists())
        finally:
            Path(new_path).unlink(missing_ok=True)

    def test_empty_source_save(self):
        """Saving zero events writes an empty file without error."""
        events = self.adapter.load_file(self.path)
        self.adapter.save_file(self.path, [])
        self.assertEqual(Path(self.path).read_text(encoding="utf-8"), "")
        self.assertEqual(self.adapter.load_file(self.path), [])


if __name__ == "__main__":
    unittest.main()
