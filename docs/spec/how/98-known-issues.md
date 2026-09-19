# HOW 总结一 · 已知缺陷与 TODO

> 判定建议：**修复** / **排期**（功能未实现）/ **决策**（需用户拍板）。旧版缺陷的处置见 `history_legacy_spec/how/98-known-defects.md`。
> 2026-09-18 批量修复：#9–#12、#14、#15、#17、#18、#21–#31、#33 已完成并回归（105 测试全过）。
> 2026-09-18 P4 解析器解耦：#5、#7、#8 完成——`.his` 解析器移植进 `universal_history/parsing/`，不再对 sibling `History/` 做代码级依赖（125 测试全过）。
> 2026-09-18 P5–P10 批量收尾：#1–#4、#6、#13、#16、#19 已完成并回归（158 测试全过）；UI 补全 Help/About、Label Tag Editor、filter 预设、方向键平滑滚动；「世纪」区间解析改进（顺带修复闰年末日回读 bug，见 §6 #37）。
> 2026-09-18 F1–F12 全功能迁移收尾：#32、#34 清零（BCE 控件 F7、T5-3/T5-4 即 F5/F6）；刻度三级降级与时/分/秒层级（F8）、JSON Adapter（F9）、Agent API（F10）、Web 前端（F11）、PyInstaller 打包配置（F12）全部交付（216 测试全过）。

## 1. 数据与适配层

| # | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 1 | ~~`models/event.py:165-169`~~ | ~~`Workspace.clear()` 对每个旧 source 发 `source_loaded`——信号名与语义不符，无 `source_removed` 信号~~ | **已修复（2026-09-18，P5）**：新增 `source_removed` 信号，`clear()`/`remove_source()` 改发它；TimelineView `set_workspace` 已接入 |
| 2 | ~~`models/event.py:142-145`~~ | ~~`upsert()` 替换时双发信号（先 event_removed 再 event_updated），监听方需自行去抖~~ | **已修复（2026-09-18，P5）**：内部 `_remove_silent()`，替换只发单次 `event_updated` |
| 3 | ~~`models/event.py:133-138`~~ | ~~`add()` 允许重复 uuid；`remove`/`get_by_uuid` 只命中第一条~~ | **已修复（2026-09-18，P5）**：`add()` 重复 uuid 抛 `ValueError`；`load` 路径重复 uuid 跳过并告警；边界测试 `tests/test_workspace_boundaries.py` |
| 4 | ~~`models/event.py:96-97`~~ | ~~EventIndex 缺 `is_period_event`/`has_time`~~ | **已修复（2026-09-18，P5）**：两个谓词已补上 |
| 5 | ~~`adapters/his_adapter.py:19`、`chrono/history_time_adapter.py:22`~~ | ~~sys.path 注入同级 `History/` 仓库的硬依赖（`parents[3]` 路径假定）~~ | **已修复（2026-09-18，P4）**：解析器移植为 `universal_history/parsing/` 包（token_parser / label_tag / history_record / history_time / cn_num / text_utils）；sys.path 注入全部删除；`History/depot` 仅作数据目录按路径引用 |
| 6 | ~~`adapters/his_adapter.py`~~ | ~~保存无错误码、无冲突检测、无只读/Web source 拒绝；整文件覆写「最后写入者胜」~~ | **已修复（2026-09-18，P6）**：sha256 指纹冲突检测，`save_file(..., force=False)` 冲突时抛 `SaveConflictError`；编辑器与主窗口删除路径捕获后弹「Overwrite?」确认；只读/Web source 拒绝仍未实现（无此类 source 类型，登记为预留） |
| 7 | ~~`adapters/his_adapter.py`~~ | ~~加载失败与空文件不可区分（继承旧版静默吞错）~~ | **已修复（2026-09-18，P4）**：移植版 `HistoryRecordLoader.from_file` 读取失败抛 `OSError`，空文件正常返回空列表；UI 四处加载入口均有 try/except 弹窗（`editor.py` 补上了缺失的一处） |
| 8 | ~~`adapters/his_adapter.py:167`~~ | ~~`_label_line` 函数内 import~~ | **已修复（2026-09-18，P4）**：`LabelTagParser` 随包顶层 import |

## 2. 时间层

| # | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 9 | `chrono/jdn_timestamp.py` | ~~`__eq__`/`__lt__` 重复定义两遍（重构残留）~~ | **已修复（2026-09-18）**：删除前一组重复定义，保留返回 `NotImplemented` 的版本 |
| 10 | `chrono/jdn_timestamp.py` | ~~`is_leap_year` 对负年取 abs~~ | **已修复（2026-09-18）**：去掉 abs，Python 向下取模对负年判定一致；补 BCE 闰年测试 |
| 11 | `chrono/tick_stepper.py` | ~~周对齐是「简化」实现~~ | **已修复（2026-09-18）**：确认行为为 ISO 周一 00:00 对齐，清理误导注释，补周一吸附测试 |
| 12 | `chrono/tick_stepper.py` | ~~`is_visible()` 与 min/max_valid_year 无调用方；label_suffix 死代码~~ | **已修复（2026-09-18）**：label_suffix 死代码删除；`is_visible()` 已由 `painter._visible_ticks` 调用（±10000 年约束生效）；snap_to_grid 兜底保留并注释 |
| 13 | ~~`chrono/lunar_date_bridge.py:44-60`~~ | ~~`from_lunar` 忽略 `is_leap_month` 参数（闰月无法逆向构造）~~ | **已修复（2026-09-18，P10）**：闰月按 lunar_python 约定传负数月份构造，并回读校验「闰」字；不存在的闰月抛 `ValueError`；回归测试 `test_from_lunar_leap_month` |
| 14 | `chrono/python_time_bridge.py` | ~~naive datetime 静默假定 UTC~~ | **已修复（2026-09-18）**：发出 `UserWarning` |
| 15 | `chrono/time_utils.py` | ~~`format_jdn` 总带时分秒；类型签名未标 Optional~~ | **已修复（2026-09-18）**：午夜时刻省略时分秒、签名标 Optional；配套新增 ISO 快路径保证回读（见 §6 #35） |

## 3. 渲染层

| # | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 16 | ~~`render/painter.py`~~ | ~~**主/副刻度双层与淡入淡出未实现**（zoom_design.md 核心机制）；单层刻度在临界缩放可能跳变~~ | **已修复（2026-09-18，P9）**：`_tick_layers` 多层刻度（fine→coarse），密度驱动淡入淡出（50/100px 渐变，>300px 降为淡背景层）；回归测试 `tests/render_tests/test_tick_layers.py` |
| 17 | `render/painter.py` | ~~刻度选择未使用 TickLevel 的 ±10000 年可见范围~~ | **已修复（2026-09-18）**：`_visible_ticks` 按可见区中心年过滤 `is_visible()` |
| 18 | `render/painter.py` | ~~年标签 `step_count>=1000` 死分支，ka/Ma/Ga 名称未用上~~ | **已修复（2026-09-18）**：Deep Time 刻度使用 ka/Ma/Ga 幅度标签 |
| 19 | ~~`render/layout.py:151`、`timeline_view.py:439-449`~~ | ~~布局与绘制均全量处理所有事件，无可见性裁剪——大数据集 O(N) 每帧~~ | **部分修复（2026-09-18，P9）**：绘制与命中测试接入 `item_in_time_range` 可见性裁剪（含约 120px/scale 边距）；布局仍全量以维持轨道稳定（设计哲学保留） |
| 20 | `render/layout.py:19`、`geometry.py:148-153` 等 | POINT_EVENT_PIXEL_HEIGHT、pixel_to_logical_distance、itemClicked、side_at_screen 等定义未使用 | **排期（保留为预留接口）**：`side_at_screen` 有调用方（右键菜单定侧），`itemClicked` 已于 F4 实发（单击详情面板）；其余为已登记预留 |
| 21 | `render/timeline_view.py` | ~~拖拽中每次 mouseMove 都重排（平移不改布局，多余计算）~~ | **已修复（2026-09-18）**：平移只 `update()`，不再触发 `_arrange_threads()` |
| 22 | `render/timeline_view.py` | ~~普通滚轮把 angleDelta 直接当像素，滚动速度不随缩放自适应~~ | **已修复（2026-09-18）**：每格滚轮按可见时间跨度的 10% 平移 |
| 23 | `render/timeline_view.py` | ~~`fit_to_sources` 对全 None 时间的事件集会 ValueError；纯同一时间点数据集 fit 无效~~ | **已修复（2026-09-18）**：全 None 早退；同时间点数据集居中并使用最小一年区间 |
| 24 | `render/timeline_view.py` | ~~`_on_event_removed` 刷新所有已绑定 source（uuid 反查不到 source）~~ | **已修复（2026-09-18）**：按 thread 事件列表定位 uuid 所属 source，只刷新它 |
| 25 | `render/painter.py` | ~~paint_axis 结束时 transform 不恢复——隐式契约~~ | **已修复（2026-09-18）**：`QPainter.save/restore` |

## 4. UI 层

| # | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 26 | `ui/editor.py` | ~~Apply 重建 labels，UI 未暴露字段（author、自定义标签）丢失~~ | **已修复（2026-09-18）**：`_ui_to_event()` 改为合并 labels，显式清空的字段正常移除；回归测试 `test_apply_preserves_unexposed_labels` |
| 27 | `ui/editor.py` | ~~多处重复实例化 HisFileAdapter；若干未使用 import~~ | **已修复（2026-09-18）**：复用 `self._adapter`；清理 QApplication/QGridLayout/QGroupBox/QTabWidget |
| 28 | 全局 | ~~切换记录 / New / Cancel / 移除 Thread 均无未保存/无确认提示~~ | **已修复（2026-09-18）**：编辑器引入 dirty flag，未保存内容提示 保存/放弃/取消（切换记录 / New / Cancel / 关闭均覆盖）；移除 Thread 仅提示关闭（主窗口右键菜单与 ThreadManager 均已加确认） |
| 29 | `main_window.py` | ~~无退出确认（旧版有中文确认框）~~ | **已修复（2026-09-18）**：`closeEvent` 恢复退出确认；i18n 骨架已接入（`i18n.py` + `translations/zh_CN.json`，英文源文案） |
| 30 | `ui/thread_manager.py` | ~~调 TimelineView 私有方法 `_arrange_threads()`；share spin 后缀 " %" 与 0–1 值不匹配~~ | **已修复（2026-09-18）**：新增 `TimelineView.relayout()` 公开方法；去掉 " %" 后缀 |
| 31 | `ui/filter_dialog.py` | ~~单端时间范围退化为点区间；三态返回值可读性差~~ | **已修复（2026-09-18）**：开口区间（None 端无界），`Workspace.select` 支持 None 端；三态返回值改为抛 ValueError |
| 32 | ~~`ui/editor.py`~~ | ~~Calendar 限公元 1-9999 年；initial=None 时非当前时间~~ | **已完成（2026-09-18，F7）**：第二阶段落地——自绘 `AstroDatePickerDialog` 年/月/日控件支持天文纪年 BCE（0=公元前1年）与 1582 年格里高利历切换之外的全年表范围；编辑器「Out of Range」日期路由到该控件；第一阶段（自然语言文本 + Calendar 近期日期，ISO 快路径回读，见 §6 #35）保留 |
| 33 | `main_window.py` | ~~Ctrl+E 在无 source 时打开空编辑器~~ | **已修复（2026-09-18）**：无 source 时弹出引导（打开文件 / 新建文件 / 取消），选定后再进编辑器 |
| 34 | ~~`render/timeline_view.py` 等~~ | ~~位置感知新建（点击处时间预填）、非模态侧边编辑器、快速录入、单击展开详情~~ | **已全部完成（2026-09-18，F2–F6）**：位置感知新建、保存后视图跳转、单击展开详情面板（F2/F3/F4）；非模态侧边编辑器 `EventEditorDock`（F5，隐藏不清空未保存内容）、快速录入 `QuickEntryDialog`（F6，标题+时间一步成事件）均已实现（[15-timeline-centric-editing.md](15-timeline-centric-editing.md) T5 全绿） |

## 5. 文档偏差

| # | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 33 | `docs/core_design.md` | 个别占位残缺（"1 天 = 微秒"数字丢失、天文纪年公式为空） | 修复 |
| 34 | ~~`docs/zoom_design.md`~~ | ~~描述的三态淡入淡出与代码现状不符（未实现）~~ | **已消除（2026-09-18，P9）**：LOD 多层刻度已实现（见 §3 #16），文档与代码一致 |

## 6. 后续发现的缺陷

| # | 位置 | 问题 | 处置 |
| --- | --- | --- | --- |
| 35 | `chrono/time_utils.py` + 旧解析器 | 标准 ISO 格式「YYYY-MM-DD[ HH:MM:SS]」被旧自然语言解析器误解析（如 "2020-01-01" → 公元 1 年），导致 Calendar 写回的时间文本无法回读 | **已修复（2026-09-18）**：`parse_time_text` 增加 ISO 快路径（先于旧解析器），支持 BC/AD 后缀与负年；`format_jdn` 输出可正确回读 |
| 36 | `parsing/`（移植自 History `core.py`/`Utility/HistoryTime.py`/`to_arab.py`） | 解析器移植（P4）：行为与旧版逐字一致；顺带修复旧版缺陷 #1（补实现 `decimal_year_to_tick`）、#2（重复 label 合并）、#3（people/location/organization 断链方法）、#4（duplicate_from 深拷贝）、#5（无时间存 int 0）、#6（保序去重）、#7（加载失败抛异常）、#9（目录加载过滤 .his）。`History` 数据库类与 `.index` 管线不迁移。已知旧版怪癖原样保留：结尾无换行时闭合 `"""` 会漏进最后一个 tag（实际落盘行均有换行，不受影响）；「世纪→00」粗糙替换保留（**后被 #37 的区间解析取代**） | **已完成（2026-09-18）**：125 测试全过（含 20 个新解析器回归测试 `tests/test_parsing.py`）；锁定计数不变（example 6、China_CN 8 文件/248、World_CN 6/235） |
| 37 | `parsing/history_time.py`、`chrono/jdn_timestamp.py` | P8–P10 批次：①「世纪」区间解析改进——移除「世纪→00」粗糙替换，新增 `CENTURY_FINDER`/`_century_text_to_ticks`（支持「21世纪」「公元前3世纪」「七世纪」中文数字），钩进 `time_text_to_ticks`（**行为变化**，用户已拍板；example.his 不含「世纪」，锁定计数不变）；②修复旧版继承 bug——`days_to_years` 对 400 年周期第 4 个百年（含闰年 400）分解错误，导致 1600/2000/2400-12-31 回读成次年 1-1（`years_100` clamp 到 3）；③农历 `from_lunar` 闰月修复（见 §2 #13） | **已完成（2026-09-18，P8/P10）** |
| 38 | `render/layout.py` + `geometry.py` | **拖动时事件条不随轴移动**：ThreadLayout 把中心相对坐标烘进缓存 rect，而 P21（#21）让平移跳过重排——事件条停在旧屏幕位置，只靠可见性裁剪消失/显示 | **已修复（2026-09-19）**：锚点坐标系——缓存几何改为锚点相对，平移漂移并入 `transform()`，拖动成为纯 transform 平移；轴线与 Thread 背景改按 `center_logical_x()` 定位；漂移超 4 视口自动重锚（保护光栅数值范围）；回归测试 `tests/render_tests/test_pan_moves_items.py` |
| 39 | `render/timeline_view.py` `_update_hover` | **悬停提示用户感知为「没有」**：用 widget toolTip 属性被动弹出，光标须停留约 1 秒才显示，移动中永不出现（旧版是自绘十字线 + 跟随弹窗） | **已修复（2026-09-19，定稿）**：弃用 Qt toolTip/QToolTip 方案，恢复旧版自绘实时提示机制——`paintEvent` 末尾屏幕坐标绘制十字线 + 跟随浮动信息框（光标时间 `(y/mm/dd)` + item 摘要/日期/`(N/M)` 进度/区间），拖动隐藏、`set_real_time_tips_enabled` 可开关、出界翻转；显示样式优化为深色圆角；回归测试 `tests/render_tests/test_hover_overlay.py`，offscreen 截图目验通过 |
| 40 | `service/web/index.html` `layout()` | **Web 前端滚动到密集时段时 thread 块「跑到上面」**：轨道分配不设上限，左侧（轴上方）thread 元素随重叠数向上堆叠，溢出 band、越过轴线直达屏幕顶（约 12+ 重叠时），滚动经过密集簇后回落——用户报「左侧约 450 BC 开始」（桌面端无此问题，其 ThreadLayout 轨道数按 band 高度建满、多余者重叠落入末轨） | **已修复（2026-09-19）**：镜像桌面端语义——`maxTracks = floor((bandH + gap) / (ITEM_H + gap))`，超出者钳制到末轨重叠；同提交内 Web 单点事件对齐桌面棒棒糖设计（轴点 + 卡片内缘引线，取代语义含糊的卡片中线针），并补远缩放退化（卡片跨度 > 2 年时画时刻竖线 + 轴点）；node 逻辑断言（40 重叠事件全部在 band 内）+ 浏览器实测截图目验通过 |
| 41 | `render/layout.py` `arrange()` | **横纵布局轨道堆叠方向不一致**：轨道恒从 y0 排起，负侧（横布局轴上方 Thread）从远端开始堆叠，而纵布局左侧 Thread 因侧位互换恰好贴轴——用户要求统一「优先靠近轴」 | **已修复（2026-09-19）**：轨道从贴轴侧向外编号——负侧轨 0 在 y1 端、正侧轨 0 在 y0 端；末轨仍是最外侧（fallback 语义不变）；回归测试 `tests/render_tests/test_axis_strip.py::TestAxisOutwardTracks` |
| 42 | `render/painter.py` 轴标签 + `timeline_view.py` `paintEvent` | **纵布局轴标签被左侧 Thread 遮挡**：纵向标签在轴左侧（与旧版方位一致），与左侧 Thread 同侧，长标签伸进 Thread 带被事件卡压住 | **已修复（2026-09-19）**：标签绘制拆出 `paint_axis_labels`；纵向模式 `paint_axis(with_labels=False)` 先画几何，Thread 画完后标签置顶绘制并带轴带色底衬 chip；回归测试 `tests/render_tests/test_axis_strip.py::TestVerticalLabelsOnTop`，offscreen 截图目验通过 |
