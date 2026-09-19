# HOW · TimelineView 交互行为

> 实现：`universal_history/render/timeline_view.py`。旧版对照：`history_legacy_spec/how/10-interactions.md`。

## 1. 信号

| 信号 | 参数 | 说明 |
| --- | --- | --- |
| `itemDoubleClicked` | EventIndex | 双击命中事件时发射（main_window 接此打开编辑器） |
| `contextMenuRequested` | QPoint（全局坐标）, Optional[EventIndex] | 右键；**精确到事件级**（旧版只到 Thread 级） |
| `itemClicked` | EventIndex | 单击命中事件时发射（T5-5/F4 起实发——press/release 位移 <6px 才算单击，拖拽不触发）；主窗口接此打开右侧 Event Details 面板 |

## 2. Workspace 绑定

- `set_workspace(workspace, source=None)`：断开旧 workspace 的 5 个信号（含 P5 新增的 `source_removed`）再连接新的；给 source 则立即建 Thread。
- `load_source(source, align="right")`：source 下全部 Event 转 EventIndex 快照建 Thread；未设 workspace 抛 RuntimeError。
- **槽函数**：增/改 → `refresh_source(event.source)`；删 → 按各 Thread 事件列表定位 uuid 所属 source，只刷新它（#24 已修复，不再全量刷新）；source_loaded → 刷新该 source；source_removed → 移除该 source 的所有 Thread。
- `refresh_source(source)`：重取快照灌入所有绑定该 source 的 Thread；空 source 是 no-op（测试锁定）。

## 3. Thread 管理

- `add_thread`：缺色自动调色板取色 → 建 ThreadLayout → **等份额插入**（该侧所有 Thread 均分 1/n）→ 重排。
- `set_thread_share(thread, share)`：目标取指定份额（钳 0~1），其余按原比例瓜分剩余（单值下限 0.001），整体归一化修漂移；**份额归一按侧独立**（测试锁定 sum==1 与几何比例）。
- `remove_thread` / `move_thread(thread, delta)`（同侧相邻交换）/ `switch_thread_side`（换侧后目标侧等份额重排）。
- `_arrange_threads()`：两侧预算来自 `thread_budgets()`；从 `AXIS_BREADTH/2` 起按 `budget × share` 依次切分；width≤0 的 Thread 跳过；**纵向模式交换左右侧逻辑符号**（保证 right 视觉在右，测试锁定）。

## 4. 视口适配

- `toggle_orientation()`：翻转 is_vertical → 重排 → 重绘。
- `fit_to_sources(sources=None, padding=0.05)`：center=时间中点，scale 使数据范围占视口 90%；纯点数据范围下限 1 年；scale 下限 1e-15。
- `show_events_at_default_scale(sources=None)`：解决「跨几千年但只有几个事件全挤在一起」——找**间距最小的相邻事件对**为中心开窗，窗口 = max(20 年, 最小间距×20)；单事件时 100px/年。主窗口加载文件后调用。

## 5. 交互

- **拖拽平移**：左键按下记点 + ClosedHand 光标；移动时按方向取屏幕 delta，`delta_us = delta_screen / scale`，`center_time -= delta_us`（内容跟随光标，**实时提交**——旧版是松开才提交）；布局对平移不变，拖拽中只重绘不重排；松开恢复光标。
- **双击**：命中 item → emit `itemDoubleClicked`。
- **右键**：emit `contextMenuRequested(globalPos, EventIndex|None)`。
- **滚轮**：
  - Ctrl+滚轮 = **锚定缩放**：factor 1.2（上）/ 1/1.2（下），scale 钳制 [1e-15, 1e-3] px/us；先记鼠标下逻辑 x 对应的时间，改 scale 后反解新 center_time 使该时间点仍在鼠标下（**与旧版同一不变式**；差异：旧版 48 档跳档，新版连续缩放）；
  - 普通滚轮 = 平移：每格（angleDelta 120 = 1 格）按**当前可见时间跨度的 10%** 平移，滚动速度随缩放自适应（2026-09-18 修复；旧版每格滚 1/4 主格）；
- **方向键平滑滚动（P7）**：`setFocusPolicy(StrongFocus)`；按住 Up/Down 按可见时间跨度的 5% 连续小步滚动，Left/Right 按整页（约一屏跨度）滚动；50ms QTimer 驱动，松开即停。
- **resize**：重排（Qt 自行触发重绘）。
- **可见性裁剪（P9）**：`paintEvent` 与 `_item_at_screen` 经 `painter.item_in_time_range` 按可见时间范围（含约 120px/scale 边距）裁剪，大数据集不再每帧 O(N) 全量绘制；**布局不裁剪**以保持轨道稳定。

## 6. 悬停实时提示（十字线 + 浮动信息框）

> 旧版出处：`viewer_ex.py` 的 `paint_real_time_tips` / `format_real_time_tip` / `on_pos_updated` / `HistoryIndexBar.get_tip_text`。
> 该功能是本项目反复次数最多的堵点（三次返工，见 §6.6 复盘），本节为定稿后的完整行为规格。

### 6.1 功能定义（用户可见行为）

光标在时间轴上移动时，**立即**（无停留延迟）出现：

1. **十字线**：过光标的水平 + 垂直两条通长虚线；
2. **浮动信息框**：跟随光标，内容为
   - 第 1 行（始终显示）：光标处的日期 `(yyyy/mm/dd)`，公元前为 `(xxxx BC/mm/dd)`；
   - 第 2 行（光标在事件上时追加）：事件摘要；单点事件附 ` : [日期]`；持续事件附 `(N/M)`（光标所在年第 N 年 / 共 M 年，天文纪年差值，钳入事件区间）与 ` : [起年 - 止年]`；
3. 左键拖动时整个 overlay 隐藏；光标离开控件即消失；可用 `set_real_time_tips_enabled()` 整体关闭。

### 6.2 与旧版逐项对照

| 旧版机制 | 新版实现 | 差异 |
| --- | --- | --- |
| 黑色实线十字线，全视口通长 | 深灰半透明**虚线**十字线 | 显示优化（弱化视觉噪音） |
| 浮动框 `(year/month/day)`，年份原始整数（公元前为负数） | `(yyyy/mm/dd)`，**era-aware**（`3000 BC/01/01`） | 显示优化 |
| 蓝底（36,169,225）矩形黑字，单行拼接 `tip \| item` | 深色圆角半透明框白字，**两行**（光标时间 / item 提示） | 显示优化 |
| item 提示：摘要 + 单点 `: [年份]` / 持续 `(N/M) : [起 - 止]` | **逐项保留**：摘要 + 单点 `: [完整日期]` / 持续 `(N/M) : [起 - 止]`（年份 era-aware） | 单点升级为完整日期（信息超集） |
| 拖动中隐藏（`__l_pressing`） | 拖动中隐藏（`_drag_last_pos` 非 None 时不绘） | 一致 |
| `enable_real_time_tips(bool)` 开关 | `set_real_time_tips_enabled(bool)` | 一致 |
| 出右边界左翻 | 出右/下边界左/上翻 | 增强（旧版只处理横向） |
| 鼠标移动 → 记状态 → repaint | 同（`mouseMoveEvent` → `_update_hover` → `update()`） | 一致 |
| 提示内容按移动时刻的状态计算 | **按 paint 时刻的当前视图状态计算**（`time_at_screen(_cursor_pos)`） | 增强：平移/缩放后光标不动文本也正确 |

### 6.3 状态机与绘制管线

- 状态：`_cursor_pos`（屏幕坐标，None=光标不在控件内）、`_hover_item`（EventIndex|None）、`_hover_year`（持续事件光标年）、`_tips_enabled`。
- 入口：`mouseMoveEvent` 非拖动分支 → `_update_hover(pos)`；`leaveEvent` → 清空全部状态。
- 绘制：`paintEvent` 末尾，`qp.resetTransform()` 后在**屏幕坐标**绘制（`painter.paint_hover_overlay`）——overlay 不属于逻辑坐标系，不参与锚点/缩放变换；横纵两种方向共用同一套绘制。
- 判定顺序（`_hover_overlay_lines()`）：`tips 关闭 → 无光标 → 拖动中` 任一为真则不绘。

### 6.4 与其他子系统的交互（易错点）

- **命中测试**复用 `_item_at_screen`（含可见性裁剪 +120px/scale 边距），保证「看得见才提示」；
- 持续事件进度年 = `time_at_screen(cursor).year`，钳入 `[since_year, until_year]`；注意 `until` 为起始日语义（1990–2010 的条最右 1px 仍在 2009 年，进度 `(20/21)`，`21/21` 只在 2010-01-01 边界点——测试锁定）；
- 平移/缩放后 `_cursor_pos` 不变但世界已变：因文本在 paint 时重算，无需额外处理（**这是相对旧版的实质增强**）；
- 拖动起点 `mousePressEvent` 只置 `_drag_last_pos`，overlay 由判定顺序自然隐藏，无需显式清除。

### 6.5 不变式（测试锁定，`tests/render_tests/test_hover_overlay.py`）

1. 光标在控件内且非拖动 → 第 1 行恒为光标处日期；
2. 悬停 item 才有第 2 行；单点含 ` : [` 日期、持续含 `(N/M)` 与 ` : [起 - 止]`；
3. 拖动中 / `set_real_time_tips_enabled(False)` / `leaveEvent` 后 → overlay 不绘；
4. 进度随光标在事件内移动跨年刷新；BCE 年份显示为 `xxxx BC`。

### 6.6 堵点复盘（三次返工的根因与教训）

| 迭代 | 方案 | 失败根因 |
| --- | --- | --- |
| v1 | widget `toolTip` 属性（被动弹出） | Qt 语义不匹配：被动 tooltip 要求光标**静止约 1 秒**，移动中永不出现；用户操作习惯是边移动边找事件，感知为「功能没有」。且这是实现时擅自「降级」（偏离旧版跟随式弹窗）未用户确认 |
| v2 | `QToolTip.showText` 主动跟随（#39 第一版修复） | 弹出逻辑对了，但仍是 Qt 原生弹窗：样式不可控、与旧版十字线机制不符；用户明确要自绘机制 |
| v3 | 自绘十字线 + 浮动框（**定稿**） | — |

教训（已固化进 `docs/testing.md` 与本节）：

1. **「降级」实现必须在规格中显式登记并取得用户确认**——v1 的 tooltip 降级埋在 11-editor.md 一句注记里，用户按旧版预期验收必然不通过；
2. **offscreen 测不出真实弹窗行为**——v1 的单测（文本内容断言）全绿但用户看不到东西；视觉类功能必须截图目验 + 真实平台冒烟；
3. **先对齐旧版功能清单再谈优化**——v2/v3 分歧本质是对「机制」还是「形式」有异议；逐项对照表（§6.2）就是为此而设，功能一项不能少，形式单列出清。

- 命中链：屏幕点 → `screen_to_logical` → 各 Thread `item_at_logical`（逆序，chip 优先）。
- `side_at_screen` 按轴中心线判左右（纵向比 x、横向比 y）；供右键菜单定 Add Thread 的侧。

## 7. 测试锁定（tests/render_tests/）

- 几何：默认 offset 0.5 两侧均分；逻辑原点映射 `(width/2, axis_center)`；
- 布局：单点卡片逻辑宽恒 120px；重叠分轨、不重叠复用轨；**单点不强制轨 0**；min_track_width 影响轨数、下限 1.0；
- 视图：切方向不崩溃；share 归一化；纵向模式 right Thread 仍在屏幕右侧；refresh_source("") no-op。
- 平移锚点（`test_pan_moves_items.py`）：拖动使事件条屏幕位置精确偏移；命中测试跟随；漂移超阈值重锚无跳变；
- 悬停 overlay（`test_hover_overlay.py`）：§6.5 不变式全锁；
- 交互注入（`test_interactions.py`）：拖动/单击判别、滚轮平移、Ctrl 锚定缩放、方向键滚动、双击/右键/快速录入信号。
