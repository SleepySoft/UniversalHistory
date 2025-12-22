from lunar_python import Lunar, Solar
from JDNTimestamp import JDNTimestamp


class LunarDateBridge:
    class LunarResult:
        def __init__(self, lunar_obj: Lunar):
            self.year = lunar_obj.getYear()
            self.month = abs(lunar_obj.getMonth())
            self.day = lunar_obj.getDay()
            # 闰月判断：lunar_python 某些版本 getMonth() 在闰月时可能返回负数或相同数，
            # 最可靠的是通过 getMonthInChinese 判断是否包含“闰”字，或使用库特定API
            self.is_leap = "闰" in lunar_obj.getMonthInChinese()

            self.year_cn = lunar_obj.getYearInGanZhi()
            self.month_cn = lunar_obj.getMonthInChinese()
            self.day_cn = lunar_obj.getDayInChinese()
            self.animal = lunar_obj.getYearShengXiao()
            self.raw = lunar_obj

        def __repr__(self):
            return f"<农历: {self.year_cn}({self.animal})年 {self.month_cn}{self.day_cn}>"

    @staticmethod
    def to_lunar(jdn_obj: 'JDNTimestamp') -> 'LunarDateBridge.LunarResult':
        y, m, d, h, minute, s, *_ = jdn_obj.to_gregorian()
        try:
            # 必须用 Solar 做中间层，保证精度
            solar = Solar.fromYmdHms(y, m, d, h, minute, s)
            lunar = solar.getLunar()
            return LunarDateBridge.LunarResult(lunar)
        except Exception as e:
            # 针对超出计算范围的年份（lunar_python 范围通常较小）
            raise ValueError(f"农历转换失败 (Year {y}): {e}")

    @staticmethod
    def from_lunar(year: int, month: int, day: int,
                   hour: int = 0, minute: int = 0, second: int = 0,
                   is_leap_month: bool = False) -> 'JDNTimestamp':
        """
        农历 -> JDN
        注意：lunar_python 的 Lunar.fromYmd 初始化时，若该年该月有闰月，
        通常需要查看库的具体实现来指定是闰月。
        此处简化为标准转换。
        """
        try:
            # 构建 Lunar 对象
            # 警告：如果正好是闰月，lunar_python 默认通常指非闰月
            lunar = Lunar.fromYmdHms(year, month, day, hour, minute, second)

            # 转换为 Solar
            solar = lunar.getSolar()

            # 转回 JDN
            return JDNTimestamp.from_ymd_hms(
                solar.getYear(), solar.getMonth(), solar.getDay(),
                solar.getHour(), solar.getMinute(), solar.getSecond()
            )
        except Exception as e:
            raise ValueError(f"无效的农历日期: {year}-{month}-{day}. Error: {str(e)}")
