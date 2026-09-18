# WHAT · 时间轴浏览与多线索

> HOW 细节：[../how/06-geometry.md](../how/06-geometry.md) ~ [../how/09-timeline-view.md](../how/09-timeline-view.md)。与旧版的逐项差异见 [../why/99-summary.md](../why/99-summary.md)。

## 时间轴浏览

- **平移**：左键拖拽（内容实时跟随光标）；滚轮（每格约 120 像素）。
- **缩放**：Ctrl+滚轮，连续缩放（×1.2 / ÷1.2），**鼠标指向的时间点保持不动**（锚定缩放）。
- **刻度**：按缩放密度自动选择层级——日、周、月、季度、年（1/2/5）、十年、世纪、千年直至 50 亿年（Deep Time 按 1-2-5 循环）；刻度吸附真实历日（2 月比 1 月窄）；公元前显示 `xxxx BC` 后缀。
- **横/纵切换**：Ctrl+T 即时切换横向/纵向；「右侧 Thread」在两种方向下都保持在视觉右侧。
- **适配视图**：Ctrl+0 把当前数据范围适配到窗口（含 5% 边距）；加载文件后自动开窗到事件最密集的区域。
- **悬停提示**：悬停在事件上显示 Qt 原生 Tooltip（单点：`时间 + 摘要`；持续：`起 ~ 止 + 摘要`）。

## 事件显示

- **单点事件**：120px 固定宽圆角卡片（chip），浅灰底，中央一条竖直 pin 线标记精确时刻；文字超出以省略号截断。
- **持续事件**：圆角矩形 bar，青绿色（Thread 可配色），长度随缩放变化。
- **远端退化**：缩得太远、chip 实际时间跨度超过 2 年时，只画一条 2px 竖线标记——避免固定宽卡片伪装成持续事件。
- **布局**：所有事件（单点/持续）统一参与轨道分配，互不重叠；空间不足时堆叠在最外侧轨道；同一事件滚动中永远在同一列（布局稳定）。
- **双击**事件打开编辑器；**右键**事件可 Edit / Delete。

## 多线索（Thread）

- 时间轴两侧任意多条 Thread，每条绑定一个数据源（.his 文件）或为空 Thread。
- **添加**：右键空白处 → Add thread（加在光标所在侧），或 Thread Manager（Ctrl+M）里 Add Left / Add Right；来源三选一：现有文件 / 新建文件 / 空 Thread（默认空 Thread 一键添加）。
- **宽度（share）**：同侧 Thread 按份额分配宽度，可调（右键 Set thread share 或 Thread Manager 的 SpinBox，0.01~0.99），其余 Thread 自动按比例瓜分剩余。
- **管理**：Thread Manager 支持移除、侧内上移/下移、换侧、调整轴位置（Axis Offset 滑条实时生效）。
- **右键菜单**（Thread 上）：Add thread / Load file / New event / Set thread share / Switch side / Remove this thread / Fit to view / Toggle orientation；命中事件时追加 Edit event / Delete event。
- **配色**：16 色背景自动轮换，相邻 Thread 不同色；`__filter__` 结果 Thread 固定淡蓝。
