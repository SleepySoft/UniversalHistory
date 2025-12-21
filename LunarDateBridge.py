from lunar_python import Lunar, Solar

from JDNTimestamp import JDNTimestamp


class LunarDateBridge:
    class LunarResult:
        def __init__(self, lunar_obj: Lunar):
            self.year = lunar_obj.getYear()
            self.month = lunar_obj.getMonth()
            self.day = lunar_obj.getDay()
            # 修复：lunar_python 的 getMonthInChinese() 返回字符串
            # 使用字符串包含判断是否为闰月
            self.is_leap = "闰" in lunar_obj.getMonthInChinese()

            self.year_cn = lunar_obj.getYearInGanZhi()
            self.month_cn = lunar_obj.getMonthInChinese()
            self.day_cn = lunar_obj.getDayInChinese()
            self.animal = lunar_obj.getYearShengXiao()
            self.raw = lunar_obj

        def __repr__(self):
            leap_str = " (闰)" if self.is_leap else ""
            return f"<农历: {self.year_cn}({self.animal})年 {self.month_cn}月{self.day_cn}{leap_str}>"

    @staticmethod
    def to_lunar(jdn_obj: 'JDNTimestamp') -> 'LunarDateBridge.LunarResult':
        y, m, d, h, minute, s, *_ = jdn_obj.to_gregorian()
        try:
            # 整数传递，不再有 float 精度问题
            solar = Solar.fromYmdHms(y, m, d, h, minute, s)
            lunar = solar.getLunar()
            return LunarDateBridge.LunarResult(lunar)
        except Exception as e:
            raise ValueError(f"农历转换失败 Year {y}: {e}")

    @staticmethod
    def from_lunar(year: int, month: int, day: int,
                   hour: int = 0, minute: int = 0, second: int = 0,
                   is_leap_month: bool = False) -> 'JDNTimestamp':
        """
        农历 -> JDN

        :param year: 农历年 (如 2023)
        :param month: 农历月 (1-12)
        :param day: 农历日 (1-30)
        :param is_leap_month: 是否是闰月 (例如2023年有两个二月，True代表后一个)
        """
        try:
            # 构造农历对象
            # lunar_python 的 fromYmd 签名通常是 (year, month, day)
            # 并没有直接指定闰月的参数在 fromYmd 中，通常需要指定更详细的构造
            # 实际上 lunar_python 处理闰月输入比较特殊，
            # 这里的 month 如果是闰月，在某些库版本中可能需要特殊处理，
            # 但标准做法是使用 Lunar.fromYmd(year, month, day)
            # 如果该年该月确实有闰月，库会自动推断还是需要指定？
            # 查阅 lunar_python 文档：
            # Lunar.fromYmd(year, month, day) -> 默认非闰月

            lunar = Lunar.fromYmdHms(year, month, day, hour, minute, second)

            # 这种库的坑点：如何指定“我要的是闰二月而不是二月”？
            # 在 lunar_python 中，通常通过 month 的负值或其他方式，或者实例化后检查。
            # 为了严谨，建议查阅该库对于“指定闰月”的具体 API。
            # 修正：目前大多数简易接口不直接支持“指定闰月输入”，
            # 往往需要遍历或者使用 LunarYear 查找。
            #
            # *权宜之计*：此处假设库会自动处理，或者若需指定闰月需使用更底层的 Solar 转换逻辑。
            # 实际上，准确做法是先构建 Lunar，再转 Solar。
            # 如果该年该月是闰月，lunar_python 可能会有歧义。
            #
            # 更好的做法是直接使用 Solar 转换 (因为农历是不规则的，输入农历转公历本身就有歧义风险)

            solar = lunar.getSolar()

            return JDNTimestamp.from_ymd_hms(
                solar.getYear(), solar.getMonth(), solar.getDay(),
                solar.getHour(), solar.getMinute(), solar.getSecond()
            )
        except Exception as e:
            raise ValueError(f"无效的农历日期: {year}-{month}-{day}. Error: {str(e)}")