# HOW · TimelineView 交互行为

> 实现：`universal_history/render/timeline_view.py`。旧版对照：`history_legacy_spec/how/10-interactions.md`。

## 1. 信号

| 信号 | 参数 | 说明 |
| --- | --- | --- |
| `itemDoubleClicked` | EventIndex | 双击命中事件时发射（main_window 接此打开编辑器） |
| `contextMenuRequested` | QPoint（全局坐标）, Optional[EventIndex] | 右键；**精确到事件级**（旧版只到 Thread 级） |
| `itemClicked` | EventIndex | **已定义但从未 emit**（单击展开详情未实现，§8.6 预留） |

## 2. Workspace 绑定

- `set_workspace(workspace, source=None)`：断开旧 workspace 的 4 个信号再连接新的；给 source 则立即建 Thread。
- `load_source(source, align="right")`：source 下全部 Event 转 EventIndex 快照建 Thread；未设 workspace 抛 RuntimeError。
- **槽函数**：增/改 → `refresh_source(event.source)`；删 → 因 uuid 反查不到 source，**刷新所有已绑定 source**（正确但粗暴）；source_loaded → 刷新该 source。
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

- **拖拽平移**：左键按下记点 + ClosedHand 光标；移动时按方向取屏幕 delta，`delta_us = delta_screen / scale`，`center_time -= delta_us`（内容跟随光标，**实时提交**——旧版是松开才提交）；松开恢复光标。
- **双击**：命中 item → emit `itemDoubleClicked`。
- **右键**：emit `contextMenuRequested(globalPos, EventIndex|None)`。
- **滚轮**：
  - Ctrl+滚轮 = **锚定缩放**：factor 1.2（上）/ 1/1.2（下），scale 钳制 [1e-15, 1e-3] px/us；先记鼠标下逻辑 x 对应的时间，改 scale 后反解新 center_time 使该时间点仍在鼠标下（**与旧版同一不变式**；差异：旧版 48 档跳档，新版连续缩放）；
  - 普通滚轮 = 平移：`delta_us = angleDelta.y / scale`——angleDelta（1/8 度单位，典型每格 120）直接当像素用，即每格约 120 逻辑像素（旧版每格滚 1/4 主格；新版滚动速度不随缩放自适应，已知瑕疵）。
- **resize**：重排（Qt 自行触发重绘）。

## 6. 悬停与命中

- `_update_hover`：命中新 item → 记 `_hover_item`、setToolTip、重绘；离开清空。**Qt 原生 Tooltip**（取代旧版自绘十字线 + 蓝色提示框；旧版持续事件的「第N年/共M年」进度提示**未移植**）。
- `_tooltip_text`：`"{year} {era}-MM-DD"`（era 为 BC/AD 后缀）；单点 → `时间\n摘要`；持续 → `起 ~ 止\n摘要`。
- 命中链：屏幕点 → `screen_to_logical` → 各 Thread `item_at_logical`（逆序，chip 优先）。
- `side_at_screen` 按轴中心线判左右（纵向比 x、横向比 y）；供右键菜单定 Add Thread 的侧。

## 7. 测试锁定（tests/render_tests/）

- 几何：默认 offset 0.5 两侧均分；逻辑原点映射 `(width/2, axis_center)`；
- 布局：单点卡片逻辑宽恒 120px；重叠分轨、不重叠复用轨；**单点不强制轨 0**；min_track_width 影响轨数、下限 1.0；
- 视图：切方向不崩溃；share 归一化；纵向模式 right Thread 仍在屏幕右侧；refresh_source("") no-op。
