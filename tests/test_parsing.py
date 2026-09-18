"""
Regression tests for the ported .his parser (universal_history.parsing).

These lock the parser-port bug fixes (legacy defects #1/#2/#5/#6/#7/#9) and
the byte-for-byte parsing compatibility with the legacy History parser.
"""

import tempfile
import unittest
from pathlib import Path

from universal_history.parsing import (
    HistoryRecord,
    HistoryRecordLoader,
    LabelTagParser,
    history_time as HistoryTime,
)
from universal_history.parsing.text_utils import list_unique
from universal_history.parsing.cn_num import cn_num_to_digit, text_cn_num_to_arab


class TestChineseNumerals(unittest.TestCase):
    """cn_num port sanity checks (legacy to_arab.py test values)."""

    def test_basic_digits(self):
        self.assertEqual(cn_num_to_digit('零'), 0)
        self.assertEqual(cn_num_to_digit('两'), 2)
        self.assertEqual(cn_num_to_digit('十'), 10)
        self.assertEqual(cn_num_to_digit('二十'), 20)
        self.assertEqual(cn_num_to_digit('一万'), 10000)
        self.assertEqual(cn_num_to_digit('一亿'), 100000000)

    def test_composite(self):
        self.assertEqual(
            cn_num_to_digit('一千一百一十一亿一千一百一十一万一千一百一十一'),
            111111111111,
        )
        self.assertEqual(
            cn_num_to_digit('五万四千三百二十一万亿四千三百二十一万四千三百二十一'),
            54321000043214321,
        )

    def test_text_arabization(self):
        self.assertEqual(text_cn_num_to_arab('公元前二百年'), '公元前200年')


class TestHistoryTime(unittest.TestCase):
    """Time text -> TICK conversion must match the legacy parser."""

    def test_bce_year(self):
        ticks = HistoryTime.time_text_to_ticks('公元前200年')
        self.assertEqual(len(ticks), 1)
        year, month, day, *_ = HistoryTime.tick_to_date_time_data(ticks[0])
        self.assertEqual((year, month, day), (-200, 1, 1))

    def test_range_separator(self):
        ticks = HistoryTime.time_text_to_ticks('公元前300年 - 公元前200年')
        self.assertEqual(len(ticks), 2)
        years = sorted(HistoryTime.tick_to_date_time_data(t)[0] for t in ticks)
        self.assertEqual(years, [-300, -200])

    def test_cn_numeral_year(self):
        ticks = HistoryTime.time_text_to_ticks('公元前二百年')
        year = HistoryTime.tick_to_date_time_data(ticks[0])[0]
        self.assertEqual(year, -200)

    def test_standard_datetime_in_brackets(self):
        ticks = HistoryTime.time_text_to_ticks('[2020-05-01 12:30:00]')
        self.assertEqual(len(ticks), 1)
        self.assertEqual(
            HistoryTime.tick_to_date_time_data(ticks[0]),
            (2020, 5, 1, 12, 30, 0),
        )

    def test_bc_ad_boundary_roundtrip(self):
        """1 BC = History year -1; AD 1 = year 1. No year 0."""
        tick_bc = HistoryTime.date_time_data_to_tick(-1, 12, 31, 0, 0, 0)
        self.assertLess(tick_bc, 0)
        self.assertEqual(
            HistoryTime.tick_to_date_time_data(tick_bc)[:3], (-1, 12, 31)
        )
        tick_ad = HistoryTime.date_time_data_to_tick(1, 1, 1, 0, 0, 0)
        self.assertEqual(tick_ad, 0)
        self.assertEqual(
            HistoryTime.tick_to_date_time_data(tick_ad)[:3], (1, 1, 1)
        )

    def test_decimal_year_to_tick(self):
        """Legacy defect #1: this function never existed in History."""
        tick = HistoryTime.decimal_year_to_tick(200.0)
        self.assertEqual(HistoryTime.tick_to_date_time_data(tick)[0], 200)
        tick_bce = HistoryTime.decimal_year_to_tick(-200.0)
        self.assertEqual(HistoryTime.tick_to_date_time_data(tick_bce)[0], -200)
        # Fractional part moves into the year.
        tick_half = HistoryTime.decimal_year_to_tick(200.5)
        self.assertEqual(HistoryTime.tick_to_date_time_data(tick_half)[0], 200)

    def test_century_ce_interval(self):
        """User decision 2026-09-18: a century is an interval, not a year."""
        ticks = HistoryTime.time_text_to_ticks('21世纪')
        self.assertEqual(len(ticks), 2)
        start = HistoryTime.tick_to_date_time_data(min(ticks))
        end = HistoryTime.tick_to_date_time_data(max(ticks))
        self.assertEqual(start[:3], (2001, 1, 1))
        self.assertEqual(end[:3], (2100, 12, 31))

    def test_century_bce_interval(self):
        ticks = HistoryTime.time_text_to_ticks('公元前3世纪')
        start = HistoryTime.tick_to_date_time_data(min(ticks))
        end = HistoryTime.tick_to_date_time_data(max(ticks))
        self.assertEqual(start[:3], (-300, 1, 1))
        self.assertEqual(end[:3], (-201, 12, 31))

    def test_century_cn_numeral(self):
        ticks = HistoryTime.time_text_to_ticks('七世纪初')
        start = HistoryTime.tick_to_date_time_data(min(ticks))
        end = HistoryTime.tick_to_date_time_data(max(ticks))
        self.assertEqual(start[:3], (601, 1, 1))
        self.assertEqual(end[:3], (700, 12, 31))

    def test_century_range(self):
        """"14世纪-16世纪" spans from the start of C14 to the end of C16."""
        ticks = HistoryTime.time_text_to_ticks('14世纪-16世纪')
        start = HistoryTime.tick_to_date_time_data(min(ticks))
        end = HistoryTime.tick_to_date_time_data(max(ticks))
        self.assertEqual(start[:3], (1301, 1, 1))
        self.assertEqual(end[:3], (1600, 12, 31))

    def test_leap_century_last_day_roundtrip(self):
        """Legacy bug (fixed during port): Dec 31 of years divisible by 400
        (1600, 2000) used to read back as Jan 1 of the next year."""
        for year in (400, 1600, 2000, 2400):
            tick = HistoryTime.date_time_data_to_tick(year, 12, 31, 0, 0, 0)
            self.assertEqual(
                HistoryTime.tick_to_date_time_data(tick)[:3],
                (year, 12, 31),
                f"year {year}",
            )
        # The day before/after must stay put as well.
        tick = HistoryTime.date_time_data_to_tick(2000, 12, 30)
        self.assertEqual(HistoryTime.tick_to_date_time_data(tick)[:3], (2000, 12, 30))
        tick = HistoryTime.date_time_data_to_tick(2001, 1, 1)
        self.assertEqual(HistoryTime.tick_to_date_time_data(tick)[:3], (2001, 1, 1))


class TestListUnique(unittest.TestCase):
    def test_order_preserving(self):
        """Legacy defect #6: set-based dedupe scrambled tag order."""
        self.assertEqual(list_unique(['b', 'a', 'b', 'c', 'a']), ['b', 'a', 'c'])


class TestLabelTagParser(unittest.TestCase):
    def test_duplicate_labels_merge(self):
        """Legacy defect #2: duplicated labels must merge, not reset."""
        d = LabelTagParser.label_tags_list_to_dict(
            [('tags', ['a']), ('tags', ['b'])]
        )
        self.assertEqual(d['tags'], ['a', 'b'])

    def test_wrap_and_parse_roundtrip(self):
        tags = ['plain', 'with, comma', 'multi\nline']
        text = LabelTagParser.tags_to_text(tags, persistence=True)
        parser = LabelTagParser()
        # Real files end label lines with '\n'. (Without a trailing newline
        # the legacy parser leaks the closing `"""` into the final tag —
        # a quirk ported verbatim for compatibility.)
        parser.parse('label: ' + text + '\n')
        parsed = dict(parser.get_label_tags())
        self.assertEqual(parsed['label'], tags)


class TestHistoryRecord(unittest.TestCase):
    def test_since_until_labels_load(self):
        """Legacy defect #1: since/until labels must not crash on load."""
        record = HistoryRecord('test')
        record.set_label_tags('since', ['-200'])
        record.set_label_tags('until', ['100'])
        self.assertLess(record.since(), 0)
        self.assertGreater(record.until(), 0)
        # since/until are reserved: they must not enter the label dict.
        self.assertNotIn('since', record.get_labels())
        self.assertNotIn('until', record.get_labels())

    def test_unparseable_time_is_zero_int(self):
        """Legacy defect #5: unparseable time stores int 0, not float 0.0."""
        record = HistoryRecord('test')
        record.set_label_tags('time', ['not a time at all ???'])
        self.assertEqual(record.since(), 0)
        self.assertIsInstance(record.since(), int)

    def test_accessor_methods(self):
        """Legacy defect #3: people()/location()/organization() must work."""
        record = HistoryRecord('test')
        record.set_label_tags('people', ['Alice', 'Bob'])
        self.assertEqual(record.people(), ['Alice', 'Bob'])
        self.assertEqual(record.location(), [])
        self.assertEqual(record.organization(), [])

    def test_duplicate_from_deep_copies(self):
        """Legacy defect #4: mutating the copy must not touch the original."""
        src = HistoryRecord('test')
        src.set_label_tags('tags', ['a'])
        dst = HistoryRecord('test')
        dst.duplicate_from(src, includes_uuid=True)
        self.assertEqual(dst.uuid(), src.uuid())
        dst.add_tags('tags', ['b'])
        self.assertEqual(src.get_tags('tags'), ['a'])
        self.assertEqual(dst.get_tags('tags'), ['a', 'b'])


class TestLoaderErrorHandling(unittest.TestCase):
    def test_missing_file_raises(self):
        """Legacy defect #7: failure must be distinguishable from empty."""
        with self.assertRaises(OSError):
            HistoryRecordLoader.from_file('definitely/not/a/real/file.his')

    def test_empty_file_loads_empty(self):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.his', delete=False, encoding='utf-8'
        ) as f:
            temp_path = f.name
        try:
            result = HistoryRecordLoader.from_file(temp_path)
            self.assertEqual(result, {temp_path: []})
        finally:
            Path(temp_path).unlink()

    def test_directory_load_filters_suffix(self):
        """Legacy defect #9: non-.his files in a directory are skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            his_path = Path(tmp) / 'a.his'
            his_path.write_text(
                '[START]: event\ntime: 200年\nevent: hello\n',
                encoding='utf-8',
            )
            (Path(tmp) / 'notes.txt').write_text('not a his file', encoding='utf-8')
            (Path(tmp) / 'readme.md').write_text('# hi', encoding='utf-8')

            result = HistoryRecordLoader.from_directory(tmp)
            self.assertEqual(len(result), 1)
            events = next(iter(result.values()))
            self.assertEqual(len(events), 1)

    def test_normalize_source_uses_ported_depot_root(self):
        depot_root = HistoryRecordLoader.get_local_depot_root()
        self.assertTrue(depot_root.replace('/', '\\').lower().endswith('history\\depot'))
        inside = str(Path(depot_root) / 'example' / 'example.his')
        normalized = HistoryRecordLoader.normalize_source(inside)
        self.assertEqual(normalized.replace('\\', '/'), 'example/example.his')


if __name__ == '__main__':
    unittest.main()
