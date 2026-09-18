# HOW · 交互规格（新版为准项与 Legacy 参照项）

> 本文件是交互行为的**权威归属表**：每条用户可感知行为标明「以新版实现为准」还是「新版未明确、以 Legacy 规格为参照」。
> Legacy 参照路径 = `HistoryMigration/docs/history_legacy_spec/`。

## 1. 以新版为准（已实现，行为以上述 how/ 分篇为准）

| 行为 | 新版出处 | 与旧版关系 |
| --- | --- | --- |
| Ctrl+滚轮锚定缩放（连续 ×1.2） | [09-timeline-view.md](09-timeline-view.md) §5 | 继承不变式，离散跳档→连续 |
| 滚轮/拖拽平移 | 同上 | 继承；拖拽实时提交（旧版松开才提交） |
| 刻度层级选择（120px 密度阈值） | [02-tick-stepper.md](02-tick-stepper.md) §4 | 继承密度驱动思想 |
| 刻度吸附真实历日、非线性映射 | [02-tick-stepper.md](02-tick-stepper.md) §3 | 继承（`offset_ad_second` → `get_next_tick`） |
| 横/纵切换 Ctrl+T | [06-geometry.md](06-geometry.md) §5 | 旧版坏损，新版实现 |
| 单点/持续统一轨道分配、末轨兜底 | [07-layout.md](07-layout.md) | 优化（§8.5 决策） |
| 事件 chip/bar 样式、省略号截断、远端 marker | [08-painting.md](08-painting.md) | 优化（§8.6 决策） |
| 悬停 Qt Tooltip | [09-timeline-view.md](09-timeline-view.md) §6 | 差异（放弃自绘十字线方案） |
| 右键菜单（含事件级 Edit/Delete） | [10-main-window.md](10-main-window.md) §3 | 优化（精确到事件） |
| Thread share/换侧/排序 | [12-dialogs.md](12-dialogs.md) §2 | 优化（旧版宽度不可调） |
| 编辑器校验/Lock/落盘/删除确认 | [11-editor.md](11-editor.md) | 继承 + 定点修复 |
| 过滤 → `__filter__` Thread | [12-dialogs.md](12-dialogs.md) §1 | 旧版未遂，新版实现 |
| 自然语言时间解析 | [03-time-bridges.md](03-time-bridges.md) §3 | **逐字继承**（复用旧解析器） |
| 启动自动加载示例 | [10-main-window.md](10-main-window.md) §1 | 新增 |

## 2. 新版未明确、以 Legacy 规格为参照的行为细节

以下行为新版未实现或未定义；若要做，**默认参照 Legacy 规格**（除非有更新决策）：

| 行为 | Legacy 参照 | 备注 |
| --- | --- | --- |
| 主/副刻度双层体系（主 ±15px / 副 ±5px、副刻度不足半步省略规则） | `how/08-timeline-rendering.md` §4 | 新版现为单层；实现时应结合 `zoom_design.md` 的淡入淡出方案 |
| 时/分/秒级刻度（1 天 → 副 4/2/1 小时） | 同上 | 新版最小层级为「日」 |
| 悬停十字准线 + 持续事件「第N年/共M年」进度 | `how/08-timeline-rendering.md` §8 | 旧版有；新版 Tooltip 无进度 |
| 刻度像素精确吸附（`__optimise_pixel`） | `how/08-timeline-rendering.md` §3 | 新版直接线性反算 |
| 方向键平滑滚动 | `how/10-interactions.md`（旧版坏损） | 若实现应修复而非复刻 |
| 时间范围/缩放限制 API | `how/08-timeline-rendering.md` §3 | 未移植 |
| 单击展开详情、密集聚簇 | `migration_analysis.md` §8.6 | 预留增强 |
| depot 浏览器（文件重命名等） | `how/11-editor.md` §10 | 未移植 |
| filter 预设存盘（.hisfilter） | `how/06-filter.md` | 路线图；若实现统一 utf-8 |
| 退出确认框 | `how/12-main-window.md` §4 | 旧版唯一中文 UI；新版无——需决策是否恢复（英文文案） |
| 未保存修改提示 | `how/11-editor.md` | 两版均无——待修复项而非参照项 |

## 3. 明确不复刻的旧版行为

- 编辑后不刷新（结构性修复，永不复刻）；
- .index 文件管线（断链）；
- Auto Detect 占位提示框（由真实 Agent 能力兑现）；
- 每次保存弹成功框；
- 无确认删除；
- Apply 丢失未暴露字段（**当前仍存在，列为待修复而非保留**，见 [98-known-issues.md](98-known-issues.md)）。
