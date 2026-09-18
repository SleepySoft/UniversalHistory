# HOW · 时间桥接（datetime / 农历 / 旧 TICK）

> 实现：`chrono/python_time_bridge.py`、`chrono/lunar_date_bridge.py`、`chrono/history_time_adapter.py`、`chrono/time_utils.py`。

## 1. PythonTimeBridge（datetime / Unix）

- 常量：`UNIX_EPOCH_JDN_DAYS = 2440587.5`（1970-01-01 00:00 UTC）。
- `to_datetime(jdn, tz=timezone.utc)`：转 UTC datetime 再 `astimezone(tz)`；**year<1 或 >9999 抛 `OverflowError`**。
- `from_datetime(dt)`：强制归一 UTC；naive datetime **假定 UTC**（注释承认是折衷）。
- `to_unix_timestamp(jdn)` → float 秒；`from_unix_timestamp(float)` 经 `int(timestamp*1e6)` 转微秒。
- 锚点测试：unix 0 ↔ 1970-01-01 00:00；2023-01-01 → 1672531200。

## 2. LunarDateBridge（农历/干支）

- 依赖 `lunar_python`（requirements.txt）。
- `to_lunar(jdn)` → `LunarResult`：链路 **JDN → Gregorian → Solar.fromYmdHms → getLunar**（必须经 Solar 中间层保精度）；字段含 year/month/day、`is_leap`（由 `getMonthInChinese()` 是否含「闰」判定）、`year_cn`（干支）、`month_cn`、`day_cn`、`animal`（生肖）；超范围异常包装为 `ValueError("农历转换失败 ...")`。
- `from_lunar(year, month, day, h, m, s, is_leap_month=False)`：农历 → Lunar → Solar → JDN。**已知未完成：`is_leap_month` 参数被忽略**（闰月无法逆向构造）。
- lunar_python 有效年份范围远小于 JDN 全域——史前/深时无农历属预期。

## 3. history_time_adapter（旧 TICK → JDN，单向）

模块 docstring 定位：旧 TICK 仅在自然语言解析时产生、**无数据以 TICK 持久化**；桥接是务实的——保留旧解析器产出的用户可见历法日期，不求严格天文等价（用户裁决 §8.1）。

- **启动副作用**：把仓库根 `History/` 插入 `sys.path` 以 import `Utility.HistoryTime`（对同级 submodule 的硬依赖，解耦待办）。
- `history_year_to_jdn_year(history_year)`：**无 0 年 → 天文纪年**映射——负年 +1（-1 → 0 = 1 BC），非负不变。AGENTS.md 强制：迁移旧年份一律调此函数。
- `history_tick_to_jdn(tick)`：`HistoryTime.tick_to_date_time_data` 拆日历分量 → 年份过上面的映射 → `from_ymd_hms` 重建。**走日历分量而非线性换算**，规避两系统零点/BCE 镜像差异。
- `history_record_time_range(record)` → `(since, until)`：用原始 `time` 标签区分「无时间」与「真实的 AD 1」（TICK 0 歧义）；解析失败（since==until==0 且无 time 标签）返回 `(None, None)`。
- `history_record_time_text_to_jdn_list(time_text)`：直接调旧管线 `HistoryTime.time_text_to_ticks` 逐 tick 转换——**解析行为逐字继承旧版**（容错规则全集见 `history_legacy_spec/how/02-natural-language-time-parsing.md`，本规格不重复登记，以彼为准）。

## 4. time_utils（UI 面向，chrono 层唯一依赖 PyQt6 的文件）

- `parse_time_text(text)` → `(since, until, display_strings)`：空文本或解析异常返回 `(None, None, [])`（吞掉一切异常）；多时间点取 min/max。
- `format_jdn(ts)`：用户可见格式 `"{year}-{m:02d}-{d:02d} {HH:MM:SS} {BC|AD}"`；**总是带时分秒**（旧版 format_tick 的 show_date/show_time 开关不再存在）；`None` 返回空串。
- `jdn_to_qdatetime(ts)`：datetime 范围内才转换，超范围返回 `None`——对应旧版「BCE 时间无法进日期拾取器」的行为通道（Calendar 按钮的 Out of Range 提示）。
- `qdatetime_to_jdn(qdt)`：naive 视为 UTC。

## 5. 行为对照要点

- 旧版 datetime 桥超范围时 print 并返回 None；新版抛 OverflowError、由调用方（time_utils / editor）捕获回退——**用户可见回退行为不变**。
- 旧版 `format_tick` 默认只出年份绝对值、无 BC 标记（缺陷 #47）；新版所有用户可见输出都带 BC/AD 后缀。
- 旧版 `[]` 方括号保护壳约定仍在**解析侧**生效（旧管线原样复用），但格式化层不再产生 `[]`。
