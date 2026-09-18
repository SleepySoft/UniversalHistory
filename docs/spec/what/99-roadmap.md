# WHAT 总结 —— 路线图与未实现功能

> 阶段方案：`HistoryMigration/migration_analysis.md` 第五章；当前状态：`HistoryMigration/docs/PROJECT_STATUS.md`。

## 已完成阶段

- **Phase 0 时间基础**：JDNTimestamp、TickStepper、桥接层、旧解析器适配 ✅
- **Phase 1 数据兼容层**：Event/EventIndex/Workspace、HisFileAdapter（读写）✅
- **Phase 2 新 Viewer**：统一坐标 TimelineView、刻度、布局、单点/持续绘制、横纵切换 ✅
- **Phase 3 编辑器与过滤**：EventEditor、FilterDialog、ThreadManager、编辑后实时刷新 ✅（详见各 what 分篇）

## 未实现（路线图）

| 功能 | 内容 | 阶段 |
| --- | --- | --- |
| Agent API | REST/WebSocket 接口、LLM 结构化 schema、事件广播协议；Agent 对话中整理/添加事件，UI 同步更新 | Phase 4 |
| Web 前端 | FastAPI 后端 + Canvas 时间轴；只读/共享视图优先（local-first 裁决） | Phase 4 |
| 非 .his 持久化 | JsonAdapter / 数据库 / HttpAdapter（Adapter 层已为此预留） | Phase 4+ |
| 权限管理 | 记录 `owner/visibility` 字段 | Phase 5（预留接口） |
| 协同编辑 | `proposal/branch/review` 模型（类 pull request） | Phase 5（预留接口） |
| 打包发布 | 目前仅源码运行 | 未排期 |

## 体验增强待办（继承自旧版设想与 §8.6）

- 主/副刻度双层体系 + 透明度淡入淡出（`docs/zoom_design.md` 核心机制，当前为单层刻度）；
- 单击展开事件详情（侧边栏/浮层）；
- 密集单点事件聚簇（「N 个事件」簇，点击展开）；
- 悬停十字准线 + 持续事件「第N年/共M年」进度提示（旧版有，未移植）；
- 农历/干支在刻度与提示中的显示；
- 键盘平移、跳转（jump to tick）；
- 旧解析器边界解耦（脱离对同级 `History/` 仓库的 sys.path 依赖，`PROJECT_STATUS.md` 下一步第 1 条）。

## 边界测试待补（PROJECT_STATUS 下一步第 2 条）

- Workspace / HisFileAdapter：保存冲突、空 source、重复 UUID 的边界行为。

## 验收总清单

行为级验收见 [../how/99-acceptance.md](../how/99-acceptance.md)；旧版行为对照见 `history_legacy_spec/how/99-migration-checklist.md`。
