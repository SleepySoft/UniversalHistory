import datetime
import time
from typing import Optional

from JDNTimestamp import JDNTimestamp


class PythonTimeBridge:
    """
    负责 JDNTimestamp 与 Python 原生 datetime/timestamp 的互转
    """

    # Unix Epoch (1970-01-01 00:00:00 UTC) 的 JDN
    UNIX_EPOCH_JDN = 2440587.5

    @staticmethod
    def to_datetime(jdn_obj: 'JDNTimestamp', tz: datetime.timezone = datetime.timezone.utc) -> datetime.datetime:
        y, m, d, h, minute, s, us = jdn_obj.to_gregorian()
        if y < 1 or y > 9999:
            raise OverflowError(f"时间超出 Python datetime 范围: {y}")
        return datetime.datetime(y, m, d, h, minute, s, us, tzinfo=datetime.timezone.utc).astimezone(tz)

    @staticmethod
    def from_datetime(dt: datetime.datetime) -> 'JDNTimestamp':
        if dt.tzinfo is None:
            dt_utc = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            dt_utc = dt.astimezone(datetime.timezone.utc)
        return JDNTimestamp.from_ymd_hms(
            dt_utc.year, dt_utc.month, dt_utc.day,
            dt_utc.hour, dt_utc.minute, dt_utc.second, dt_utc.microsecond
        )

    @staticmethod
    def to_unix_timestamp(jdn_obj: 'JDNTimestamp') -> float:
        """
        转换为 Unix 时间戳 (秒)。
        支持负数 (1970年之前)。
        """
        # 公式: (JDN - Epoch) * 86400
        return (jdn_obj.value - PythonTimeBridge.UNIX_EPOCH_JDN) * 86400.0

    @staticmethod
    def from_unix_timestamp(timestamp: float) -> 'JDNTimestamp':
        """
        从 Unix 时间戳构造。
        """
        jdn_val = (timestamp / 86400.0) + PythonTimeBridge.UNIX_EPOCH_JDN
        return JDNTimestamp(jdn_val)