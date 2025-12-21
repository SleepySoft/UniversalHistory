import unittest
import math
import datetime
from datetime import timezone

from JDNTimestamp import JDNTimestamp
from LunarDateBridge import LunarDateBridge
from PythonTimeBridge import PythonTimeBridge


# 假设你的类定义在 history_time.py 中
# from history_time import JDNTimestamp, PythonTimeBridge, LunarDateBridge

# 为了演示方便，这里假设类已经存在于当前命名空间
# (请将之前实现的三个类 JDNTimestamp, PythonTimeBridge, LunarDateBridge 代码粘贴在同一文件或导入)

class TestJDNTimestamp(unittest.TestCase):

    def assertTimeEqual(self, t1_tuple, t2_tuple, msg=None):
        # 纯整数比较，必须完全相等，没有任何 delta 容忍
        self.assertEqual(t1_tuple, t2_tuple, msg)

    # ----------------------------------------------------------------
    # 1. 基础往返测试 (Round Trip)
    # ----------------------------------------------------------------

    # 1. 往返测试 (现在应该完美通过)
    def test_round_trip_modern(self):
        y, m, d, h, minute, s, us = 2023, 11, 25, 14, 30, 15, 123456
        ts = JDNTimestamp.from_ymd_hms(y, m, d, h, minute, s + us / 1e6)
        out = ts.to_gregorian()
        self.assertTimeEqual(out, (y, m, d, h, minute, s, us), "现代时间往返失败")

    def test_round_trip_ancient(self):
        y, m, d = -550, 9, 28
        ts = JDNTimestamp.from_ymd(y, m, d)
        out = ts.to_gregorian()
        self.assertEqual(out[:3], (-550, 9, 28))

    def test_round_trip_end_of_day(self):
        """测试一天的最后一微秒 (进位测试)"""
        # 23:59:59.999999
        y, m, d = 1999, 12, 31
        h, minute, s, us = 23, 59, 59, 999999

        ts = JDNTimestamp.from_ymd_hms(y, m, d, h, minute, s + us / 1e6)
        out = ts.to_gregorian()
        self.assertTimeEqual(out, (y, m, d, h, minute, s, us), "午夜前微秒精度丢失")

    def test_round_trip_precision_edge(self):
        """
        测试午夜前最后一微秒的精度。
        这是定点数系统的终极测试。
        """
        # 1999-12-31 23:59:59.999999
        y, m, d, h, min, s, us = 1999, 12, 31, 23, 59, 59, 999999
        ts = JDNTimestamp.from_ymd_hms(y, m, d, h, min, s, us)

        # 1. 验证往返读取是否一致
        out = ts.to_gregorian()
        self.assertTimeEqual(out, (y, m, d, h, min, s, us), "读取值与构造值不一致")

        # 2. 验证 +1 微秒是否完美进位
        # 1微秒 = 1 (因为内部存储就是微秒)
        # 但我们对外接口是 add days (float)，所以我们手动构造一下验证逻辑
        # 这里为了测试核心逻辑，直接操作 value (模拟加法)
        ts_next = JDNTimestamp(ts.value + 1)
        out_next = ts_next.to_gregorian()

        # 应该精确变为 2000-01-01 00:00:00.000000
        self.assertTimeEqual(out_next, (2000, 1, 1, 0, 0, 0, 0), "微秒进位失败")

    # ----------------------------------------------------------------
    # 2. 权威数据锚点测试 (Golden Data)
    # ----------------------------------------------------------------

    def test_j2000_epoch(self):
        ts = JDNTimestamp.from_ymd_hms(2000, 1, 1, 12, 0, 0)
        self.assertAlmostEqual(ts.value, 2451545.0, places=6, msg="J2000.0 计算偏移")

    def test_julian_epoch_in_proleptic_gregorian(self):
        """JDN 0 对应 -4713年 11月 24日 12:00:00"""
        ts = JDNTimestamp(0)
        y, m, d, h, *_ = ts.to_gregorian()
        self.assertEqual(y, -4713)
        self.assertEqual(m, 11)
        self.assertEqual(d, 24)
        self.assertEqual(h, 12)

    # ----------------------------------------------------------------
    # 3. 复杂逻辑测试 (闰年与跨零年)
    # ----------------------------------------------------------------

    def test_leap_years(self):
        # 2000 (是), 2024 (是), 0 (1BC, 是), -4 (5BC, 是)
        self.assertTrue(JDNTimestamp.from_year(2000).is_leap_year())
        self.assertTrue(JDNTimestamp.from_year(0).is_leap_year())
        # 1900 (否), 2023 (否)
        self.assertFalse(JDNTimestamp.from_year(1900).is_leap_year())
        self.assertFalse(JDNTimestamp.from_year(2023).is_leap_year())

    def test_year_zero_continuity(self):
        """
        测试从 1 BC (0) 到 1 AD (1) 的连续性
        """
        # 0年12月31日
        ts_bc1_end = JDNTimestamp.from_ymd(0, 12, 31)
        # 1年1月1日
        ts_ad1_start = JDNTimestamp.from_ymd(1, 1, 1)

        diff = ts_ad1_start - ts_bc1_end
        self.assertEqual(diff, 1.0, "公元前1年最后一天到公元1年第一天应该只差1天")

    # ----------------------------------------------------------------
    # 4. 星期与 ISO 周
    # ----------------------------------------------------------------

    def test_weekday(self):
        """验证星期计算"""
        # 2023-11-26 是周日 (7)
        ts = JDNTimestamp.from_ymd(2023, 11, 26)
        self.assertEqual(ts.weekday, 7)

        # 2000-01-01 是周六 (6)
        ts = JDNTimestamp.from_ymd(2000, 1, 1)
        self.assertEqual(ts.weekday, 6)

    def test_iso_week_constructor(self):
        ts = JDNTimestamp.from_iso_week(2023, 1, 1)
        y, m, d, *_ = ts.to_gregorian()
        self.assertEqual((y, m, d), (2023, 1, 2))


class TestPythonTimeBridge(unittest.TestCase):

    def test_modern_datetime(self):
        now = datetime.datetime.now(timezone.utc)
        ts = PythonTimeBridge.from_datetime(now)
        dt_back = PythonTimeBridge.to_datetime(ts)
        self.assertEqual(now.year, dt_back.year)

    def test_unix_epoch(self):
        """测试 Unix 纪元转换"""
        # 1970-01-01 00:00:00 UTC
        ts = PythonTimeBridge.from_unix_timestamp(0)
        y, m, d, h, *_ = ts.to_gregorian()
        self.assertEqual((y, m, d, h), (1970, 1, 1, 0))

        # 负时间戳 (1969-12-31)
        ts_neg = PythonTimeBridge.from_unix_timestamp(-86400)
        y, m, d, *_ = ts_neg.to_gregorian()
        self.assertEqual((y, m, d), (1969, 12, 31))

    def test_datetime_overflow(self):
        # 10000年 应该触发 OverflowError
        future_ts = JDNTimestamp.from_year(10000)
        with self.assertRaisesRegex(OverflowError, "时间超出 Python datetime 范围"):
            PythonTimeBridge.to_datetime(future_ts)

    def test_datetime_conversion(self):
        now = datetime.datetime.now(timezone.utc)
        ts = PythonTimeBridge.from_datetime(now)
        dt_back = PythonTimeBridge.to_datetime(ts)
        self.assertEqual(now, dt_back)


class TestLunarDateBridge(unittest.TestCase):
    def test_lunar_anchor_2024(self):
        # 2024-02-10 (甲辰年 正月 初一)
        ts = JDNTimestamp.from_ymd(2024, 2, 10)
        lunar = LunarDateBridge.to_lunar(ts)
        self.assertEqual(lunar.year, 2024)
        self.assertEqual(lunar.day_cn, "初一")

    def test_prehistory_lunar_robustness(self):
        # 测试对于过于古老的时间，是否能优雅失败
        # 比如 -5350 年，lunar_python 可能会崩溃
        ts = JDNTimestamp.from_year(-5350)
        try:
            LunarDateBridge.to_lunar(ts)
        except ValueError as e:
            # 我们期望它抛出 ValueError 而不是底层的 Exception
            self.assertIn("超出农历库计算范围", str(e))


if __name__ == '__main__':
    unittest.main()