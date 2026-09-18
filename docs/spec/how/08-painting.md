# HOW · 绘制规则（painter）

> 实现：`universal_history/render/painter.py`（纯绘制函数，不读写业务数据）。

## 1. 常量与配色

- 轴线宽 2px；刻度线长 ±6px；标签偏移 12px。
- `POINT_EVENT_FILL = (243,244,246)` 浅灰——继承旧版单点事件背景色；持续事件用 Thread 的 item color（默认青绿 `(185,227,217)`）。
- TimelineView 侧配色（`timeline_view.py`）：背景 `(255,245,247)`、轴 `(120,120,120)`、刻度 `(100,100,100)`、文字 `(50,50,50)`；刻度字体 "Segoe UI" 9pt、item 字体微软雅黑 8pt（旧版单点 6pt/持续 8pt 双字体，新版统一 8pt）。
- Thread 调色板 16 色 + ITEM_COLORS 6 色，数值沿用旧版（注释 "borrowed from the reference History project"）；**取色规则修正**：`len(left)+len(right)` 直接取模（第一个 Thread 用第 1 色；旧版先 +1 再取模跳过首色）。测试锁定「相邻 Thread 不同色」。

## 2. 刻度标签格式（_format_tick_label）

- 天文纪年转显示：`y<=0` → `-(y-1)` + `" BC"` 后缀（如 y=-4999 → "5000 BC"；旧版是 `BC ` 前缀）；
- Year 级：只显示年份数字（**注意 step_count>=1000 的两个分支代码相同，"ka/Ma/Ga" 名称注册了但未用于标签**——死分支）；
- Month 级：1 月显示年份，其余显示英文月缩写（Jan…Dec）；
- Day 级：每月 1 日显示 `MM/YYYY`，其余只显示日号；
- 其余层级：`str(tick)` fallback；
- 正年份无 "AD" 后缀（裸数字）。

## 3. 轴与刻度（paint_axis）

- 在逻辑变换激活状态画轴线 `(-half_len, 0)→(half_len, 0)`；
- 刻度线 y∈[-6,6] 竖线——**当前无主次刻度之分**；
- **标签在屏幕坐标绘制**：先 `resetTransform()` 保证文字不旋转；标签放轴的「无 Thread 覆盖侧」（水平模式上方、垂直模式右侧）；水平模式文字水平居中于刻度，垂直模式放刻度右侧 4px 垂直居中；
- 副作用：函数结束时 transform 处于 reset 状态**不恢复**——依赖调用方重设（隐式契约，脆弱点）。

## 4. 事件绘制（paint_item）

- **远端单点退化**：chip 实际时间跨度 > 2 年（硬编码阈值）时只画 2px 竖线 marker，无文字——防止缩远时固定宽卡片伪装成持续事件（新增行为，旧版没有）。
- 正常绘制：**圆角矩形 radius=4**，边框为填充色加深 20%（§8.6「圆角卡片/Chip」落地；旧版单点是带箭头五边形、持续是直角矩形）。
- 单点额外画一条**贯穿卡片的竖直 pin 线**标记精确时刻（区分 period bar）。
- 文字：`resetTransform` 后取 `screen_rect`，内缩 4px padding；宽或高 ≤0 不画；**`elidedText(ElideRight)` 省略号截断**（§8.6 落地；旧版 WordWrap 无截断）；左对齐 + 垂直居中。
- Thread 背景：整行填充 `(-half_len, y0, length, height)`。

## 5. 与旧版绘制的逐项对照

| 项 | 旧版 | 新版 |
| --- | --- | --- |
| 单点图形 | 10px 箭头五边形指向轴 | 圆角 chip + pin 竖线；远端退化为 marker |
| 持续图形 | 直角纯色矩形 | 圆角矩形 + 深色描边 |
| 文字 | 居中 WordWrap 无截断 | 左对齐 ElideRight 省略号 |
| 字体 | 单点 6pt / 持续 8pt | 统一 8pt |
| 主/副刻度 | 两级线长 ±15/±5px | 多层 LOD：minor 半长刻度 / major 全长带标签 / demoted 淡背景（P9 已实现，见 [02-tick-stepper.md](02-tick-stepper.md) §6） |
| 刻度标签 | 按最高非零位选格式、BC 前缀 | Year/Month/Day 特判、BC 后缀 |
| 悬停提示 | 自绘十字线 + 蓝色提示框 + 进度 | Qt 原生 Tooltip（见 [09-timeline-view.md](09-timeline-view.md)） |
