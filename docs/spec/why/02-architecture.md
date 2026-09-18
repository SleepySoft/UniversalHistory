# WHY · 为什么分层 + 信号驱动

> 分层约定：根仓库 `AGENTS.md`「项目分层」；旧版问题分析：`history_legacy_spec/how/13-stale-ui-analysis.md`。

## 旧版的结构问题

1. **数据无通知机制**：旧版 `History` 类是「内存数据库」，无信号/回调；Thread 持有索引快照；编辑器与时间轴零联动——三者叠加导致「编辑后永不实时刷新」（三层原因的完整分析见 legacy spec）。
2. **层间反向依赖**：旧版 viewer 自己管坐标映射、刻度、布局且与 TICK 强绑定；编辑器直接操作解析器和文件；横向/纵向两套绘制代码靠镜像特判。
3. **格式与模型不分**：`HistoryRecord` 同时承担解析结果、业务模型和索引三种角色，`.his` 序列化内嵌在模型里。

## 新架构（五层）

```
.his file
  → adapters（HisFileAdapter：外部格式唯一入口）
  → models（Event / EventIndex / Workspace：内存唯一数据源 + pyqtSignal）
  → render（geometry / layout / painter：只算几何与绘制，不读写业务数据）
  → ui（main_window / 各对话框：组装流程）
  → chrono（JDNTimestamp / TickStepper / 桥接：所有层的公共时间底座）
```

层规则（AGENTS.md）：

| 层 | 规则 |
| --- | --- |
| chrono | 定点整数为准，不引入浮点时间运算 |
| models | UI 通过信号响应数据变更 |
| adapters | 外部格式只经 Adapter 进入模型；模型/UI 不直接解析文件 |
| render | 只负责几何、布局、绘制 |
| ui | 组装用户流程；复杂计算下放 |

## 信号机制：对旧版缺陷的结构性修复

`Workspace` 是 QObject，发四个信号：`event_added(Event)`、`event_updated(Event)`、`event_removed(uuid)`、`source_loaded(source)`。TimelineView 连接这些信号做 `refresh_source`——**编辑后时间轴即时刷新**从「需要补丁」变成「架构的自然结果」。

批量加载时逐条发信号会刷屏，因此 `load()` 走静默追加 + 每 source 一次 `source_loaded`（见 [../how/04-models.md](../how/04-models.md)）。

## 统一逻辑坐标系：旧版未遂意图的完成态

旧版 `AxisMetrics` 想用 transverse/longitudinal 抽象统一横纵布局，但残留两套绘制和镜像特判，并留 TODO「Can we just rotate the QPaint axis?」。作者自述「借助 AI 轻松实现了绘制时的坐标变换，解决了耿耿于怀的横纵向统一绘制问题」。

新版答案：**逻辑 X 永远是时间轴方向、逻辑 Y 垂直于时间轴；QTransform（平移 + rotate 90°）负责逻辑→屏幕映射，且变换不含缩放**——逻辑坐标单位就是屏幕像素，布局常量（卡片宽 120px、边距 6px、轨宽 50px）可直接在逻辑坐标里加减。绘制代码只有一套，横纵切换 = 翻转 `is_vertical`（Ctrl+T）。

## 为什么是 PyQt6

- PyQt5 在 Python 3.14 上已无二进制 wheel（`pyqt5==5.15` 需 qmake 编译），旧 GUI 在现代环境实际无法运行；
- PyQt6 对现代 Python 支持良好；Qt5→Qt6 的改动（枚举命名空间、`exec_()`→`exec()`、`horizontalAdvance` 等）属机械替换，风险可控（`migration_analysis.md` §8.3）。
