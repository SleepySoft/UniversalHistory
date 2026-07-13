import unittest

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import Event, Workspace


class TestWorkspaceSignals(unittest.TestCase):

    def test_upsert_emits_updated_for_existing(self):
        ws = Workspace()
        captured = []
        ws.event_added.connect(lambda e: captured.append(("added", e.uuid)))
        ws.event_updated.connect(lambda e: captured.append(("updated", e.uuid)))

        event = Event("u1", "s1", JDNTimestamp.from_ymd(2000, 1, 1),
                      JDNTimestamp.from_ymd(2000, 1, 1), "event")
        ws.upsert(event)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], "added")

        event2 = Event("u1", "s1", JDNTimestamp.from_ymd(2001, 1, 1),
                       JDNTimestamp.from_ymd(2001, 1, 1), "event")
        ws.upsert(event2)
        self.assertEqual(len(captured), 2)
        self.assertEqual(captured[1][0], "updated")

    def test_remove_emits_removed(self):
        ws = Workspace()
        event = Event("u1", "s1", JDNTimestamp.from_ymd(2000, 1, 1),
                      JDNTimestamp.from_ymd(2000, 1, 1), "event")
        ws.upsert(event)

        captured = []
        ws.event_removed.connect(lambda uid: captured.append(uid))
        ws.remove("u1")
        self.assertEqual(captured, ["u1"])

    def test_load_replaces_existing_source(self):
        ws = Workspace()
        ws.load({"s1": [Event("u1", "s1", JDNTimestamp.from_ymd(2000, 1, 1),
                               JDNTimestamp.from_ymd(2000, 1, 1), "event")]})
        ws.load({"s1": [Event("u2", "s1", JDNTimestamp.from_ymd(2001, 1, 1),
                               JDNTimestamp.from_ymd(2001, 1, 1), "event")]})

        self.assertEqual(len(ws.events("s1")), 1)
        self.assertEqual(ws.events("s1")[0].uuid, "u2")


if __name__ == "__main__":
    unittest.main()
