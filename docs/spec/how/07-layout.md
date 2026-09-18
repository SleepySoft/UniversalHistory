# HOW · Thread / Track 布局算法（layout）

> 实现：`universal_history/render/layout.py`。旧版对照：`history_legacy_spec/how/09-thread-track-layout.md`；新策略决策：`migration_analysis.md` §8.5。

## 0. 概念层级（正式术语）

渲染与交互的概念分三级，**Track 是正式的一级**（术语表见 `migration_analysis.md` §8.4）：

```
TimelineView（控件，轴居中）
  └── Thread（线索：绑定 source、有 align/share/配色；用户可管理）
        └── Track（轨道：Thread 内按宽度分出的平行带；布局级概念，
              无用户可见身份，但轨数公式、分配顺序、末轨兜底都是行为规格）
              └── Item（事件条/chip：一个 EventIndex 的布局结果）
```

- 用户管理到 Thread 级（增删、换侧、share）；**Track 不提供用户级配置**，唯一可调参数是每轨最小宽度（`MIN_TRACK_WIDTH`）；
- Track 的存在理由与行为规则（长优先、统一分配、末轨兜底）即本文件 §3 的算法，验收以 `tests/render_tests/test_layout.py` 为准。

## 1. 视觉常量

- `POINT_EVENT_PIXEL_WIDTH = 120.0`：单点事件卡片的固定屏幕宽度（§8.6「固定长度卡片」的落地）；
- `EVENT_MARGIN_PIXELS = 6.0`：事件间水平间距；
- `MIN_TRACK_WIDTH = 50.0`（与旧版 `REFERENCE_TRACK_WIDTH = 50` 一致）；
- `POINT_EVENT_PIXEL_HEIGHT = 24.0`：已定义未使用（预留）。

## 2. 结构

- `ItemLayout`：单事件布局结果——event（EventIndex）、逻辑矩形 x0/x1/y0/y1、is_point；`screen_rect()` 四角分别过 `logical_to_screen` 取包围盒（**旋转安全**）。
- `Track`：index、y0/y1、`occupied: [(x0,x1)]`；`has_space` 为**闭区间重叠检测**（首尾相接允许）——比旧版「只查端点落入」严格（旧版靠长优先排序规避包含情形，新版无此隐患）。
- `ThreadLayout`：`align ∈ {"left","right"}`；`share` 钳制 [0,1]（本侧横向空间份额）；默认色 track 浅灰 `(240,240,240)`、item 青绿 `(185,227,217)`（继承旧版 story 色）；`source` 绑定 Workspace source 用于刷新；`set_events` 存快照清 items（不触发 arrange，由视图层统一调）。

## 3. arrange() 核心算法

1. 轨道数：`track_count = max(1, int(thread_width / min_track_width + 0.5))`（四舍五入、至少 1 条——与旧版公式一致）；`track_height = thread_width / track_count` 重新均分（实际轨宽未必等于设定值，同旧版）。
2. 轨道从 y0 起依次排开（右侧 y0≥0，左侧 y1≤0）。
3. **长优先排序**：key = `(-(until-since), since)`——持续时长降序 + 开始时间升序 tie-break（旧版依赖 sort 稳定性，新版确定性）。无时间事件排最前但随后跳过不布局。
4. **单点事件虚拟像素区间**：is_point → `x0 = time_x − 60`、`x1 = time_x + 60`（120px 卡片）；持续事件 → `[since_x, until_x]`。**单点与持续以同一套区间逻辑参与统一分配**——不再固定轨 0（§8.5 决策落地；回归测试：远处三个单点应占 ≥2 条轨）。
5. x1<x0 时交换（防御 BC 反向数据）。
6. **margin 外扩**：占用区间两侧各加 6px；存入 ItemLayout 时去掉 margin——**占用含边距、绘制不含**。
7. **分配**：顺序遍历轨道，首个 `has_space` 者接收。
8. **Fallback**：所有轨道放不下时**无条件压入最后一轨**（允许重叠）——与旧版一致，但新版两类事件统一适用。
9. **全量布局**：对所有事件布局（不做可见性裁剪）——继承旧版「全量重排保稳定」哲学；注意新版连绘制也不筛（大数据集潜在性能问题，见 [98-known-issues.md](98-known-issues.md)）。

## 4. 命中测试

`item_at_logical(pos)`：**逆序遍历** items（后分配者 = 较短/单点事件优先命中）——保证单点 chip 优先于底层长 bar 被点中。

## 5. 与旧版算法的关系

继承：轨道数公式、长优先、末轨兜底、全量重排、首尾相接允许。
优化：单点统一分配（§8.5）、重叠检测更严格、确定性 tie-break、移除无效的 3px 错位补偿 hack（旧版缺陷 #25）。
