import datetime
from datetime import timezone
from universal_history.chrono.jdn_timestamp import JDNTimestamp


class PythonTimeBridge:
    """
    负责 JDNTimestamp 与 Python 原生 datetime/timestamp 的互转
    """

    # Unix Epoch (1970-01-01 00:00:00 UTC) 对应的 JDN
    # 1970-01-01 12:00:00 是 2440588.0
    # 所以 00:00:00 是 2440587.5
    UNIX_EPOCH_JDN_DAYS = 2440587.5
    UNIX_EPOCH_MICROSECONDS = int(UNIX_EPOCH_JDN_DAYS * JDNTimestamp.DAY_UNIT)

    @staticmethod
    def to_datetime(jdn_obj: 'JDNTimestamp', tz: datetime.timezone = datetime.timezone.utc) -> datetime.datetime:
        y, m, d, h, minute, s, us = jdn_obj.to_gregorian()
        if y < 1 or y > 9999:
            raise OverflowError(f"时间超出 Python datetime 范围 (1-9999): {y}")

        dt_utc = datetime.datetime(y, m, d, h, minute, s, us, tzinfo=datetime.timezone.utc)
        return dt_utc.astimezone(tz)

    @staticmethod
    def from_datetime(dt: datetime.datetime) -> 'JDNTimestamp':
        # 强制转为 UTC，消除时区差异对绝对时间点的影响
        if dt.tzinfo is None:
            # 如果是 naive time，假定为本地时间或 UTC？
            # 最佳实践：假设为 UTC，或者抛出警告。这里假设为 UTC。
            dt_utc = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            dt_utc = dt.astimezone(datetime.timezone.utc)

        return JDNTimestamp.from_ymd_hms(
            dt_utc.year, dt_utc.month, dt_utc.day,
            dt_utc.hour, dt_utc.minute, dt_utc.second, dt_utc.microsecond
        )

    @staticmethod
    def to_unix_timestamp(jdn_obj: 'JDNTimestamp') -> float:
        """转换为 Unix 时间戳 (秒)"""
        diff_us = jdn_obj.value - PythonTimeBridge.UNIX_EPOCH_MICROSECONDS
        return diff_us / 1_000_000.0

    @staticmethod
    def from_unix_timestamp(timestamp: float) -> 'JDNTimestamp':
        """从 Unix 时间戳构造"""
        # timestamp 是秒
        offset_us = int(timestamp * 1_000_000)
        total_us = PythonTimeBridge.UNIX_EPOCH_MICROSECONDS + offset_us
        return JDNTimestamp(total_us)
