import unittest
import datetime
from datetime import timezone, timedelta

# 导入你的核心类
from universal_history.chrono.jdn_timestamp import JDNTimestamp
from universal_history.chrono.lunar_date_bridge import LunarDateBridge
from universal_history.chrono.python_time_bridge import PythonTimeBridge


class TestComprehensiveHistorySystem(unittest.TestCase):

    # =========================================================================
    # Part 1: 核心算术与逻辑 (The Integer Engine)
    # =========================================================================

    def test_arithmetic_consistency(self):
        """测试加减法的数学一致性"""
        t0 = JDNTimestamp.from_ymd(2000, 1, 1)  # 2000-01-01

        # 1. 加法测试: +1.5天
        t1 = t0 + 1.5
        y, m, d, h, *_ = t1.to_gregorian()
        self.assertEqual((y, m, d, h), (2000, 1, 2, 12), "加1.5天计算错误")

        # 2. 减法测试: 两个 JDN 相减应得到微秒差值
        diff_microseconds = t1 - t0
        self.assertEqual(diff_microseconds, 1.5 * 86400 * 1_000_000, "时间差值计算错误")

        # 3. 比较运算符重载
        self.assertTrue(t0 < t1)
        self.assertTrue(t1 > t0)
        self.assertTrue(t0 != t1)
        self.assertTrue(t0 == JDNTimestamp.from_ymd(2000, 1, 1))

    def test_microsecond_overflow(self):
        """测试微秒溢出进位 (999999 -> 000000)"""
        # 构造: 2023-12-31 23:59:59.999999
        ts = JDNTimestamp.from_ymd_hms(2023, 12, 31, 23, 59, 59, 999999)

        # +1 微秒 (0.000001 秒 / 86400 秒/天 = day fraction)
        # 但我们核心是 int，直接加微秒最精确
        # 这里模拟 add float days: 1 us = 1 / (86400 * 1e6) days
        delta_days = 1.0 / (86400.0 * 1_000_000.0)
        ts_next = ts + delta_days

        y, m, d, h, mn, s, us = ts_next.to_gregorian()
        self.assertEqual((y, m, d, h, mn, s, us), (2024, 1, 1, 0, 0, 0, 0),
                         "跨年微秒进位失败")

    # =========================================================================
    # Part 2: 历史与日历规则 (Historical & Calendar Rules)
    # =========================================================================

    def test_proleptic_gregorian_continuity(self):
        """
        [关键测试]
        验证这是 Proleptic Gregorian (外推格里高利历)。
        历史上 1582年10月4日之后紧接着是 1582年10月15日 (跳过了10天)。
        但你的算法应该是数学连续的，不应该有跳跃。
        这意味着 1582-10-05 在你的系统中是存在的。
        """
        ts_before = JDNTimestamp.from_ymd(1582, 10, 4)
        ts_test = JDNTimestamp.from_ymd(1582, 10, 5)  # 历史上不存在，但数学上存在

        # 验证连续性：相差1天
        diff = ts_test - ts_before
        self.assertEqual(diff, JDNTimestamp.DAY_UNIT, "外推历法应该保持数学连续，不应模拟历史跳跃")

    def test_bc_ad_transition(self):
        """
        测试公元前(BC)到公元后(AD)的跨越。
        JDN 系统使用天文学年份：
        公元 1 年 = Year 1
        公元前 1 年 = Year 0
        公元前 2 年 = Year -1
        """
        # 验证 Year 0 存在且是闰年 (根据 Proleptic 规则: 0 % 4 == 0)
        ts_zero = JDNTimestamp.from_year(0)
        self.assertTrue(ts_zero.is_leap_year(), "Year 0 应该是闰年")

        # 验证 0年2月29日 存在
        ts_leap_day = JDNTimestamp.from_ymd(0, 2, 29)
        self.assertEqual(ts_leap_day.day, 29)

        # 验证跨年连续性: -1年12月31日 -> 0年1月1日
        ts_neg_end = JDNTimestamp.from_ymd(-1, 12, 31)
        ts_zero_start = JDNTimestamp.from_ymd(0, 1, 1)
        self.assertEqual(ts_zero_start - ts_neg_end, JDNTimestamp.DAY_UNIT)

    def test_leap_year_rules_comprehensive(self):
        """全面测试闰年规则 (4年一闰, 100年不闰, 400年又闰)"""
        leap_years = [-400, 0, 1996, 2000, 2024, 2400]
        common_years = [-100, 1900, 2023, 2100]

        for y in leap_years:
            self.assertTrue(JDNTimestamp.from_year(y).is_leap_year(), f"{y} 应该是闰年")

        for y in common_years:
            self.assertFalse(JDNTimestamp.from_year(y).is_leap_year(), f"{y} 应该是平年")

    # =========================================================================
    # Part 3: Python 桥接与时区 (The Python Bridge)
    # =========================================================================

    def test_timezone_conversion(self):
        """
        测试：北京时间 2023-01-01 08:00:00 -> JDN -> UTC 2023-01-01 00:00:00
        """
        tz_cn = timezone(timedelta(hours=8))
        dt_cn = datetime.datetime(2023, 1, 1, 8, 0, 0, tzinfo=tz_cn)

        # 1. 导入 JDN
        ts = PythonTimeBridge.from_datetime(dt_cn)

        # 2. 导出回 Python (指定 UTC)
        dt_utc = PythonTimeBridge.to_datetime(ts, tz=timezone.utc)

        self.assertEqual(dt_utc.year, 2023)
        self.assertEqual(dt_utc.hour, 0)  # 8点 - 8小时 = 0点

        # 3. 导出回 Python (指定 北京时间)
        dt_back_cn = PythonTimeBridge.to_datetime(ts, tz=tz_cn)
        self.assertEqual(dt_back_cn.hour, 8)

    def test_python_min_max_boundaries(self):
        """测试 Python datetime 的极限 (Year 1 到 9999)"""
        # Min
        ts_min = JDNTimestamp.from_ymd(1, 1, 1)
        dt_min = PythonTimeBridge.to_datetime(ts_min)
        self.assertEqual(dt_min.year, 1)

        # Max
        # 错误修复：这里包含时间，必须用 from_ymd_hms
        ts_max = JDNTimestamp.from_ymd_hms(9999, 12, 31, 23, 59, 59)
        dt_max = PythonTimeBridge.to_datetime(ts_max)
        self.assertEqual(dt_max.year, 9999)

        # Overflow
        ts_over = JDNTimestamp.from_ymd(10000, 1, 1)
        with self.assertRaises(OverflowError):
            PythonTimeBridge.to_datetime(ts_over)

    # =========================================================================
    # Part 4: 农历桥接 (Lunar Bridge)
    # =========================================================================

    def test_lunar_leap_month_handling(self):
        """
        测试农历闰月年份。
        2023年有闰二月 (Leap Month 2)。
        """
        # 2023-03-22 是公历，对应 农历 癸卯年 闰二月 初一
        # 注意：lunar_python 可能会根据具体的时区或计算有点微差，这里用标准对照

        ts = JDNTimestamp.from_ymd(2023, 3, 22)
        lunar_res = LunarDateBridge.to_lunar(ts)

        # 验证
        self.assertEqual(lunar_res.year, 2023)
        self.assertEqual(lunar_res.month, 2)
        self.assertTrue(lunar_res.is_leap, "2023-03-22 应该是农历闰二月")
        self.assertEqual(lunar_res.day_cn, "初一")

    def test_solar_terms_influence(self):
        """测试节气转换 (立春 vs 春节)"""
        # 2024-02-04 16:27:00 是立春
        # 但 2024年春节是 2月10日。
        # 所以 2月4日 仍然属于 农历2023年 (癸卯兔年)。

        ts = JDNTimestamp.from_ymd_hms(2024, 2, 4, 16, 27, 0)
        lunar_res = LunarDateBridge.to_lunar(ts)

        # 核心验证：虽然公历是2024，但农历年应该是2023
        self.assertEqual(lunar_res.year, 2023, "立春在春节前，年份应仍为旧年(2023)")

        # 验证生肖 (癸卯兔)
        self.assertEqual(lunar_res.animal, "兔")

        # 验证月份 (腊月/12月)
        self.assertEqual(lunar_res.month, 12)


if __name__ == '__main__':
    unittest.main()
