# HOW · JDNTimestamp 规范

> 实现：`universal_history/chrono/jdn_timestamp.py`。设计规范：`docs/core_design.md`（§1-4）。与旧版逐点差异见 [../why/01-time-system.md](../why/01-time-system.md)。

## 1. 内部表示

- 存储：`self.value: int` = 距 JDN 0 的总**微秒**数；`__slots__=('value',)`。
- 常量：`SCALE=1_000_000`、`DAY_SECONDS=86400`、`DAY_UNIT=86_400_000_000`、`HALF_DAY_UNIT=DAY_UNIT//2`。
- **Midnight Offset**：JDN 整数对应当日 12:00，内部 value 以「JDN 整数 − 半天」对齐 00:00:00 到整点边界——构造时 `value = noon_value − HALF_DAY + 当日时间偏移`；提取时 `value + HALF_DAY_UNIT`（`core_design.md` §2.2）。
- `jdn_float` 属性仅供调试/科学对比（注释明确有精度损失）。

## 2. 构造（classmethod）

- `from_ymd_hms(year, month, day, hour=0, minute=0, second=0, microsecond=0)`：Fliegel & Van Flandern 正向算法，纯整数；`a=(14−month)//12; y=year+4800−a; m=month+12a−3`；`jdn = day + (153m+2)//5 + 365y + y//4 − y//100 + y//400 − 32045`。**不做参数校验**（月/日超界线性外推，与旧版一致）。支持任意天文纪年整数（含 0 与负数）。
- `from_ymd(y,m,d)` = 当日 00:00:00；`from_year(year)` = 该年 1 月 1 日。
- `from_iso_week(iso_year, week_number, weekday=1)`：以 ISO 年 1 月 4 日所在周周一为第 1 周起点；weekday Mon=1…Sun=7。

## 3. 转换与属性

- `to_gregorian()` → `(year, month, day, hour, minute, second, microsecond)`：value 加半天整除得 JDN 日、取模得当日微秒偏移；Fliegel 逆运算（L/N/I/J 链）解出年月日。**全程整数，往返误差 0 微秒**（测试锚定：round-trip、月末精度、午夜跨界）。
- `year/month/day/hour/minute/second/microsecond` 只读属性全部**实时计算**（历法标签是 View，单一事实来源）。
- `weekday`：ISO 语义 1=Mon…7=Sun；`(jdn_days % 7) + 1`（JDN 0 是周一中午）。
- `is_leap_year()`：格里高利规则，**负年取绝对值**（与旧版镜像一致）；year=0（1 BC）判闰。

## 4. 运算与比较

- `@total_ordering`；比较与哈希仅与同型。
- `__add__(int|float)`：按**天数**加（支持小数天，内部截断为微秒）；不支持加另一个 JDNTimestamp。
- `__sub__`：减 JDNTimestamp → 微秒差 `int`；减数值 → 按天数减。
- `__repr__`：`<JDNTimestamp: YYYY-MM-DD HH:MM:SS.ffffff>`。

## 5. 纪年约定（验收锚点）

- 天文纪年：**Year 0 = 1 BC，Year -1 = 2 BC**；跨公元边界连续（`test_year_zero_continuity`）。
- 用户可见格式化（`time_utils.format_jdn`）：`y<=0` → 显示年份 `1−y` + "BC" 后缀，否则 + "AD"；输出 `"{year}-{m:02d}-{d:02d}[ {HH:MM:SS}] {BC|AD}"`，午夜省略时分秒。
- 刻度标签（`render/painter.py`）：`y<=0` → `-(y-1)` + `" BC"` 后缀；正年份裸数字。
- **旧版年份迁移一律调 `history_year_to_jdn_year()`**（负年 +1），见 [03-time-bridges.md](03-time-bridges.md)。

## 6. 已知瑕疵

- ~~`__eq__`/`__lt__` 重复定义两遍~~ **已修复（2026-09-18，P2）**；
- ~~`is_leap_year` 的 `abs()` 与负年地板除语义不一致~~ **已修复（2026-09-18，P2）**：去掉 abs，BCE 闰年判定一致，补回归测试；
- 400 年周期闰年末日（1600/2000/2400-12-31）回读错误 **已修复（2026-09-18，P8）**：`days_to_years` 第 4 个百年分解 clamp（见 [98-known-issues.md](98-known-issues.md) §6 #37）。
