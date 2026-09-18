from typing import Tuple, Union
from functools import total_ordering


@total_ordering
class JDNTimestamp:
    """
    历史时间核心类 (Integer Fixed-Point JDN)

    存储:
        self.value (int): 距离 JDN 0 (公元前4713年1月1日 12:00:00 UTC, Julian Proleptic) 的总微秒数。

    精度:
        微秒 (microseconds)。整数存储，绝对无损。
    """

    __slots__ = ('value',)

    # 常量定义
    SCALE = 1_000_000  # 1秒 = 1,000,000 微秒
    DAY_SECONDS = 86400
    DAY_UNIT = DAY_SECONDS * SCALE  # 一天的总微秒数 (86,400,000,000)
    HALF_DAY_UNIT = DAY_UNIT // 2  # 半天

    def __init__(self, total_microseconds: int):
        self.value = int(total_microseconds)

    def __repr__(self):
        # 方便调试，直接显示转换后的公历
        y, m, d, h, mn, s, us = self.to_gregorian()
        return f"<JDNTimestamp: {y:04d}-{m:02d}-{d:02d} {h:02d}:{mn:02d}:{s:02d}.{us:06d}>"

    # =========================================================================
    # 辅助属性 (用于调试和验证)
    # =========================================================================

    @property
    def jdn_float(self) -> float:
        """返回标准的浮点型 JDN (天数)，用于科学计算或对比，会有精度损失"""
        return self.value / self.DAY_UNIT

    # =========================================================================
    # 构造 (Construction) - 纯整数逻辑
    # =========================================================================

    @classmethod
    def from_ymd_hms(cls, year: int, month: int, day: int,
                     hour: int = 0, minute: int = 0, second: int = 0,
                     microsecond: int = 0) -> 'JDNTimestamp':
        """
        从外推格里高利历构造
        算法: Fliegel & Van Flandern (适用于转换 Noon JDN)
        """
        # 1. 计算该日期 "12:00:00" 时对应的 JDN 整数
        a = (14 - month) // 12
        y = year + 4800 - a
        m = month + 12 * a - 3

        # 计算出的 jdn_noon_days 是一个整数，代表当天的中午12点
        jdn_noon_days = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045

        # 2. 转换为微秒大整数 (Base Noon)
        total_noon = jdn_noon_days * cls.DAY_UNIT

        # 3. 计算从“当日00:00”到“目标时间”的偏移量
        time_offset = (hour * 3600 + minute * 60 + second) * cls.SCALE + microsecond

        # 4. 核心逻辑：
        # JDN 整数值对应的是 12:00。
        # 00:00 对应的是 (Noon - 0.5 Day)。
        # 所以: Value = (NoonValue - HalfDay) + TimeOffset
        final_value = total_noon - cls.HALF_DAY_UNIT + time_offset

        return cls(final_value)

    @classmethod
    def from_ymd(cls, year: int, month: int, day: int) -> 'JDNTimestamp':
        return cls.from_ymd_hms(year, month, day)

    @classmethod
    def from_year(cls, year: int) -> 'JDNTimestamp':
        """构造某年1月1日 00:00:00"""
        return cls.from_ymd_hms(year, 1, 1)

    @classmethod
    def from_iso_week(cls, iso_year: int, week_number: int, weekday: int = 1) -> 'JDNTimestamp':
        # 1. 找到 ISO 年的基准日：1月4日
        jan4 = cls.from_ymd(iso_year, 1, 4)

        # 2. 找到 1月4日 所在周的周一 (ISO Week 1 的起始)
        # weekday: Mon=1 ... Sun=7
        jan4_wd = jan4.weekday  # 1-7

        # 回退 (weekday - 1) 天到达周一
        week1_monday_val = jan4.value - (jan4_wd - 1) * cls.DAY_UNIT

        # 3. 加上周数偏移和天数偏移
        # (week_number - 1) * 7 天 + (weekday - 1) 天
        days_to_add = (week_number - 1) * 7 + (weekday - 1)
        target_val = week1_monday_val + days_to_add * cls.DAY_UNIT

        return cls(target_val)

    # =========================================================================
    # 转换 (Extraction) - 纯整数逻辑
    # =========================================================================

    def to_gregorian(self) -> Tuple[int, int, int, int, int, int, int]:
        """
        返回: (year, month, day, hour, minute, second, microsecond)
        """
        # 1. 调整回 Noon Base 进行日期计算
        # 我们的 value 是基于 JDN 0.0 (Noon)。
        # 如果是 00:00:00，value 尾数是 .5 * DAY_UNIT。
        # 为了利用整数除法算出“今天是JDN第几天(整数)”，我们需要加上半天，
        # 让 00:00:00 变成下一个整数边界（或保持在当前整数区间，取决于具体的Fliegel逆运算要求）。
        #
        # Fliegel 算法接受一个整数 JDN，返回该 JDN 中午对应的 YMD。
        # 举例：2000-01-01 12:00 -> JDN 2451545.0
        #      2000-01-01 00:00 -> JDN 2451544.5
        # 我们希望 00:00 属于 2000-01-01。
        # 2451544.5 + 0.5 = 2451545.0。 整数部分 2451545。-> Fliegel 算出 2000-01-01。正确。

        adjusted_value = self.value + self.HALF_DAY_UNIT

        # JDN Days (整数)
        jdn_days = adjusted_value // self.DAY_UNIT

        # 剩余部分是“距离当日中午12点之前”还是“距离当日0点”？
        # adjusted_value 是把时间轴平移了 12小时。
        # 所以 adjusted_value % DAY_UNIT 得到的是“距离当日 00:00:00 逝去的微秒数”。
        time_part = adjusted_value % self.DAY_UNIT

        # 2. Fliegel & Van Flandern 逆向算法
        L = jdn_days + 68569
        N = (4 * L) // 146097
        L = L - (146097 * N + 3) // 4
        I = (4000 * (L + 1)) // 1461001
        L = L - (1461 * I) // 4 + 31
        J = (80 * L) // 2447
        day = L - (2447 * J) // 80
        L = J // 11
        month = J + 2 - 12 * L
        year = 100 * (N - 49) + I + L

        # 3. 解析时间
        total_seconds = time_part // self.SCALE
        microsecond = time_part % self.SCALE

        hour = total_seconds // 3600
        rem_seconds = total_seconds % 3600
        minute = rem_seconds // 60
        second = rem_seconds % 60

        return int(year), int(month), int(day), int(hour), int(minute), int(second), int(microsecond)

    # =========================================================================
    # 属性与计算
    # =========================================================================

    @property
    def year(self) -> int:
        return self.to_gregorian()[0]

    @property
    def month(self) -> int:
        return self.to_gregorian()[1]

    @property
    def day(self) -> int:
        return self.to_gregorian()[2]

    @property
    def hour(self) -> int:
        return self.to_gregorian()[3]

    @property
    def minute(self) -> int:
        return self.to_gregorian()[4]

    @property
    def second(self) -> int:
        return self.to_gregorian()[5]

    @property
    def microsecond(self) -> int:
        return self.to_gregorian()[6]

    @property
    def weekday(self) -> int:
        # 1=Mon, 7=Sun
        # JDN 0 (Monday noon) -> 0.
        # Calculation: (JDN_Noon + 0.5 + 0) ? No.
        # JDN 整数对应的是中午。
        # 2451545 (2000-01-01) 是周六(6).
        # (2451545 + 1) % 7 = 2451546 % 7 ...
        # 常规公式: (JDN + 1) % 7.
        # 我们用 adjusted_value // DAY_UNIT 得到的就是 JDN 整数。
        adjusted_value = self.value + self.HALF_DAY_UNIT
        jdn_days = adjusted_value // self.DAY_UNIT
        wd = (jdn_days) % 7
        # 注意: JDN 0 是周一(12:00)。(0)%7 = 0.
        # 我们想要 1=Mon, ..., 6=Sat, 0(or 7)=Sun.
        # 如果 JDN=0 -> Mon(1). 公式应为 (JDN + 1) % 7 ?
        # 验证: 2000-01-01 JDN 2451545. (2451545+1)%7 = 2451546%7 = 0 (Wait, 2451546 is divisible by 7? 2451546/7=350220.8).
        # 实际上: JDN 0 is Mon.
        # (0 + 0) % 7 = 0 -> let's map 0->Mon? No, standard is 0->Mon, 1->Tue... 6->Sun.
        # Python: 0=Mon, 6=Sun? No, ISO is 1=Mon, 7=Sun.
        # Let's calibrate: 2000-01-01 was Saturday (6).
        # JDN 2451545. (2451545 + 1) % 7 = ?
        # 2451545 % 7 = 5.
        # So Mon(0) -> 0. Sat(5) -> 5? No we want Sat=6.
        # Formula: (JDN % 7) + 1.
        # If JDN=0 (Mon), 0+1=1 (Mon). Correct.
        # If JDN=2451545, 5+1=6 (Sat). Correct.
        wd = (jdn_days % 7) + 1
        return wd

    def is_leap_year(self) -> bool:
        # Proleptic Gregorian 规则，直接作用于天文纪年（含 0 与负年）。
        # Python 的 % 是向下取模，对负年的可整除判定与正年一致，
        # 且与 from_ymd_hms 的 Fliegel 正向算法（移位后地板除）语义吻合，
        # 无需取 abs。例如：0 (1 BC)、-4 (5 BC) 为闰年；-100 (101 BC) 不是。
        y = self.year
        return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)

    # =========================================================================
    # 1. 比较运算符 (Rich Comparison) - 解决 '>=' not supported 报错
    # =========================================================================

    def __eq__(self, other):
        if isinstance(other, JDNTimestamp):
            return self.value == other.value
        return False

    def __lt__(self, other):
        if isinstance(other, JDNTimestamp):
            return self.value < other.value
        return NotImplemented

    # 由于使用了 @total_ordering，__le__, __gt__, __ge__ 会自动生成

    def __hash__(self):
        return hash(self.value)

    def __add__(self, other):
        if isinstance(other, (int, float)):
            # 加天数 (支持小数天)
            us_delta = int(other * self.DAY_UNIT)
            return JDNTimestamp(self.value + us_delta)
        raise TypeError("Can only add numeric days (float/int) to JDNTimestamp")

    def __sub__(self, other):
        if isinstance(other, JDNTimestamp):
            # 返回微秒差值 (int)
            return self.value - other.value

        if isinstance(other, (int, float)):
            # 减去天数
            offset_us = int(other * self.DAY_UNIT)
            return JDNTimestamp(self.value - offset_us)

        return NotImplemented
