# WHY · 为什么 Agent 录入与 Web 是一等目标

> 目标来源：`migration_design.txt`「需要增加的特性」；历史渊源：`history_legacy_spec/why/05-ai-and-future.md`。

## 兑现旧承诺

作者数年前就在旧代码注释里写下用 NLP 提取历史事件要素的设想（截图存于 `History/Doc/img-nlp-comments.png`），README 更新节自述「现在终于到了可以兑现的时候」。旧版编辑器的四个 Auto Detect 按钮是占位符——弹 "Not implemented" 提示，文案承诺 "In feature, we will use NLP or LLM to recognize the %s information from main text"。

UniversalHistory 把这件事从「占位按钮」升格为**架构级目标**（`migration_design.txt:16`）：

> AI 及 Agent 录入友好：目标是和 Agent 对话的过程中由 Agent 整理并添加事件，界面同步更新。

## 架构上的准备

新分层（见 [02-architecture.md](02-architecture.md)）正是为此设计：

- **Workspace 信号**：Agent 添加事件 = 调 `workspace.upsert()`，UI 通过信号同步刷新——「界面同步更新」不需要任何额外机制；
- **Adapter 层**：未来的 `HttpAdapter` 让网络数据源与本地 .his 走同一模型；
- **datetime/Unix 桥接**：Agent API 的数据交换格式就绪。

## Web 版的定位（用户已裁决）

`migration_analysis.md` §8.2：**桌面端（Qt6）为主力编辑/浏览工具，local-first；网页版作为可选的只读或共享视图，通过后端按需启用**。理由：网页要能承载操作就需要启动后端，比较重；保留「双击即可编辑、直接操作本地文件」的轻量体验优先。

## 远期预留（Phase 5，不实现但留接口）

- 权限管理：记录增加 `owner/visibility`；
- 协同编辑：`proposal/branch/review` 模型（类似 pull request——呼应旧版「纯文本 + Git + fork/PR」的协作哲学，见 legacy why/03）。

## 当前状态

Agent API（REST/WebSocket）、LLM schema、事件广播协议、Web 前端均未实现（`PROJECT_STATUS.md`「未完成」节）。下一步建议见 `PROJECT_STATUS.md:64-69`：定义 Agent Service 最小 JSON schema、引入 FastAPI/WebSocket 最小后端，复用 Event/EventIndex/Workspace 语义。
