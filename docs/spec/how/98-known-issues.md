# HOW 总结一 · 已知缺陷与 TODO

> 判定建议：**修复** / **排期**（功能未实现）/ **决策**（需用户拍板）。旧版缺陷的处置见 `history_legacy_spec/how/98-known-defects.md`。

## 1. 数据与适配层

| # | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 1 | `models/event.py:165-169` | `Workspace.clear()` 对每个旧 source 发 `source_loaded`——信号名与语义不符，无 `source_removed` 信号 | 修复 |
| 2 | `models/event.py:142-145` | `upsert()` 替换时双发信号（先 event_removed 再 event_updated），监听方需自行去抖 | 修复 |
| 3 | `models/event.py:133-138` | `add()` 允许重复 uuid；`remove`/`get_by_uuid` 只命中第一条 | 修复 + 补边界测试（PROJECT_STATUS 待办） |
| 4 | `models/event.py:96-97` | EventIndex 缺 `is_period_event`/`has_time` | 修复 |
| 5 | `adapters/his_adapter.py:19`、`chrono/history_time_adapter.py:22` | sys.path 注入同级 `History/` 仓库的硬依赖（`parents[3]` 路径假定） | 排期（解析器边界解耦，PROJECT_STATUS 待办 1） |
| 6 | `adapters/his_adapter.py` | 保存无错误码、无冲突检测、无只读/Web source 拒绝；整文件覆写「最后写入者胜」 | 排期（保存冲突，PROJECT_STATUS 待办 2） |
| 7 | `adapters/his_adapter.py` | 加载失败与空文件不可区分（继承旧版静默吞错） | 修复 |
| 8 | `adapters/his_adapter.py:167` | `_label_line` 函数内 import | 修复（随解析器解耦一并处理） |

## 2. 时间层

| # | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 9 | `chrono/jdn_timestamp.py:33-39,238-246` | `__eq__`/`__lt__` 重复定义两遍（重构残留） | 修复 |
| 10 | `chrono/jdn_timestamp.py:227-232` | `is_leap_year` 对负年取 abs，与 Fliegel 正向算法的负年地板除语义不完全一致 | 修复（统一 BCE 闰年语义） |
| 11 | `chrono/tick_stepper.py:76` | 周对齐是「简化」实现 | 修复 |
| 12 | `chrono/tick_stepper.py:29-30,108,190-197` | `is_visible()` 与 min/max_valid_year 无调用方；snap_to_grid 静默兜底；label_suffix 死代码 | 修复 |
| 13 | `chrono/lunar_date_bridge.py:44-60` | `from_lunar` 忽略 `is_leap_month` 参数（闰月无法逆向构造） | 排期 |
| 14 | `chrono/python_time_bridge.py:31` | naive datetime 静默假定 UTC（注释说可抛警告，未实现） | 修复 |
| 15 | `chrono/time_utils.py:41-52` | `format_jdn` 总带时分秒；类型签名未标 Optional | 修复 |

## 3. 渲染层

| # | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 16 | `render/painter.py` | **主/副刻度双层与淡入淡出未实现**（zoom_design.md 核心机制）；单层刻度在临界缩放可能跳变 | 排期（结合 Legacy `how/08` 的主副刻度规则） |
| 17 | `render/painter.py:64-68` | 刻度选择未使用 TickLevel 的 ±10000 年可见范围 | 修复 |
| 18 | `render/painter.py:33-36` | 年标签 `step_count>=1000` 死分支，ka/Ma/Ga 名称未用上 | 修复 |
| 19 | `render/layout.py:151`、`timeline_view.py:439-449` | 布局与绘制均全量处理所有事件，无可见性裁剪——大数据集 O(N) 每帧 | 排期（性能优化；注意保持布局稳定性哲学） |
| 20 | `render/layout.py:19`、`geometry.py:148-153` 等 | POINT_EVENT_PIXEL_HEIGHT、pixel_to_logical_distance、itemClicked、side_at_screen 等定义未使用 | 清理或排期 |
| 21 | `render/timeline_view.py:477` | 拖拽中每次 mouseMove 都重排（平移不改布局，多余计算） | 修复 |
| 22 | `render/timeline_view.py:516-517` | 普通滚轮把 angleDelta 直接当像素，滚动速度不随缩放自适应 | 修复 |
| 23 | `render/timeline_view.py:301-330` | `fit_to_sources` 对全 None 时间的事件集会 ValueError；纯同一时间点数据集 fit 无效 | 修复 |
| 24 | `render/timeline_view.py:592-596` | `_on_event_removed` 刷新所有已绑定 source（uuid 反查不到 source） | 修复（建立 uuid→source 索引或让信号带 source） |
| 25 | `render/painter.py:84-129` | paint_axis 结束时 transform 不恢复——隐式契约 | 修复（QPainter.save/restore） |

## 4. UI 层

| # | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 26 | `ui/editor.py:387-397` | Apply 重建 labels，**UI 未暴露字段（author、自定义标签）丢失**——继承旧版缺陷 #33 | 修复（labels 合并而非重建） |
| 27 | `ui/editor.py:77,224,235` | 多处重复实例化 HisFileAdapter；若干未使用 import | 修复 |
| 28 | 全局 | 切换记录 / New / Cancel / 移除 Thread 均无未保存/无确认提示（部分继承旧版） | 决策（逐项定哪些要确认） |
| 29 | `main_window.py` | 无退出确认（旧版有中文确认框） | 决策（恢复则用英文文案） |
| 30 | `ui/thread_manager.py:190` | 调 TimelineView 私有方法 `_arrange_threads()`；share spin 后缀 " %" 与 0–1 值不匹配 | 修复 |
| 31 | `ui/filter_dialog.py:129-132` | 单端时间范围退化为点区间；三态返回值可读性差 | 修复 |
| 32 | `ui/editor.py:295-313` | Calendar 限公元 1-9999 年；initial=None 时非当前时间 | 决策（BCE 录入的替代交互） |
| 33 | `main_window.py:157-160` | Ctrl+E 在无 source 时打开空编辑器（"No source"，Apply 才被拦截）——应改为引导绑定/选文件 | 修复（[15-timeline-centric-editing.md](15-timeline-centric-editing.md) T4） |
| 34 | `render/timeline_view.py` 等 | 位置感知新建（点击处时间预填）、非模态侧边编辑器、快速录入、单击展开详情 | 排期（T5 增强，[15-timeline-centric-editing.md](15-timeline-centric-editing.md)） |

## 5. 文档偏差

| # | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 33 | `docs/core_design.md` | 个别占位残缺（"1 天 = 微秒"数字丢失、天文纪年公式为空） | 修复 |
| 34 | `docs/zoom_design.md` | 描述的三态淡入淡出与代码现状不符（未实现） | 保持为设计目标，本规格 [02-tick-stepper.md](02-tick-stepper.md) §6 已标注 |
