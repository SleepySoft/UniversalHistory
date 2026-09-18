# UniversalHistory WHY / WHAT / HOW 规格

本目录是 UniversalHistory 的结构化规格文档，与旧版规格 `HistoryMigration/docs/history_legacy_spec/` 配套：前者描述「旧软件是什么」，本目录描述「新软件是什么、要成为什么」。

## 编写原则

1. **操作逻辑 = Legacy 特性 + 优化**：用户可见的交互与行为默认继承旧版（见 `history_legacy_spec/`），凡新实现有意改变的地方，本文档标注「优化」并说明理由。
2. **底层按新设计规范化**：时间（JDN 定点整数）、数据（Event/Workspace 信号模型）、格式（Adapter 层）、渲染（统一逻辑坐标）以 `docs/core_design.md`、`docs/zoom_design.md` 与现有代码为准。
3. **细节兜底**：本文档与 UniversalHistory 代码未明确的行为细节，以 `history_legacy_spec/` 为参照标准；冲突时以本目录为准。

## 目录结构

```
spec/
├── why/    —— 为什么重做、为什么这样设计
├── what/   —— 软件现在/将要提供什么功能
└── how/    —— 各层如何实现与行为规格
```

## 索引

### why/

| 文件 | 内容 |
| --- | --- |
| [00-overview.md](why/00-overview.md) | 总览：迁移动机与新设计哲学速览 |
| [01-time-system.md](why/01-time-system.md) | 为什么从 TICK 到 JDNTimestamp |
| [02-architecture.md](why/02-architecture.md) | 为什么分层 + 信号驱动 |
| [03-legacy-inheritance.md](why/03-legacy-inheritance.md) | 为什么操作逻辑继承旧版 |
| [04-agent-and-web.md](why/04-agent-and-web.md) | 为什么 Agent 录入与 Web 是一等目标 |
| [99-summary.md](why/99-summary.md) | 总结：继承/优化/新增决策总表 |

### what/

| 文件 | 内容 |
| --- | --- |
| [00-overview.md](what/00-overview.md) | 总览：功能清单与状态 |
| [01-timeline-and-threads.md](what/01-timeline-and-threads.md) | 时间轴浏览与多线索 |
| [02-editing.md](what/02-editing.md) | 事件编辑 |
| [03-filter-and-data.md](what/03-filter-and-data.md) | 过滤与数据兼容 |
| [99-roadmap.md](what/99-roadmap.md) | 总结：路线图与未实现功能 |

### how/

| 文件 | 内容 |
| --- | --- |
| [00-overview.md](how/00-overview.md) | 总览：分层架构与数据流 |
| [01-jdn-timestamp.md](how/01-jdn-timestamp.md) | JDNTimestamp 规范 |
| [02-tick-stepper.md](how/02-tick-stepper.md) | 刻度层级与步进 |
| [03-time-bridges.md](how/03-time-bridges.md) | datetime / 农历 / 旧 TICK 桥接 |
| [04-models.md](how/04-models.md) | Event / EventIndex / Workspace 与信号语义 |
| [05-his-adapter.md](how/05-his-adapter.md) | .his 读写规则 |
| [06-geometry.md](how/06-geometry.md) | 统一逻辑坐标系 |
| [07-layout.md](how/07-layout.md) | Thread/Track 布局算法 |
| [08-painting.md](how/08-painting.md) | 绘制规则 |
| [09-timeline-view.md](how/09-timeline-view.md) | TimelineView 交互行为 |
| [10-main-window.md](how/10-main-window.md) | 主窗口与菜单 |
| [11-editor.md](how/11-editor.md) | EventEditor 行为 |
| [12-dialogs.md](how/12-dialogs.md) | Filter / ThreadManager / AddThread / BindSource 对话框 |
| [13-interaction-spec.md](how/13-interaction-spec.md) | 交互规格：新版为准项与 Legacy 参照项 |
| [98-known-issues.md](how/98-known-issues.md) | 总结：已知缺陷与 TODO |
| [99-acceptance.md](how/99-acceptance.md) | 总结：验收清单 |

## 相关文档

- 旧版行为规格：`HistoryMigration/docs/history_legacy_spec/`
- 迁移分析与阶段方案：`HistoryMigration/migration_analysis.md`
- 迁移目标：`HistoryMigration/migration_design.txt`
- 当前进度：`HistoryMigration/docs/PROJECT_STATUS.md`
- 时间系统设计：`docs/core_design.md`；刻度/缩放设计：`docs/zoom_design.md`
