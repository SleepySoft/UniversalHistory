import unittest
import datetime
from datetime import timezone

# 假设这三个类都在同一个包或当前目录下
from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.chrono.lunar_date_bridge import LunarDateBridge
from universal_history.chrono.python_time_bridge import PythonTimeBridge


class TestJDNTimestamp(unittest.TestCase):

    def assertTimeEqual(self, t1_tuple, t2_tuple, msg=None):
        self.assertEqual(t1_tuple, t2_tuple, msg)

    # 1. 基础往返测试
    def test_round_trip_modern(self):
        y, m, d, h, minute, s, us = 2023, 11, 25, 14, 30, 15, 123456
        ts = JDNTimestamp.from_ymd_hms(y, m, d, h, minute, s, us)
        out = ts.to_gregorian()
        self.assertTimeEqual(out, (y, m, d, h, minute, s, us), "现代时间往返失败")

    def test_round_trip_ancient(self):
        # 公元前 550 年
        y, m, d = -550, 9, 28
        ts = JDNTimestamp.from_ymd(y, m, d)
        out = ts.to_gregorian()
        self.assertEqual(out[:3], (-550, 9, 28))

    def test_end_of_day_precision(self):
        """测试 23:59:59.999999 不会意外进位"""
        y, m, d = 1999, 12, 31
        h, minute, s, us = 23, 59, 59, 999999
        ts = JDNTimestamp.from_ymd_hms(y, m, d, h, minute, s, us)
        out = ts.to_gregorian()
        self.assertTimeEqual(out, (y, m, d, h, minute, s, us))

    def test_midnight_rollover(self):
        """测试加 1 微秒是否完美进位到第二天"""
        y, m, d = 1999, 12, 31
        ts = JDNTimestamp.from_ymd_hms(y, m, d, 23, 59, 59, 999999)

        # 手动加 1 微秒
        ts_next = JDNTimestamp(ts.value + 1)
        out_next = ts_next.to_gregorian()

        self.assertTimeEqual(out_next, (2000, 1, 1, 0, 0, 0, 0))

    # 2. 权威数据锚点测试
    def test_j2000_epoch(self):
        # J2000.0 是 2000-01-01 12:00:00 TT (这里简化为 UTC) -> JDN 2451545.0
        ts = JDNTimestamp.from_ymd_hms(2000, 1, 1, 12, 0, 0)
        # 修正：使用 jdn_float 进行比较，而不是 value (int)
        self.assertAlmostEqual(ts.jdn_float, 2451545.0, places=6, msg="J2000.0 计算偏移")

    def test_unix_epoch_check(self):
        # Unix Epoch 1970-01-01 00:00:00 -> JDN 2440587.5
        ts = JDNTimestamp.from_ymd_hms(1970, 1, 1, 0, 0, 0)
        self.assertAlmostEqual(ts.jdn_float, 2440587.5, places=6)

    # 3. 复杂逻辑
    def test_leap_years(self):
        self.assertTrue(JDNTimestamp.from_year(2000).is_leap_year())
        self.assertTrue(JDNTimestamp.from_year(2024).is_leap_year())
        self.assertFalse(JDNTimestamp.from_year(2100).is_leap_year())

    def test_year_zero_continuity(self):
        """测试 1 BC (0) 到 1 AD (1) 跨度"""
        ts_bc1 = JDNTimestamp.from_ymd(0, 12, 31)
        ts_ad1 = JDNTimestamp.from_ymd(1, 1, 1)
        # 差 1 天
        delta = ts_ad1 - ts_bc1
        self.assertEqual(delta, JDNTimestamp.DAY_UNIT)

    # 4. 星期测试
    def test_weekday(self):
        # 2024-05-20 是周一 (1)
        ts = JDNTimestamp.from_ymd(2024, 5, 20)
        self.assertEqual(ts.weekday, 1)

        # 2024-05-19 是周日 (7)
        ts = JDNTimestamp.from_ymd(2024, 5, 19)
        self.assertEqual(ts.weekday, 7)


class TestPythonTimeBridge(unittest.TestCase):
    def test_timestamp_conversion(self):
        # 测试 Unix 时间戳 0
        ts = PythonTimeBridge.from_unix_timestamp(0)
        self.assertEqual(ts.year, 1970)
        self.assertEqual(ts.to_gregorian()[3], 0)  # hour 0

        # 测试转换回 Unix 时间戳
        ts_now = JDNTimestamp.from_ymd_hms(2023, 1, 1, 0, 0, 0)
        unix_ts = PythonTimeBridge.to_unix_timestamp(ts_now)
        # 2023-1-1 00:00 UTC = 1672531200
        self.assertAlmostEqual(unix_ts, 1672531200.0, places=1)


if __name__ == '__main__':
    unittest.main()
