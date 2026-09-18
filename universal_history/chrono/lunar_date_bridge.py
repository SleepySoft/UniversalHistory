from lunar_python import Lunar, Solar
from universal_history.chrono.jdn_timestamp import JDNTimestamp


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

        `is_leap_month=True` 时按闰月处理；lunar_python 约定闰月用负数月份
        传入（如闰二月传 -2）。若该年该月没有闰月，库会抛出异常并在此
        包装为 ValueError。
        """
        try:
            # lunar_python 约定：闰月以负数月份构造。
            lunar_month = -month if is_leap_month else month
            lunar = Lunar.fromYmdHms(year, lunar_month, day, hour, minute, second)

            # 防御：部分版本对不存在的闰月会静默落到平月，回读校验。
            if is_leap_month and "闰" not in lunar.getMonthInChinese():
                raise ValueError(f"{year} 年 {month} 月不是闰月")

            # 转换为 Solar
            solar = lunar.getSolar()

            # 转回 JDN
            return JDNTimestamp.from_ymd_hms(
                solar.getYear(), solar.getMonth(), solar.getDay(),
                solar.getHour(), solar.getMinute(), solar.getSecond()
            )
        except Exception as e:
            raise ValueError(f"无效的农历日期: {year}-{month}-{day}. Error: {str(e)}")
