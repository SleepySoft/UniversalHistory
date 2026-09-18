# WHY · 为什么从 TICK 到 JDNTimestamp

> 新设计规范：`docs/core_design.md`；旧版时间系统：`history_legacy_spec/how/01-time-system.md`；哲学延续性：`history_legacy_spec/why/02-time-philosophy.md`。

## 旧版 TICK 的局限

旧版 `HistoryTime` 的 TICK（整数秒，公元元年元旦 = 0）已经是正确的方向（「真实刻度 vs 历法标签」二分），但有四个地基性问题：

1. **自定义零点**：公元 1-01-01 为零点是非标准约定，无法与任何天文/历法工具互操作；
2. **无 0 年**：`year=-1` 即 1 BC，跨公元边界的加减需要显式 ±1 修正（`offset_ad_second` 的跨零分支是旧版最易错的代码）；
3. **BCE 月日镜像规则**：「公元前一日 = 公元前 1 年 12 月 31 日」是自定义映射，与外推格里高利历在远古时期有偏差；
4. **秒级精度 + 浮点混入**：解析失败时 since/until 写 0.0（float），类型不纯。

## 新设计（core_design.md §1-2）

- **内部表示**：距 JDN 0 的微秒总数（Python int，无限精度）；JDN 0 = 天文年 -4712-11-24 12:00（外推格里高利历）。value 以「当日 12:00 为基准再减半天」，使 00:00:00 落在整点边界（Midnight Offset）。
- **天文纪年**：Year 0 = 1 BC，Year -1 = 2 BC——跨公元边界数学连续，不再需要跨零修正分支。
- **外推格里高利历**：400 年闰法向过去无限外推；「系统是数学标尺，不是历史模拟器」。
- **算法选型**：Fliegel & Van Flandern (1968) 纯整数算法；+4800 偏移保证负年单调连续。
- **历法标签实时计算**：year/month/day/weekday 等全部是 View 属性，不占存储（单一事实来源）。

## 与旧版的关系：继承什么，修正什么

| 旧版行为 | 处置 | 说明 |
| --- | --- | --- |
| 「真实刻度 vs 历法标签」二分 | **继承** | JDNTimestamp 是同一哲学的严谨化 |
| 自然语言解析管线（容错优先） | **继承** | 适配层原样复用旧解析器，行为逐字不变（见 [../how/03-time-bridges.md](../how/03-time-bridges.md)） |
| BCE 闰年取绝对值 | **继承** | `is_leap_year` 对负年取绝对值 |
| 无 0 年 | **修正** | 天文纪年；`history_year_to_jdn_year()` 单向桥接（负年 +1） |
| BCE 月日镜像 | **修正** | 载入时经日历分量转换，把旧镜像结果当「用户可见日期」保留；进入新系统后按连续历法处理 |
| 秒精度 | **优化** | 微秒定点 |
| 参数不校验（超界线性外推） | **继承** | `from_ymd_hms` 同样不外校验 |
| datetime 桥超范围静默 print | **优化** | 抛 `OverflowError`，调用方捕获后回退；用户可见回退行为不变 |

## 用户的明确裁决（migration_analysis.md §8.1）

- 没有数据以 TICK 持久化——**不需要双向精确转换器**；
- 唯一要保留的是「自然语言时间文本 → 时间」的解析能力，只发生在载入阶段；
- 远古/史前时间与外推格里高利历的细微偏差**可接受**，不作为验收不符项。

## 新增能力

- **农历/干支桥接**（`LunarDateBridge`）：旧版只有注释掉的 `tick_to_cn_date_text`；新版经 JDN→Solar→Lunar 链路支持干支年、生肖、中文月日（闰月反查未实现，见 [../how/98-known-issues.md](../how/98-known-issues.md)）。
- **Python datetime / Unix 时间戳互转**：为 Agent API 与 Web 前端的数据交换做准备。
