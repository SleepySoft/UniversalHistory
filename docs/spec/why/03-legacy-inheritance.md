# WHY · 为什么操作逻辑继承旧版

> 迁移总原则（`migration_design.txt`）：「保留 History 项目原有的功能和特性」。本文件说明哪些旧版交互被刻意继承、为什么。

## 继承的理由

旧版交互不是随意堆出来的，而是作者多年实际使用（depot 中有中国史、世界史真实笔记）的沉淀。迁移的风险不在「新功能做不出来」，而在「老用户肌肉记忆被打断、老数据读不出来」。因此：**默认继承，只在旧版行为被证实是缺陷或有明确更好的方案时才优化**。

## 刻意继承的核心行为

| 行为 | 为什么必须保留 |
| --- | --- |
| 自然语言时间解析容错管线 | 「文章中复制的时间文字都能认出来」是录入零摩擦的引擎（legacy why/02）；适配层**原样复用**旧解析器，行为逐字不变 |
| 布局稳定性优先 | 「同一事件永远在同一列」是用户信任的基石（legacy why/04）；长优先排序、全量重排、末轨 fallback 全部保留 |
| 锚定缩放 | Ctrl+滚轮时鼠标指向的时间点不动——旧版正确实现，新版保留同一不变式 |
| 五要素 + focus_label | 数据模型语义与 .his 格式兼容的根基 |
| Time 必填 + focus 必填校验 | 编辑器的数据质量门 |
| Lock 字段保值 | 连续录入同一地点/人物的效率设计（README Dev Note 确认有意） |
| 多 Thread 对照 + 16 色轮换 | 软件初心；调色板数值原样沿用（`timeline_view.py` 注释 "borrowed from the reference History project"） |
| .his 纯文本格式 | 用户数据的兼容性红线；Git 协作媒介 |

## 有意优化（及理由）

| 旧版行为 | 新版行为 | 理由 |
| --- | --- | --- |
| 单点事件固定第 0 轨 | 120px 固定宽卡片以虚拟像素区间参与统一轨道分配 | 用户反馈（`migration_analysis.md` §8.5）：空间足够时不必挤在内侧 |
| 单点画箭头五边形、文字无截断 | 圆角 chip + pin 线 + ElideRight 省略号截断 | §8.6 现代 UI 呈现；旧版长标题显示不全是已知缺陷 |
| 双击才看详情 | Qt 原生 Tooltip 悬停即显摘要 | §8.6 交互分层 |
| 索引快照不同步 | Workspace 信号驱动刷新 | 旧版著名缺陷（legacy how/13） |
| 「保存到哪个文件」每次询问 | Workspace 当前 source 为默认；新事件先选/建文件 | `migration_design.txt` 列出的痛点 |
| Apply/Del 后弹「Save successful」模态框 | 静默落盘，失败才弹框 | 连续录入体验 |
| 删除无确认 | 删除前确认框 | 数据安全 |
| focus=time 永远无法 Apply | 修复 | 旧版 bug |
| 回填不还原 focus radio | 回填还原 | 旧版 bug |
| Thread 宽度不可调 | share 份额可调、可换侧、可排序 | 对照布局的灵活性 |

## 有意移除/废弃

- Auto Detect 占位按钮（NLP/LLM 将由真正的 Agent 能力兑现，而非提示框）；
- Load Depot（空实现）、Load All Records（阻塞 UI）、Help/About（空壳）；
- .index 文件管线（生成与回读均断链；EventIndex 为内存投影）；
- Label Tag Editor 空 Tab、Front/Back 卡片设想（未实现且无需求确认）。

## 细节兜底条款

新实现未覆盖的行为细节（例如解析容错的各种边角、刻度格式习惯、录入习惯），以 `history_legacy_spec/how/` 为参照标准——它是旧版行为的完整登记。冲突时以本规格（UniversalHistory 侧）为准。

**兜底条款的两个例外**（用户裁决，不继承旧版、按新设计）：

1. **记录归属与文件管理**——旧版「编辑了也不知道保存到哪」的混乱不沿用，按 [../how/14-event-ownership.md](../how/14-event-ownership.md) 的 O1-O7 设计；
2. **编辑器与时间轴的主从关系**——旧版「先有编辑器、后有轴」的结构不沿用，按 [../how/15-timeline-centric-editing.md](../how/15-timeline-centric-editing.md) 的时间轴中心设计。
