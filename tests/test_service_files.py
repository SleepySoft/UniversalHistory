import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from universal_history.adapters import event_to_dict
from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import Event, Workspace
from universal_history.service.agent_api import create_app
from universal_history.service.file_library import AllowedFileLibrary


def _event_dict() -> dict:
    event = Event(
        uuid="9a5f57a8-90d7-4a4e-b64f-e98b472e5c2e",
        source="panel",
        since=JDNTimestamp.from_year(2020),
        until=JDNTimestamp.from_year(2020),
        focus_label="event",
        labels={"title": ["Loaded from panel"]},
    )
    return event_to_dict(event)


class TestAllowedFileLibrary(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name).resolve()
        (self.root / "loaded.uh.json").write_text(
            json.dumps({
                "format": "universal-history/v1",
                "events": [_event_dict()],
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.root / "notes.txt").write_text("ignored", encoding="utf-8")
        self.library = AllowedFileLibrary([self.root])

    def tearDown(self):
        self._temp.cleanup()

    def test_lists_only_supported_files(self):
        files = self.library.list_files()
        self.assertEqual([item.name for item in files], ["loaded.uh.json"])
        self.assertEqual(files[0].file_format, "json")

    def test_resolve_uses_opaque_id(self):
        item = self.library.list_files()[0]
        self.assertEqual(self.library.resolve(item.id), self.root / "loaded.uh.json")
        with self.assertRaises(FileNotFoundError):
            self.library.resolve("not-a-real-file-id")


class TestServiceFilePanel(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name).resolve()
        path = self.root / "loaded.uh.json"
        path.write_text(
            json.dumps({
                "format": "universal-history/v1",
                "events": [_event_dict()],
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        self.workspace = Workspace()
        self.library = AllowedFileLibrary([self.root])
        self.client = TestClient(create_app(self.workspace, self.library))

    def tearDown(self):
        self._temp.cleanup()

    def test_list_files_is_empty_without_allow_roots(self):
        client = TestClient(create_app(Workspace()))
        self.assertEqual(client.get("/api/files").json()["files"], [])

    def test_initial_file_path_is_marked_loaded(self):
        self.library.mark_loaded_path(self.root / "loaded.uh.json")
        catalog = self.client.get("/api/files").json()
        self.assertTrue(catalog["files"][0]["loaded"])

    def test_list_and_load_allowed_file(self):
        catalog = self.client.get("/api/files").json()
        self.assertEqual(len(catalog["files"]), 1)
        file_id = catalog["files"][0]["id"]

        response = self.client.post(
            "/api/files/load", json={"file_id": file_id}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["event_count"], 1)
        self.assertEqual(body["sources"], ["panel"])
        self.assertEqual(len(self.workspace.events("panel")), 1)

        catalog = self.client.get("/api/files").json()
        self.assertTrue(catalog["files"][0]["loaded"])

    def test_unknown_file_id_is_rejected(self):
        response = self.client.post(
            "/api/files/load", json={"file_id": "unknown"}
        )
        self.assertEqual(response.status_code, 404)

    def test_load_allowed_his_file(self):
        path = self.root / "loaded.his"
        path.write_text(
            '[START]: event\n\n'
            'uuid: c9a7d9d4-1d05-48de-a6ba-e74e693b1f0b\n'
            'time: 2021\n\n'
            'title:"""\nLoaded HIS\n"""\n\n'
            'event:"""\nPanel loaded this record.\n"""\n',
            encoding="utf-8",
        )
        catalog = self.client.get("/api/files").json()
        item = next(
            item for item in catalog["files"] if item["name"] == "loaded.his"
        )
        response = self.client.post(
            "/api/files/load", json={"file_id": item["id"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["event_count"], 1)
        self.assertEqual(len(self.workspace.events()), 1)
