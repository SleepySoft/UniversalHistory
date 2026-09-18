# HOW · 刻度层级与步进（TickStepper）

> 实现：`universal_history/chrono/tick_stepper.py`；刻度选择在 `render/painter.py:_visible_ticks`。设计规范：`docs/zoom_design.md`。**注意：zoom_design.md 的多层 LOD 淡入淡出尚未实现**，见文末。

## 1. 设计约束（zoom_design.md，已实现部分）

- 刻度必须吸附**标准日历单位**层级，禁止动态生成「1.5 天」式刻度；
- 刻度推进必须经日历运算（`to_gregorian` 分量），**禁止 `jdn + 固定微秒`**——闰年、大小月使每月/年长度不一；
- 非线性绘制：逐刻度独立映射（2 月的格子应比 1 月窄）；
- 密度驱动选层：以像素间距选择刻度层级。

## 2. TickLevel 与层级表

`TickLevel` 字段：`id`、`name`、`unit ∈ {Day, Month, Year}`、`step_count`、`avg_duration_us`（选层权重）、`min_valid_year`/`max_valid_year`（默认 ±inf）。

层级表（`TickStepper.LEVELS`，按步长从小到大）：

| 层级 | unit/step | 有效年份范围 |
| --- | --- | --- |
| 1 Day | Day/1 | ±10000 |
| 1 Week | Day/7（对齐周一） | ±10000 |
| 1 Month | Month/1 | ±10000 |
| 1 Quarter | Month/3 | ±10000 |
| 1/2/5 Years | Year/1,2,5 | 不限 |
| 10/20/50 Years | Year/10,20,50 | 不限 |
| 1 Century / 2 / 5 Centuries | Year/100,200,500 | 不限 |
| 1 Millennium | Year/1000 | 不限 |
| Deep Time | Year/10⁴…5×10⁹（1-2-5 循环，至 5 Ga） | 不限 |

常量：`ONE_DAY=86_400_000_000` 微秒；`ONE_YEAR=int(ONE_DAY*365.2425)`；`HIST_MIN=-10000`、`HIST_MAX=10000`（Day/Week/Month/Quarter 仅在有信史范围显示——**注意 `is_visible()` 目前无调用方**，范围约束已注册未生效）。

## 3. 吸附与推进

- `snap_to_grid(jdn, level)`：求 **≤ jdn 的最近整刻度**（floor）。先 `to_gregorian()` 再走日历逻辑：
  - Day/1 → 当日 00:00；Day/7（周）→ 回退到周一 00:00（注释自认「简化的周对齐」）；
  - Month/1 → 当月 1 日；Month/3 → 1/4/7/10 月；Month/6 → 1 月或 7 月；
  - Year → `y − (y % step_count)`；**依赖 Python 负数取模语义**使 BCE 刻度对齐天文年的 step 整数倍（-4 % 5 = 1 → 对齐到 -5）。
  - 未匹配的 (unit, step) 组合原样返回（静默兜底）。
- `get_next_tick(current, level)`：Day → 加 step_count 天；Month → 日历加月并跨年归一化；Year → `from_ymd_hms(y+step, 1, 1)`。**全部走日历运算**。

## 4. 渲染端层级选择（painter.py:_visible_ticks）

- 目标间距 **120px**：`target_us = 120 / scale`，在 LEVELS 中从小到大取第一个 `avg_duration_us >= target_us` 的层级；都不够大取最末级。
- 从 `snap_to_grid(start)` 起迭代收集 [start, end) 内刻度，安全上限 200 个。
- **当前只选单一层级、统一线长（±6px）——无主/副刻度之分**。

## 5. 与旧版刻度体系的关系

| 旧版（48 档 STEP_LIST） | 新版 | 说明 |
| --- | --- | --- |
| 主/副刻度六元组 offset 对 | 单层级表 | **回退**：副刻度体系未实现 |
| 年→月→周→日→时递进 | Day/Week/Month/Quarter/Year 层级 | 继承递进思想；注意新版最小层是「日」（时/分/秒层未注册） |
| 刻度推进 `offset_ad_second`（显式无 0 年修正） | `get_next_tick` 日历运算 | 优化：天文纪年天然连续 |
| MAIN_SCALE_MIN_PIXEL=50 | target_px=120 | 密度驱动思想继承，阈值与策略换代 |
| 上限 1000 万年 | 50 亿年（Deep Time） | 扩展 |
| BC 前缀（`BC 500`） | BC 后缀（`500 BC`） | 风格变化 |

## 6. 未实现（zoom_design.md 核心机制）

- 多层层叠绘制 + 透明度淡入淡出（三态：淡入/稳定/淡出）——缩放「无缝衔接」与临界闪烁的解决方案；
- 主/副刻度样式（旧版主 ±15px / 副 ±5px）；
- 三级显示降级（近代全显 / 史前仅年份 / 远古转 BP 格式，`core_design.md` §5.2）；
- 时/分/秒层级（旧版有 1 天主刻度 → 副 4/2/1 小时档）。
