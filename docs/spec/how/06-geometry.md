# HOW · 统一逻辑坐标系（geometry）

> 实现：`universal_history/render/geometry.py`。WHY（旧版未遂意图的完成态）见 [../why/02-architecture.md](../why/02-architecture.md)。

## 1. 核心思想

- **逻辑 X 永远是时间轴方向，逻辑 Y 垂直于时间轴**；逻辑原点在视口中心。
- **QTransform 只做平移 + 旋转，不含缩放**——因此逻辑坐标的单位**就是屏幕像素**，布局常量（卡片宽、边距、轨宽）可直接在逻辑坐标里加减，无需换算。这是理解全部布局代码的钥匙。
- 横纵切换 = 翻转 `is_vertical`，绘制代码只有一套。

## 2. 常量与默认值

- `AXIS_BREADTH = 30`：中央轴带保留像素（对应旧版 `__axis_space_w = 30`）。
- 默认视口 800×600（无 widget 时的虚拟尺寸）；`set_widget_size()` 为测试注入点。
- 默认 `is_vertical=False`（**横向**；注意旧版默认纵向）。
- `center_time` 默认 2000-01-01 12:00。
- 默认 scale = 200 px/年（px/微秒换算）。
- `axis_offset = 0.5`（轴在横向空间的比例位置：0=贴一端、0.5=居中、1=贴另一端；继承旧版 `__axis_align_offset` 语义）。

## 3. 时间 ↔ 坐标（锚点坐标系，2026-09-19 起）

- **布局锚点 `_anchor_time`**：ThreadLayout 缓存的事件条坐标是**锚点相对**的，而非视野中心相对——`time_to_logical_x(ts) = (ts.value − anchor.value) × scale`；
- **平移 = 纯 transform 平移**：拖动只改 `center_time`，锚点不动；`transform()` 内部附加 `(anchor − center) × scale` 的 X 向平移，缓存几何随轴一起移动，无需重排（known-issues §6 #38 的修复）；
- `center_logical_x()` = 视野中心在锚点坐标系中的 X（轴线、Thread 背景按它定位，保证平移时始终铺满视口）；
- **重锚时机**：每次 `_arrange_threads()`（缩放、resize、数据变化）把锚点同步为当前中心；纯平移漂移超过 4 个视口长度时由 `_set_center_time` 触发重锚（防止缓存坐标超出光栅引擎数值范围）；
- `logical_x_to_time` 反算（`int()` 截断，锚点基准）；
- `visible_time_range()` = `center ± half_length/scale`（中心基准，不随锚点变）；
- `pixel_to_logical_distance` / `logical_to_pixel_distance`：距离换算（当前无调用方，预留接口）。

## 4. 轴位置与两侧预算

- `axis_screen_center()` = `AXIS_BREADTH/2 + axis_offset × (breadth − AXIS_BREADTH)`——轴中心永远在轴带内滑动，不压 Thread 区。
- `thread_budgets()` → `(left_budget, right_budget)`：轴带两侧剩余像素，轴贴边时一侧可为 0（`max(0, …)` 钳制）。测试锁定：默认两侧相等、总和 = breadth−30、offset=0/1 时一侧全零。

## 5. 横纵切换（transform()）

- **横向**：`translate(width/2, axis_center)`——逻辑原点落在屏幕横向中点、轴心纵坐标。
- **纵向**：`translate(axis_center, height/2)` 后 `rotate(90)`——逻辑 X 旋为屏幕纵向，逻辑 +Y 旋后为屏幕 **−X**（左）。因此纵向模式下右侧 Thread 须用**负** Y 区、左侧用正 Y 区，保证「right 视觉上仍在右」（`timeline_view.py:409-418`；测试锁定）。
- 平移漂移平移量 `dx = (anchor − center) × scale`：横向并入首位移，纵向在 `rotate(90)` 后再 `translate(dx, 0)`（先作用于逻辑坐标再旋转）。
- `logical_to_screen` / `screen_to_logical`：正/逆变换；不可逆时返回原点（防御分支）。

## 6. 与旧版对照

旧版 `AxisMetrics`（transverse/longitudinal）+ 横纵两套绘制函数 + 镜像特判，并留 TODO「Can we just rotate the QPaint axis?」。新版即该 TODO 的完成态：一套绘制、旋转交给 QTransform、无镜像特判散布。

## 7. 堵点复盘：拖动时事件条不随轴移动（#38）

> 该缺陷与 #39（悬停提示）并列为本项目交互层两大堵点。症状：拖动时间轴时刻度正常移动，事件条却钉在原地不动，只靠可见性裁剪逐个消失/显示。

### 7.1 根因（两个正确决策的恶性组合）

1. **缓存坐标的基准选择**：`ThreadLayout.arrange()` 把事件条矩形缓存为**视野中心相对**的逻辑坐标（`time_to_logical_x` 以 `center_time` 为基准）——这对「排列时刻」是自然的；
2. **P21 性能优化**（#21）：平移不改轨道分配，故拖拽中跳过重排只 `update()`——单看也正确。

组合后：拖动只改 `center_time`，刻度轴每帧按新中心重算（正常移动），而事件条仍按旧中心烘焙的坐标绘制（钉死），裁剪又按新视野执行（逐个消失/显示）。**单点决策都成立，系统级行为错误**——这是典型的接口语义漂移：缓存坐标隐含的「中心相对」契约没有任何字段或文档承载。

### 7.2 修复设计（锚点坐标系）

- 引入**显式布局锚点** `_anchor_time`：缓存几何一律锚点相对；锚点在每次 `_arrange_threads()` 时同步为当前中心；
- `transform()` 内部叠加平移漂移 `(anchor − center) × scale`——拖动成为**纯变换平移**，缓存几何随轴移动且零重排（P21 优化保留）；
- 轴线与 Thread 背景等「应铺满当前视口」的元素改按 `center_logical_x()` 定位（否则它们会跟着锚点漂走）；
- 漂移超 4 个视口长度自动重锚（`_set_center_time`），防止缓存坐标无限增大触及光栅引擎数值范围；
- 缩放/resize/数据变化本来就会重排 → 锚点自动重同步，无额外处理。

### 7.3 备选方案与取舍

| 方案 | 取舍 |
| --- | --- |
| 拖动时每次重排（撤销 P21） | 简单但 O(N)/帧，大数据集拖拽掉帧——否决 |
| 逻辑坐标改为绝对时间（`ts.value × scale`） | 拖动天然正确，但坐标值达 1e9 量级，超出 Qt 光栅内部定点数范围——否决 |
| 锚点 + 漂移平移（**采用**） | 数值始终小、拖动零重排、代价是多一个锚点生命周期（重排即同步 + 漂移阈值重锚） |

### 7.4 不变式（测试锁定，`test_pan_moves_items.py`）

1. 平移 Δpx 后任一 item 的 `screen_rect` 精确偏移 Δpx（±1px）；
2. 命中测试（`_item_at_screen`）与 `time_at_screen` 在平移后仍一致；
3. 漂移超阈值重锚后视图无跳变（`center_logical_x` 归零，屏幕位置连续）；
4. 缩放锚点不变式（光标下时间点不动）由 `test_interactions.py` 锁定。

### 7.5 教训

1. **缓存坐标的基准是契约，必须显式化**——「相对谁」要落成字段与文档（本节），不能只在调用点隐式成立；
2. **性能优化要回归交互不变式**——P21 的单测只验证了「不再调用重排」，没有验证「内容跟随光标」这条用户可感知不变式；交互回归测试（拖动后位置断言）当时缺位；
3. 修复后应立即补**截图目验**（平移前后两帧对比），数值断言证明不了「看起来对」。
