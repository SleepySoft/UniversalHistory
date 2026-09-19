# HOW · 绘制规则（painter）

> 实现：`universal_history/render/painter.py`（纯绘制函数，不读写业务数据）。

## 1. 常量与配色

- 轴线宽 2px；刻度单侧下挂：major 9px（1.5px 宽，层次更重）/ minor 4px / demoted 7px；标签顶缘距基线 14px（LABEL_TOP），刻度与标签之间有 5px 净间距；轴带 `AXIS_BREADTH = 60`（geometry.py），轴带底色 `AXIS_STRIP_FILL = (252,250,251)`，与暖色画布区分出独立的「尺子」区。
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

- **轴带（2026-09-19 重设计）**：先填 `AXIS_STRIP_FILL` 轴带背景（横向 ±30px），再画基线——轴区读作独立的尺子，不再是光秃秃一根线；
- 基线在逻辑 y=0 横贯当前视口（按 `center_logical_x()` 定位）；
- **刻度只向 +y 单侧悬挂**（major 9px / minor 4px / demoted 7px），不再 ±6px 上下穿——旧设计上行刻度与标签互相叠压（用户报告）；纵向模式由旋转自动转置为「向左」；
- **标签在屏幕坐标绘制**：先 `resetTransform()` 保证文字不旋转；标签位于刻度尖端下方（`LABEL_TOP=14`），水平模式 `AlignHCenter|AlignTop` 居中于刻度，垂直模式在轴左侧右对齐、垂直居中于刻度（与旧版纵向标签方位一致）；
- 标签绘制段用 `qp.save()`/`qp.restore()` 包裹，`resetTransform()` 不泄漏——函数进出 transform 状态一致（旧文档记的「不恢复」隐式契约已随 save/restore 消除）。

## 4. 事件绘制（paint_item）

- **远端单点退化**：chip 实际时间跨度 > 2 年（硬编码阈值）时只画 2px 竖线 marker（位于精确时刻 = 卡片左缘）+ 轴上圆点，无文字——防止缩远时固定宽卡片伪装成持续事件（新增行为，旧版没有）。
- 正常绘制：**圆角矩形 radius=4**，边框为填充色加深 20%（§8.6「圆角卡片/Chip」落地；旧版单点是带箭头五边形、持续是直角矩形）。
- **单点「棒棒糖」结构（2026-09-19 重设计，取代居中 chip + 中央 pin 线）**：
  - 卡片**左缘锚定在事件时刻**（`x0 = time_x`，`layout.py`），不再以时刻居中——消除「卡片散、时刻靠猜」；
  - **轴上圆点**（r=3，深灰 `POINT_DOT_COLOR`）落在逻辑 y=0 的精确时刻——沿轴即可读点；
  - **引线（stem）**：从卡片靠轴侧边缘连到轴点（中灰 `POINT_STEM_COLOR`，1px），穿越中间轨道属预期（主流时间轴工具如 Knight Lab Timeline 同款 lollipop 惯例）；
  - 引线/圆点在卡片**之前**绘制（压在卡片底下）；横纵切换由统一逻辑坐标自动转置，无特判。
- 文字：`resetTransform` 后取 `screen_rect`，内缩 4px padding；宽或高 ≤0 不画；**`elidedText(ElideRight)` 省略号截断**（§8.6 落地；旧版 WordWrap 无截断）；左对齐 + 垂直居中。
- Thread 背景：整行填充（按 `center_logical_x()` 铺满当前视口，见 [06-geometry.md](06-geometry.md) §3）。

## 5. 与旧版绘制的逐项对照

| 项 | 旧版 | 新版 |
| --- | --- | --- |
| 单点图形 | 10px 箭头五边形指向轴 | 棒棒糖：轴上圆点 + 引线 + 左缘锚定圆角 chip（2026-09-19 重设计）；远端退化为 marker + 轴点 |
| 持续图形 | 直角纯色矩形 | 圆角矩形 + 深色描边 |
| 文字 | 居中 WordWrap 无截断 | 左对齐 ElideRight 省略号 |
| 字体 | 单点 6pt / 持续 8pt | 统一 8pt |
| 主/副刻度 | 两级线长 ±15/±5px 上下穿轴 | 多层 LOD（minor 4 / major 9 / demoted 7px），**单侧下挂不越轴**（2026-09-19），major 1.5px 加粗 |
| 刻度标签 | 按最高非零位选格式、BC 前缀；轴下方 ±15 刻度之外 | Year/Month/Day 特判、BC 后缀；轴带内刻度下方（LABEL_TOP=14），与基线净距 5px |
| 悬停提示 | 自绘十字线 + 蓝色提示框 + 进度 | 自绘十字线 + 深色圆角提示框 + 进度（2026-09-19 恢复自绘机制，见 [09-timeline-view.md](09-timeline-view.md) §6） |
