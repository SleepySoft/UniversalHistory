from typing import Tuple, Union


class JDNTimestamp:
    """
    历史时间核心类 (Integer Fixed-Point JDN)

    存储: 
        self.value (int): 距离 JDN 0 (公元前4713年11月24日 12:00:00) 的总微秒数。

    精度: 
        微秒 (microseconds)。

    数学逻辑:
        1 天 = 86,400,000,000 微秒。
        完全避免 float 运算，彻底解决 23:59:59.999999 进位精度丢失问题。
    """

    __slots__ = ('value',)

    # 常量定义
    SCALE = 1_000_000  # 精度：微秒
    DAY_SECONDS = 86400
    DAY_UNIT = DAY_SECONDS * SCALE  # 一天的总单位数 (864亿)
    HALF_DAY_UNIT = DAY_UNIT // 2  # 半天 (用于校准中午和午夜)

    def __init__(self, total_microseconds: int):
        self.value = int(total_microseconds)

    def __repr__(self):
        return f"<JDNTimestamp(Int): {self.value}>"

    def __eq__(self, other):
        if isinstance(other, JDNTimestamp):
            return self.value == other.value
        return False

    # =========================================================================
    # 构造 (Construction) - 纯整数逻辑
    # =========================================================================

    @classmethod
    def from_ymd_hms(cls, year: int, month: int, day: int,
                     hour: int = 0, minute: int = 0, second: int = 0,
                     microsecond: int = 0) -> 'JDNTimestamp':
        """
        从外推格里高利历构造 (Fliegel & Van Flandern 整数版)
        """
        # 1. 计算日期部分的 JDN 整数 (该值为当日中午 12:00 的 JDN)
        # 算法: Fliegel & Van Flandern
        a = (14 - month) // 12
        y = year + 4800 - a
        m = month + 12 * a - 3

        # 算出的是“日”的整数
        jdn_noon_days = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045

        # 2. 转换为微秒大整数
        # 此时 total_noon 代表当日中午 12:00 的刻度
        total_noon = jdn_noon_days * cls.DAY_UNIT

        # 3. 计算当日时间的微秒偏移
        # 我们需要从“午夜”开始算，所以时间偏移量是 hour:minute:second
        time_offset = (hour * 3600 + minute * 60 + second) * cls.SCALE + microsecond

        # 4. 合并
        # 标准 JDN 是中午起算。
        # 当日 00:00:00 实际上是 (中午JDN - 0.5天)
        # 所以: 最终值 = 中午基准值 - 半天 + 当日时间偏移
        final_value = total_noon - cls.HALF_DAY_UNIT + time_offset

        return cls(final_value)

    @classmethod
    def from_ymd(cls, year: int, month: int, day: int) -> 'JDNTimestamp':
        return cls.from_ymd_hms(year, month, day)

    @classmethod
    def from_iso_week(cls, iso_year: int, week_number: int, weekday: int = 1) -> 'JDNTimestamp':
        jan4 = cls.from_ymd(iso_year, 1, 4)
        jan4_wd = jan4.weekday
        # 纯整数运算：一天就是 DAY_UNIT
        week1_monday_val = jan4.value - (jan4_wd - 1) * cls.DAY_UNIT
        target_val = week1_monday_val + ((week_number - 1) * 7 + (weekday - 1)) * cls.DAY_UNIT
        return cls(target_val)

    # =========================================================================
    # 转换 (Extraction) - 纯整数逻辑
    # =========================================================================

    def to_gregorian(self) -> Tuple[int, int, int, int, int, int, int]:
        """
        返回: (year, month, day, hour, minute, second, microsecond)
        """
        # 1. 还原到以“中午”为整数边界的数值
        # 因为逆向算法基于 Noon JDN 整数
        # 当前值是 Based on Midnight (visually)，但数值轴是 Based on Noon 0.
        # 我们加上半天，这样如果时间是 00:00:00，加上半天后正好是 12:00:00 (前一天? 或者是当天中午?)

        # 逻辑梳理：
        # 假设 2000-01-01 12:00:00. Value = X (整数).
        # 2000-01-01 00:00:00. Value = X - HalfDay.
        # 要调用 Fliegel 算法，我们需要获得 X (日期部分的 JDN 整数)。
        # 2000-01-01 00:00:00 + HalfDay = X. (整除 DAY_UNIT 得到 JDN)
        # 2000-01-01 23:59:59 + HalfDay = X + (Almost 1 Day). (整除 DAY_UNIT 依然得到 JDN)

        adjusted_value = self.value + self.HALF_DAY_UNIT

        # JDN 整数部分 (日)
        jdn_days = adjusted_value // self.DAY_UNIT

        # 当日剩余微秒数 (时间部分)
        time_part = adjusted_value % self.DAY_UNIT

        # 2. Fliegel & Van Flandern 逆向算法 (整数)
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

        # 3. 解析时间部分 (time_part 是微秒总数)
        # 纯整数除法，绝对精确
        total_seconds = time_part // self.SCALE
        microsecond = time_part % self.SCALE

        hour = total_seconds // 3600
        rem_seconds = total_seconds % 3600
        minute = rem_seconds // 60
        second = rem_seconds % 60

        return year, month, day, hour, minute, second, microsecond

    # =========================================================================
    # 属性与计算
    # =========================================================================

    @property
    def year(self) -> int:
        return self.to_gregorian()[0]

    @property
    def weekday(self) -> int:
        # 1=Mon, 7=Sun
        # 计算基于 Noon JDN。
        adjusted_value = self.value + self.HALF_DAY_UNIT
        jdn_days = adjusted_value // self.DAY_UNIT
        wd = (jdn_days + 1) % 7
        return 7 if wd == 0 else wd

    def is_leap_year(self) -> bool:
        y = self.year
        return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)

    def __sub__(self, other):
        if isinstance(other, JDNTimestamp):
            # 返回微秒差值 (int)
            return self.value - other.value
        # 如果减去的是数字，默认当做“天”处理? 还是微秒?
        # 为了避免歧义，建议只允许同类相减，或者明确其他类型是天
        return self.value - int(float(other) * self.DAY_UNIT)

    def __add__(self, days: float):
        # 加天数 (支持小数天)
        # 转换为整数微秒
        us_delta = int(days * self.DAY_UNIT)
        return JDNTimestamp(self.value + us_delta)
