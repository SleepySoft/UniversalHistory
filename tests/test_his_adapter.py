import unittest
from pathlib import Path

from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.models import Event, Workspace
from universal_history.adapters import HisFileAdapter
from universal_history.chrono import history_tick_to_jdn


class TestHisFileAdapter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.adapter = HisFileAdapter()
        cls.example_path = str(
            Path(__file__).resolve().parents[2] / "History" / "depot" / "example" / "example.his"
        )

    def test_load_example_file(self):
        events = self.adapter.load_file(self.example_path)
        self.assertEqual(len(events), 6)

        # First event: BC3000, title present, point event.
        first = events[0]
        self.assertTrue(first.is_point_event())
        self.assertEqual(first.focus_label, "event")
        self.assertIn("Hi-Story Example", first.title())
        self.assertTrue(first.has_time())
        self.assertEqual(first.since.year, -2999)  # 3000 BC -> astronomical -2999

        # A later event: 2030 AD.
        third = events[2]
        self.assertEqual(third.since.year, 2030)

    def test_load_example_depot(self):
        by_source = self.adapter.load_depot("example")
        self.assertEqual(len(by_source), 1)

        source, events = next(iter(by_source.items()))
        self.assertTrue(source.endswith("example.his"))
        self.assertEqual(len(events), 6)

    def test_workspace_integration(self):
        workspace = Workspace()
        workspace.load(self.adapter.load_depot("example"))

        self.assertEqual(len(workspace.sources()), 1)
        self.assertEqual(len(workspace.events()), 6)

        # Filter by tag.
        results = workspace.select(include_labels={"tags": ["tag5"]})
        self.assertGreaterEqual(len(results), 2)

        # Filter by focus label.
        results = workspace.select(focus_label="people")
        self.assertEqual(len(results), 1)

    def test_time_conversion_bc_ad_boundary(self):
        """1 BC (History year -1) maps to JDNTimestamp year 0."""
        # 1 BC in History TICK is roughly one year before AD 1.
        # We use the ported parser's time module to convert a known date.
        from universal_history.parsing import history_time as HistoryTime
        tick = HistoryTime.date_time_data_to_tick(-1, 12, 31, 0, 0, 0)
        ts = history_tick_to_jdn(tick)
        self.assertEqual(ts.year, 0)
        self.assertEqual(ts.month, 12)
        self.assertEqual(ts.day, 31)

        # AD 1.
        tick = HistoryTime.date_time_data_to_tick(1, 1, 1, 0, 0, 0)
        ts = history_tick_to_jdn(tick)
        self.assertEqual(ts.year, 1)

    def test_save_and_reload_roundtrip(self):
        """Events written back to .his must be loadable again."""
        import tempfile
        import os

        original = self.adapter.load_file(self.example_path)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".his", delete=False, encoding="utf-8"
        ) as f:
            temp_path = f.name

        try:
            self.adapter.save_file(temp_path, original)
            reloaded = self.adapter.load_file(temp_path)

            self.assertEqual(len(original), len(reloaded))
            for o, r in zip(original, reloaded):
                self.assertEqual(o.uuid, r.uuid)
                self.assertEqual(o.focus_label, r.focus_label)
                self.assertEqual(o.labels.get("time"), r.labels.get("time"))
                self.assertEqual(
                    sorted(o.labels.get("tags", [])),
                    sorted(r.labels.get("tags", [])),
                )
                # Time equality
                self.assertEqual(o.since, r.since)
                self.assertEqual(o.until, r.until)
        finally:
            os.unlink(temp_path)


class TestRealDepots(unittest.TestCase):
    """Lock real-world data: China_CN / World_CN depots must stay loadable
    with stable counts (acceptance checklist §4).

    Counts were probed on 2026-09-18; update them only when the underlying
    .his data files intentionally change.
    """

    EXPECTED = {
        "China_CN": {
            "COVID-19疫情.his": 19,
            "三国时期事件.his": 105,
            "三国时期人物.his": 36,
            "中国朝代表.his": 34,
            "史前大事件.his": 32,
            "周朝时期事件.his": 9,
            "周朝时期人物.his": 4,
            "楚汉时期事件.his": 9,
        },
        "World_CN": {
            "埃及年表.his": 51,
            "宗教事件.his": 8,
            "希腊罗马主要事件.his": 72,
            "欧亚大陆主要事件.his": 57,
            "欧亚大陆主要人物.his": 17,
            "韩国政治史.his": 30,
        },
    }

    @classmethod
    def setUpClass(cls):
        cls.adapter = HisFileAdapter()

    def _check_depot(self, depot: str):
        by_source = self.adapter.load_depot(depot)
        expected_files = self.EXPECTED[depot]
        self.assertEqual(len(by_source), len(expected_files))

        for source, events in by_source.items():
            filename = source.replace("\\", "/").rsplit("/", 1)[-1]
            self.assertIn(filename, expected_files)
            self.assertEqual(len(events), expected_files[filename], filename)
            for event in events:
                self.assertTrue(event.uuid, filename)
                self.assertTrue(event.source, filename)

        return by_source

    def test_china_cn_depot_loadable(self):
        by_source = self._check_depot("China_CN")
        total = sum(len(v) for v in by_source.values())
        self.assertEqual(total, 248)

    def test_world_cn_depot_loadable(self):
        by_source = self._check_depot("World_CN")
        total = sum(len(v) for v in by_source.values())
        self.assertEqual(total, 235)

    def test_real_depots_bce_times_parse(self):
        """BC-heavy data (dynasties, prehistory) must produce astronomical
        years (<= 0) via the natural-language parsing pipeline."""
        by_source = self.adapter.load_depot("China_CN")
        bce = [
            e for events in by_source.values() for e in events
            if e.since is not None and e.since.year <= 0
        ]
        # Dynasties / prehistory depots contain many BC events.
        self.assertGreater(len(bce), 50)


if __name__ == "__main__":
    unittest.main()
