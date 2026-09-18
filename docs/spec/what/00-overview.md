# WHAT 总览 —— UniversalHistory 提供什么

> 本文件是 what/ 的「总」入口。状态基准：`HistoryMigration/docs/PROJECT_STATUS.md`（2026-09-18，61 测试全过）。

## 软件形态

跨平台桌面应用（Python 3.10+ / PyQt6），`python -m universal_history` 启动。主窗口中央为无限时间轴，两侧可放置多条 Thread 对照；数据为本地 `.his` 纯文本文件（与旧版 History 完全兼容）。

启动时自动加载 `History/depot/example/example.his`（若存在）作为演示数据。

## 功能域清单

| 功能域 | 用户能做什么 | 状态 | 分篇 |
| --- | --- | --- | --- |
| 时间轴浏览 | 拖拽/滚轮平移、Ctrl+滚轮锚定缩放、刻度按密度自动换层（1 天 ~ 50 亿年）、横/纵切换（Ctrl+T）、适配数据范围（Ctrl+0） | 可用 | [01](01-timeline-and-threads.md) |
| 事件显示 | 单点事件（圆角 chip）与持续事件（圆角 bar）区分、省略号截断、悬停 Tooltip、过远缩放下 chip 退化为标记线 | 可用 | [01](01-timeline-and-threads.md) |
| 多线索对照 | 轴两侧任意 Thread、share 份额可调、换侧/排序/移除、16 色轮换、Thread Manager（Ctrl+M） | 可用 | [01](01-timeline-and-threads.md) |
| 事件编辑 | 五要素 + Tags、focus 校验、Lock 保值、日历选择、删除确认、编辑后时间轴即时刷新 | 可用 | [02](02-editing.md) |
| 过滤 | 按 source/focus/包含排除标签/时间范围筛选，结果显示在专用 `__filter__` Thread | 可用 | [03](03-filter-and-data.md) |
| 数据兼容 | 读写旧版 .his（自然语言时间、focus 结构、多行文本），写回保持兼容 | 可用 | [03](03-filter-and-data.md) |
| 农历/干支 | 时间可与农历互转（桥接层能力，UI 尚未暴露） | 底层可用 | [03](03-filter-and-data.md) |
| Agent API | — | **未实现** | [99](99-roadmap.md) |
| Web 前端 | — | **未实现** | [99](99-roadmap.md) |
| 权限/协同 | — | **设计预留** | [99](99-roadmap.md) |

## 与旧版的对应关系速览

- 旧版「可用主体」（浏览 + 录入 + 多线索）全部继承并优化；
- 旧版「坏损/半成品」（横纵切换、过滤上轴、编辑刷新、Thread 配置）全部重新实现且可用；
- 旧版「空壳/死代码」不迁移；
- 逐项对照见 `history_legacy_spec/what/99-status-matrix.md` 与本目录 [99-roadmap.md](99-roadmap.md)。
