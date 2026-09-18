"""
Tests for the Agent API (REST + WebSocket broadcast).
"""

import unittest

from fastapi.testclient import TestClient

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import Event, Workspace
from universal_history.service.agent_api import create_app


def _event(uuid, year=2000, source="s"):
    return Event(uuid=uuid, source=source,
                 since=JDNTimestamp.from_year(year),
                 until=JDNTimestamp.from_year(year),
                 focus_label="event", labels={"title": [f"ev-{uuid}"]})


class TestAgentApi(unittest.TestCase):

    def setUp(self):
        self.ws_model = Workspace()
        self.ws_model.add(_event("a"))
        self.ws_model.add(_event("b", year=-43, source="rome"))
        self.client = TestClient(create_app(self.ws_model))

    def test_schema(self):
        r = self.client.get("/api/schema")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["format"], "universal-history/v1")

    def test_sources(self):
        r = self.client.get("/api/sources")
        self.assertEqual(r.status_code, 200)
        by_source = {s["source"]: s["event_count"] for s in r.json()}
        self.assertEqual(by_source, {"s": 1, "rome": 1})

    def test_list_events_index_shape(self):
        r = self.client.get("/api/events")
        self.assertEqual(r.status_code, 200)
        items = r.json()
        self.assertEqual(len(items), 2)
        self.assertIn("abstract", items[0])
        self.assertIsInstance(items[0]["since"], int)

    def test_filter_by_source_and_time(self):
        r = self.client.get("/api/events", params={"source": "rome"})
        self.assertEqual([i["uuid"] for i in r.json()], ["b"])
        # Time filter: year 1999..2001 in JDN microseconds.
        lo = JDNTimestamp.from_year(1999).value
        hi = JDNTimestamp.from_year(2001).value
        r = self.client.get("/api/events",
                            params={"time_from": lo, "time_to": hi})
        self.assertEqual([i["uuid"] for i in r.json()], ["a"])

    def test_get_event_full(self):
        r = self.client.get("/api/events/a")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["labels"]["title"], ["ev-a"])
        r = self.client.get("/api/events/nope")
        self.assertEqual(r.status_code, 404)

    def test_upsert_create_and_update(self):
        r = self.client.post("/api/events", json={
            "source": "s", "since": JDNTimestamp.from_year(2020).value,
            "until": JDNTimestamp.from_year(2020).value,
            "labels": {"title": ["new"]},
        })
        self.assertEqual(r.status_code, 201)
        new_uuid = r.json()["uuid"]
        self.assertIsNotNone(self.ws_model.get_by_uuid(new_uuid))

        r = self.client.post("/api/events", json={
            "uuid": new_uuid, "source": "s",
            "since": JDNTimestamp.from_year(2021).value,
            "until": JDNTimestamp.from_year(2021).value,
            "labels": {"title": ["updated"]},
        })
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            self.ws_model.get_by_uuid(new_uuid).labels["title"], ["updated"]
        )

    def test_delete(self):
        r = self.client.delete("/api/events/a")
        self.assertEqual(r.status_code, 204)
        self.assertIsNone(self.ws_model.get_by_uuid("a"))
        r = self.client.delete("/api/events/a")
        self.assertEqual(r.status_code, 404)

    def test_websocket_receives_broadcasts(self):
        with self.client.websocket_connect("/ws") as ws:
            hello = ws.receive_json()
            self.assertEqual(hello["type"], "hello")
            # A model mutation broadcasts to the socket.
            self.ws_model.add(_event("c", year=2030))
            msg = ws.receive_json()
            self.assertEqual(msg["type"], "event_added")
            self.assertEqual(msg["event"]["uuid"], "c")
            self.ws_model.remove("c")
            msg = ws.receive_json()
            self.assertEqual(msg["type"], "event_removed")
            self.assertEqual(msg["uuid"], "c")


if __name__ == "__main__":
    unittest.main()
